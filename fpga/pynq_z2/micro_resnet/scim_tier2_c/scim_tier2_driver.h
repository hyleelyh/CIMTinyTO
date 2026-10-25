/* ============================================================================
 * Header: scim_tier2_driver.h
 * Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
 * Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Host Emulation (Pillar 6.1)
 * Standard: C99 / POSIX MMIO Shared Library
 * ============================================================================
 * Pedagogical & Silicon Rationale:
 *
 * 1. User-Space Direct Hardware Pointers (/dev/mem):
 *    - Eliminates kernel-context-switch overhead by memory mapping physical
 *      AXI4-Lite addresses directly into user-space via mmap().
 *    - Uses volatile pointer access (STR/LDR ARM instructions) to prevent compiler
 *      optimization from pruning memory-mapped I/O transactions.
 *
 * 2. Packed Single-Cycle AXI Writes:
 *    - Exploits tt_scim_axi_wrapper's combined strobe encoding:
 *        REG_DATA_IN = (data & 0xFF) | (1 << 8) -> Sets byte AND pulses wr_act!
 *        REG_DATA_IN = (cmd  & 0xFF) | (1 << 9) -> Sets byte AND pulses ctrl_strobe!
 *    - Halves MMIO write traffic from 32 writes to 16 writes per tile.
 * ============================================================================
 */

#ifndef SCIM_TIER2_DRIVER_H
#define SCIM_TIER2_DRIVER_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* AXI4-Lite Register Offsets (in bytes) */
#define SCIM_REG_CTRL       0x00
#define SCIM_REG_DATA_IN    0x04
#define SCIM_REG_STATUS     0x08
#define SCIM_REG_DATA_OUT   0x0C
#define SCIM_REG_STEP_PULSE 0x10

/* Default Physical Base Address on Zynq-7020 */
#define SCIM_DEFAULT_BASE_ADDR  0x40000000
#define SCIM_MAP_SIZE           0x1000

/* Initialization and Teardown */
int  scim_c_init(uint32_t base_addr, int force_sim);
void scim_c_close(void);
int  scim_c_is_simulated(void);

/* Low-Level Hardware Control */
void scim_c_reset(void);
void scim_c_load_weights(const uint8_t *flat_weights_256);
int  scim_c_run_mvm(const uint8_t *act_16, int mode, int16_t *results_out_16);

/* High-Performance Whole-Layer Acceleration */
int  scim_c_execute_layer(const uint8_t *input_hw_c, int H, int W,
                          const int16_t *bias_16, int mult, int shift,
                          uint8_t *output_hw_c);

#ifdef __cplusplus
}
#endif

#endif /* SCIM_TIER2_DRIVER_H */
