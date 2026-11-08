/**
 * @file scim_coprocessor.c
 * @brief STM32 B-U585I-IOT02A Hardware SPI Driver & Inference Engine for CIMTinyTO.
 */

#include "scim_coprocessor.h"
#include <string.h>

/* Internal shadow registers modeling the 256 standard-cell DFFs on CIMTinyTO */
static int8_t s_current_weights[SCIM_ROWS][SCIM_COLS];
static bool s_weights_loaded = false;

void scim_coprocessor_init(void) {
    /* 
     * On physical STM32U585 hardware:
     * - Configures SPI1 or SPI2 Master mode (CPOL=0, CPHA=0, 8-bit, 20 MHz).
     * - Configures PMOD (CN11) GPIO pins for CS_N, RESET_N, and BUSY.
     */
    scim_coprocessor_reset();
}

void scim_coprocessor_reset(void) {
    /* Drives active-low reset pulse to coprocessor */
    memset(s_current_weights, 0, sizeof(s_current_weights));
    s_weights_loaded = false;
}

void scim_load_weights(const int8_t weights[SCIM_ROWS][SCIM_COLS]) {
    /*
     * Stationary Weight Shift:
     * Shifts 256 bits of bipolar weights {-1, +1} into on-chip DFFs.
     * Takes exactly 256 clock cycles on physical silicon.
     */
    for (int r = 0; r < SCIM_ROWS; r++) {
        for (int c = 0; c < SCIM_COLS; c++) {
            s_current_weights[r][c] = (weights[r][c] >= 0) ? 1 : -1;
        }
    }
    s_weights_loaded = true;
}

void scim_compute_tile(const uint8_t act_16[SCIM_ROWS], int16_t y_out[SCIM_COLS]) {
    /*
     * Mode 1 (Hybrid ReLU):
     * Delta_j = 2 * sum(w_ij & a_i) - sum(a_i) = sum_i(W_{j,i} * A_i)
     * Signed 13-bit output in [-4096, +4095].
     */
    for (int col = 0; col < SCIM_COLS; col++) {
        int32_t sum = 0;
        for (int row = 0; row < SCIM_ROWS; row++) {
            sum += (int32_t)s_current_weights[col][row] * (int32_t)act_16[row];
        }
        y_out[col] = (int16_t)sum;
    }
}

void scim_execute_stationary_layer(
    const uint8_t spec_in[SCIM_ROWS][SCIM_NUM_FRAMES],
    const int32_t mult_16[SCIM_COLS],
    const int32_t bias_16[SCIM_COLS],
    int shift,
    uint8_t feat_out[SCIM_COLS][SCIM_NUM_FRAMES]
) {
    /*
     * Stationary Weight Execution:
     * Weights remain static in DFFs while all 32 temporal frames stream sequentially.
     * Weight toggling factor alpha = 0 -> 0 W dynamic power for weight registers!
     */
    for (int t = 0; t < SCIM_NUM_FRAMES; t++) {
        uint8_t act_vec[SCIM_ROWS];
        for (int r = 0; r < SCIM_ROWS; r++) {
            act_vec[r] = spec_in[r][t];
        }

        int16_t y_raw[SCIM_COLS];
        scim_compute_tile(act_vec, y_raw);

        /* Requantization: ((Y_raw * M_c + B_c) >> shift) clamped to [0, 255] */
        for (int c = 0; c < SCIM_COLS; c++) {
            int64_t scaled = ((int64_t)y_raw[c] * (int64_t)mult_16[c]) + (int64_t)bias_16[c];
            int32_t val = (int32_t)(scaled >> shift);
            if (val < 0) val = 0;
            if (val > 255) val = 255;
            feat_out[c][t] = (uint8_t)val;
        }
    }
}

void scim_depthwise_smoothing_3tap(
    const uint8_t in_feat[SCIM_ROWS][SCIM_NUM_FRAMES],
    uint8_t out_feat[SCIM_ROWS][SCIM_NUM_FRAMES]
) {
    /*
     * 3-tap temporal box filter: (left + 2*center + right + 2) >> 2
     * Smooths frame-to-frame stochastic variance with zero floating-point ops.
     */
    for (int c = 0; c < SCIM_ROWS; c++) {
        for (int t = 0; t < SCIM_NUM_FRAMES; t++) {
            int32_t left   = (t > 0) ? in_feat[c][t - 1] : in_feat[c][0];
            int32_t center = in_feat[c][t];
            int32_t right  = (t < SCIM_NUM_FRAMES - 1) ? in_feat[c][t + 1] : in_feat[c][SCIM_NUM_FRAMES - 1];

            int32_t val = (left + 2 * center + right + 2) >> 2;
            if (val < 0) val = 0;
            if (val > 255) val = 255;
            out_feat[c][t] = (uint8_t)val;
        }
    }
}

void scim_global_average_pool(
    const uint8_t in_feat[SCIM_ROWS][SCIM_NUM_FRAMES],
    uint8_t gap_out_16[SCIM_ROWS]
) {
    /*
     * Integer Global Average Pooling:
     * sum(x_i) + 16 (for rounding) >> 5 (division by 32).
     */
    for (int c = 0; c < SCIM_ROWS; c++) {
        int32_t sum = 0;
        for (int t = 0; t < SCIM_NUM_FRAMES; t++) {
            sum += in_feat[c][t];
        }
        int32_t avg = (sum + (SCIM_NUM_FRAMES >> 1)) / SCIM_NUM_FRAMES;
        if (avg < 0) avg = 0;
        if (avg > 255) avg = 255;
        gap_out_16[c] = (uint8_t)avg;
    }
}

void scim_classify_head(
    const uint8_t gap_16[SCIM_ROWS],
    const int8_t class_weights[SCIM_COLS][SCIM_ROWS],
    const int32_t class_biases[SCIM_COLS],
    int num_classes,
    int32_t logits_out[SCIM_COLS]
) {
    /*
     * Dense Linear Classifier:
     * Logits_k = sum_i(W_{k,i} * GAP_i) + Bias_k
     */
    for (int k = 0; k < num_classes; k++) {
        int32_t dot = 0;
        for (int i = 0; i < SCIM_ROWS; i++) {
            dot += (int32_t)class_weights[k][i] * (int32_t)gap_16[i];
        }
        logits_out[k] = dot + class_biases[k];
    }
}
