#define _DEFAULT_SOURCE
#define _POSIX_C_SOURCE 200809L

#include "scim_tier2_driver.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <errno.h>

/* Internal State */
static int dev_mem_fd = -1;
static volatile uint8_t *mapped_base = NULL;
static uint32_t current_base_addr = SCIM_DEFAULT_BASE_ADDR;
static int is_simulated = 0;

/* Software Emulation Fallback State (when /dev/mem is unavailable) */
static uint8_t  sim_shift_reg[256];
static uint8_t  sim_act_regs[16];
static int16_t  sim_accumulators[16];
static int      sim_mode = 1;
static uint8_t  sim_addr = 0;
static uint8_t  sim_byte_sel = 0;

/* Register Write Macro */
static inline void reg_write(uint32_t offset, uint32_t val) {
    if (mapped_base) {
        *((volatile uint32_t *)(mapped_base + offset)) = val;
    }
}

/* Register Read Macro */
static inline uint32_t reg_read(uint32_t offset) {
    if (mapped_base) {
        return *((volatile uint32_t *)(mapped_base + offset));
    }
    return 0;
}

int scim_c_init(uint32_t base_addr, int force_sim) {
    current_base_addr = base_addr;
    is_simulated = 0;

    if (force_sim) {
        is_simulated = 1;
        mapped_base = NULL;
        memset(sim_shift_reg, 0, sizeof(sim_shift_reg));
        memset(sim_act_regs, 0, sizeof(sim_act_regs));
        memset(sim_accumulators, 0, sizeof(sim_accumulators));
        return 0;
    }

    dev_mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (dev_mem_fd < 0) {
        /* Fall back to simulation mode gracefully */
        is_simulated = 1;
        mapped_base = NULL;
        memset(sim_shift_reg, 0, sizeof(sim_shift_reg));
        memset(sim_act_regs, 0, sizeof(sim_act_regs));
        memset(sim_accumulators, 0, sizeof(sim_accumulators));
        return 0;
    }

    mapped_base = (volatile uint8_t *)mmap(
        NULL,
        SCIM_MAP_SIZE,
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        dev_mem_fd,
        (off_t)base_addr
    );

    if (mapped_base == MAP_FAILED) {
        close(dev_mem_fd);
        dev_mem_fd = -1;
        mapped_base = NULL;
        is_simulated = 1;
        return 0;
    }

    /* Hardware reset sequence */
    scim_c_reset();
    return 0;
}

void scim_c_close(void) {
    if (mapped_base && mapped_base != MAP_FAILED) {
        munmap((void *)mapped_base, SCIM_MAP_SIZE);
        mapped_base = NULL;
    }
    if (dev_mem_fd >= 0) {
        close(dev_mem_fd);
        dev_mem_fd = -1;
    }
    is_simulated = 0;
}

int scim_c_is_simulated(void) {
    return is_simulated;
}

void scim_c_reset(void) {
    if (is_simulated) {
        memset(sim_shift_reg, 0, sizeof(sim_shift_reg));
        memset(sim_act_regs, 0, sizeof(sim_act_regs));
        memset(sim_accumulators, 0, sizeof(sim_accumulators));
        sim_addr = 0;
        sim_byte_sel = 0;
        return;
    }

    /* Assert reset: rst_n=0, ena=1 */
    reg_write(SCIM_REG_CTRL, 0x02);
    usleep(100);
    /* Release reset: rst_n=1, ena=1 */
    reg_write(SCIM_REG_CTRL, 0x03);
    usleep(100);
}

void scim_c_load_weights(const uint8_t *flat_weights_256) {
    if (is_simulated) {
        memcpy(sim_shift_reg, flat_weights_256, 256);
        return;
    }

    /* Shift in MSB first (index 255 down to 0) */
    for (int idx = 255; idx >= 0; idx--) {
        uint32_t bit = flat_weights_256[idx] & 0x01;
        /* REG_CTRL: rst_n=1, ena=1, w_shift_en=1 (bit 5), w_din=bit (bit 4) */
        uint32_t ctrl_val = 0x03 | (1 << 5) | (bit << 4);
        reg_write(SCIM_REG_CTRL, ctrl_val);
    }
}

static void sim_execute_mvm(void) {
    /* Fast integer Mode 1 (Hybrid ReLU) simulation: W in {-1, +1}, A in [0, 255] */
    for (int col = 0; col < 16; col++) {
        int32_t sum = 0;
        for (int row = 0; row < 16; row++) {
            int w_bit = sim_shift_reg[row * 16 + col];
            int32_t w_val = (w_bit > 0) ? +1 : -1;
            int32_t act_val = (int32_t)sim_act_regs[row];
            sum += w_val * act_val;
        }
        /* Saturate to 13-bit signed [-4096, +4095] */
        if (sum > 4095) sum = 4095;
        if (sum < -4096) sum = -4096;
        sim_accumulators[col] = (int16_t)sum;
    }
}

int scim_c_run_mvm(const uint8_t *act_16, int mode, int16_t *results_out_16) {
    if (is_simulated) {
        memcpy(sim_act_regs, act_16, 16);
        sim_mode = mode;
        sim_execute_mvm();
        memcpy(results_out_16, sim_accumulators, 16 * sizeof(int16_t));
        return 257; /* Hardware cycles */
    }

    /* Step 1: Reset address counter to 0 */
    /* Writing REG_DATA_IN with bit 9 pulses ctrl_strobe: cmd = (addr=0, mode=mode) */
    uint32_t mode_bit = (mode != 0) ? 1 : 0;
    uint32_t cmd_reset_addr = 0x00 | (mode_bit << 4) | (1 << 9);
    reg_write(SCIM_REG_DATA_IN, cmd_reset_addr);

    /* Step 2: Write 16 activation bytes with packed wr_act strobing */
    for (int i = 0; i < 16; i++) {
        /* Writing REG_DATA_IN with bit 8 sets byte AND pulses wr_act */
        uint32_t act_cmd = (act_16[i] & 0xFF) | (1 << 8);
        reg_write(SCIM_REG_DATA_IN, act_cmd);
    }

    /* Step 3: Trigger computation (start_req=1, mode=mode_bit) with ctrl_strobe pulse (bit 9) */
    uint32_t start_cmd = (1 << 7) | (mode_bit << 4) | (1 << 9);
    reg_write(SCIM_REG_DATA_IN, start_cmd);

    /* Step 4: Tight polling loop waiting for done assertion (REG_STATUS bit 1) */
    uint32_t status = 0;
    int timeout = 500000;
    while (timeout-- > 0) {
        status = reg_read(SCIM_REG_STATUS);
        if (status & (1 << 1)) {
            break; /* done asserted */
        }
    }

    /* Step 5: Read back 16 accumulators (lower and upper bytes) */
    for (int col = 0; col < 16; col++) {
        /* Low byte (byte_sel = 0) */
        uint32_t cmd_low = (0 << 6) | (col & 0x0F) | (1 << 9);
        reg_write(SCIM_REG_DATA_IN, cmd_low);
        uint32_t low_byte = reg_read(SCIM_REG_DATA_OUT) & 0xFF;

        /* High byte (byte_sel = 1) */
        uint32_t cmd_high = (1 << 6) | (col & 0x0F) | (1 << 9);
        reg_write(SCIM_REG_DATA_IN, cmd_high);
        uint32_t high_byte = reg_read(SCIM_REG_DATA_OUT) & 0xFF;

        /* Reconstruct 13-bit signed integer */
        uint32_t raw = (high_byte << 8) | low_byte;
        int16_t val = (int16_t)(raw & 0x1FFF);
        if (val & 0x1000) {
            val = (int16_t)(val - 0x2000);
        }
        results_out_16[col] = val;
    }

    uint32_t cycles = (status >> 16) & 0xFFFF;
    return (int)cycles;
}

int scim_c_execute_layer(const uint8_t *input_hw_c, int H, int W,
                          const int16_t *bias_16, int mult, int shift,
                          uint8_t *output_hw_c) {
    int total_pixels = H * W;
    int16_t raw_acc[16];

    for (int p = 0; p < total_pixels; p++) {
        const uint8_t *act_vec = &input_hw_c[p * 16];
        uint8_t *out_vec = &output_hw_c[p * 16];

        scim_c_run_mvm(act_vec, 1 /* Mode 1 */, raw_acc);

        /* Requantize: clamp(floor((acc + bias) * mult >> shift), 0, 255) */
        for (int c = 0; c < 16; c++) {
            int64_t val = ((int64_t)raw_acc[c] + (int64_t)bias_16[c]) * mult;
            val = val >> shift;
            if (val < 0) val = 0;
            if (val > 255) val = 255;
            out_vec[c] = (uint8_t)val;
        }
    }

    return total_pixels;
}
