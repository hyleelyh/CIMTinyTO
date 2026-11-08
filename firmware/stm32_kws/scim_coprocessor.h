/**
 * @file scim_coprocessor.h
 * @brief STM32 B-U585I-IOT02A Hardware SPI Driver & Inference Engine for CIMTinyTO.
 *
 * Microarchitectural Highlights:
 * - 3.3V LVCMOS SPI Master @ 10-25 MHz.
 * - Stationary Weight Caching: 256-bit serial weight shift occurs ONCE per layer.
 * - Frame Streaming: 32 temporal frames stream at wire-speed through static DFFs.
 * - Mode 1 (Hybrid ReLU): Signed 13-bit accumulator output Y in [-4096, +4095].
 * - Zero Floating Point: 32-bit integer arithmetic with per-channel multipliers.
 */

#ifndef SCIM_COPROCESSOR_H
#define SCIM_COPROCESSOR_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SCIM_ROWS       16
#define SCIM_COLS       16
#define SCIM_NUM_FRAMES 32

/**
 * @brief Initialize SPI and GPIO control lines for CIMTinyTO coprocessor.
 */
void scim_coprocessor_init(void);

/**
 * @brief Hard reset the SCIM coprocessor via rst_n pulse.
 */
void scim_coprocessor_reset(void);

/**
 * @brief Load 16x16 bipolar weight matrix into stationary DFF shift registers.
 * @param[in] weights 16x16 array of bipolar weights in {-1, +1}.
 */
void scim_load_weights(const int8_t weights[SCIM_ROWS][SCIM_COLS]);

/**
 * @brief Compute single 16x16 SCIM tile in Mode 1 (Hybrid ReLU).
 * @param[in]  act_16 16-element unipolar activation vector in [0, 255].
 * @param[out] y_out  16-element signed accumulator results in [-4096, +4095].
 */
void scim_compute_tile(const uint8_t act_16[SCIM_ROWS], int16_t y_out[SCIM_COLS]);

/**
 * @brief Execute stationary weight layer across 32 temporal frames.
 * @param[in]  spec_in   16x32 input uint8 activation spectrogram.
 * @param[in]  mult_16   16-element per-channel fixed-point multipliers.
 * @param[in]  bias_16   16-element per-channel fixed-point biases.
 * @param[in]  shift     Bit shift for requantization (typically 11).
 * @param[out] feat_out  16x32 output uint8 feature map.
 */
void scim_execute_stationary_layer(
    const uint8_t spec_in[SCIM_ROWS][SCIM_NUM_FRAMES],
    const int32_t mult_16[SCIM_COLS],
    const int32_t bias_16[SCIM_COLS],
    int shift,
    uint8_t feat_out[SCIM_COLS][SCIM_NUM_FRAMES]
);

/**
 * @brief Host Cortex-M33 3-tap temporal depthwise box smoothing across time frames.
 * Formula: (left + 2*center + right + 2) >> 2
 */
void scim_depthwise_smoothing_3tap(
    const uint8_t in_feat[SCIM_ROWS][SCIM_NUM_FRAMES],
    uint8_t out_feat[SCIM_ROWS][SCIM_NUM_FRAMES]
);

/**
 * @brief Host Cortex-M33 Global Temporal Average Pooling (GAP) across 32 frames.
 */
void scim_global_average_pool(
    const uint8_t in_feat[SCIM_ROWS][SCIM_NUM_FRAMES],
    uint8_t gap_out_16[SCIM_ROWS]
);

/**
 * @brief Evaluate Dense Classifier Head dot product and add integer biases.
 */
void scim_classify_head(
    const uint8_t gap_16[SCIM_ROWS],
    const int8_t class_weights[SCIM_COLS][SCIM_ROWS],
    const int32_t class_biases[SCIM_COLS],
    int num_classes,
    int32_t logits_out[SCIM_COLS]
);

#ifdef __cplusplus
}
#endif

#endif /* SCIM_COPROCESSOR_H */
