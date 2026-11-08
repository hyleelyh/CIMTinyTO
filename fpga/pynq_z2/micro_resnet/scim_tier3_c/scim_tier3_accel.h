/* ============================================================================
 * Header: scim_tier3_accel.h
 * Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
 * Target: AMD Xilinx Zynq-7020 (PYNQ-Z2 ARM Cortex-A9) & Host Emulation (Pillar 6.1)
 * Standard: C99 / POSIX Shared Library
 * ============================================================================
 * Pedagogical & Silicon Rationale:
 *
 * 1. Overcoming the Memory Wall on ARM Cortex-A9:
 *    - The Zynq-7020 Cortex-A9 core features a 32 KB L1 Data Cache and 512 KB L2.
 *    - NumPy in Python dynamically allocates multi-dimensional heap arrays (malloc)
 *      for every intermediate tensor operation, causing continuous cache line evictions
 *      and expensive DDR3 memory bus contention (~70-100 ns latency per miss).
 *    - This C acceleration library eliminates all dynamic allocations by processing
 *      data in-place using pre-allocated, contiguous CMA-aligned buffers.
 *
 * 2. NHWC (Channels-Last) SIMD Vector Alignment:
 *    - 16 channels stored consecutively in memory equal exactly 16 bytes (128 bits).
 *    - 128 bits perfectly matches:
 *      (a) An ARM NEON SIMD vector register (q0..q15).
 *      (b) A four-word burst transfer on the 32-bit AXI-DMA bus.
 *    - Keeping tensors in NHWC format across all layers eliminates repetitive
 *      multidimensional transpositions (np.transpose(feat, (1, 2, 0))).
 * ============================================================================
 */

#ifndef SCIM_TIER3_ACCEL_H
#define SCIM_TIER3_ACCEL_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SCIM_CMD_MVM_BATCH 0x03

/**
 * @brief Preprocess 32x32 RGB image and pack directly into AXI-DMA command packet.
 *
 * Converts 32x32x3 uint8 RGB pixels into 16-channel unipolar features and
 * packs them little-endian directly into dma_in_buf with the DMA batch header.
 *
 * Channels:
 *  c[0..2]  : R, G, B
 *  c[3]     : Luminance (0.299*R + 0.587*G + 0.114*B)
 *  c[4]     : |R - G|
 *  c[5]     : |G - B|
 *  c[6]     : |R - B|
 *  c[7..9]  : 255 - R, 255 - G, 255 - B
 *  c[10..15]: (c[0..5] >> 1) + 64
 *
 * @param rgb_in      Input buffer: 32 * 32 * 3 uint8 (H, W, 3)
 * @param dma_in_buf  Output buffer: 1 + 1024 * 4 uint32 words
 * @param H           Height (typically 32)
 * @param W           Width (typically 32)
 * @return int        Total 32-bit words written (1 + H * W * 4)
 */
int c_preprocess_and_pack_input(
    const uint8_t *rgb_in,
    uint32_t *dma_in_buf,
    int H,
    int W
);

/**
 * @brief Requantize 16-bit signed hardware accumulators into 8-bit unipolar ReLU activations.
 *
 * Formula:
 *   out[t][c] = clamp(((raw_acc[t][c] + bias[c]) * mult[c]) >> shift, 0, 255)
 *
 * Vectorized using 128-bit SIMD (ARM NEON or compiler autovectorization).
 *
 * @param raw_acc    Input raw accumulators from DMA: num_tiles * 16 signed 16-bit
 * @param out_acts   Output activations: num_tiles * 16 unsigned 8-bit
 * @param bias       16-element signed 32-bit biases
 * @param mult       16-element signed 32-bit scale multipliers
 * @param shift      Bit shift (typically 8..11)
 * @param num_tiles  Number of spatial tiles (e.g. 1024, 256)
 */
void c_requantize_relu_16b_to_8b(
    const int16_t *raw_acc,
    uint8_t *out_acts,
    const int32_t *bias,
    const int32_t *mult,
    int shift,
    int num_tiles
);

/**
 * @brief Fast 3x3 depthwise box smoothing with replicated edge padding.
 *
 * Computes:
 *   out[y][x][c] = (sum_{dy, dx in {-1, 0, 1}} in[clamp(y+dy)][clamp(x+dx)][c]) / 9
 *
 * Processes contiguous NHWC memory lines fitting inside the 32 KB L1 data cache.
 *
 * @param in_acts   Input NHWC activations: H * W * 16 uint8
 * @param out_acts  Output NHWC activations: H * W * 16 uint8
 * @param H         Height (e.g. 32)
 * @param W         Width (e.g. 32)
 */
void c_depthwise_smooth_3x3(
    const uint8_t *in_acts,
    uint8_t *out_acts,
    int H,
    int W
);

/**
 * @brief Fused residual shortcut addition and 2x2 max-pooling.
 *
 * Performs:
 *   res[y][x][c] = (shortcut[y][x][c] + conv_out[y][x][c]) / 2
 * Followed immediately by 2x2 max-pooling with stride 2 directly into output.
 * Avoids writing the intermediate unpooled tensor to memory.
 *
 * @param res_shortcut  Input shortcut activations: H * W * 16 uint8
 * @param res_conv_out  Input residual conv activations: H * W * 16 uint8
 * @param pooled_out    Output pooled activations: (H/2) * (W/2) * 16 uint8
 * @param H             Input height (e.g. 32 or 16)
 * @param W             Input width (e.g. 32 or 16)
 */
void c_fused_residual_add_and_maxpool2x2(
    const uint8_t *res_shortcut,
    const uint8_t *res_conv_out,
    uint8_t *pooled_out,
    int H,
    int W
);

/**
 * @brief Pack arbitrary NHWC uint8 activations into an AXI-DMA input buffer.
 *
 * Writes DMA header: (SCIM_CMD_MVM_BATCH << 24) | num_tiles
 * Followed by num_tiles * 4 uint32 words (16 bytes per tile).
 *
 * @param in_acts     Input NHWC activations: num_tiles * 16 uint8
 * @param dma_in_buf  Output DMA buffer: 1 + num_tiles * 4 uint32 words
 * @param num_tiles   Number of spatial tiles (H * W)
 * @return int        Total 32-bit words written (1 + num_tiles * 4)
 */
int c_pack_dma_input(
    const uint8_t *in_acts,
    uint32_t *dma_in_buf,
    int num_tiles
);

/**
 * @brief Global Average Pooling (GAP) and Dense Linear Classifier.
 *
 * Computes:
 *   gap[c] = (sum_{y, x} in_acts[y][x][c]) / 64
 *   logits[k] = sum_{c=0..15} (gap[c] * weights[c][k]) + biases[k]
 *
 * @param in_acts     Input feature map: 8 * 8 * 16 uint8 (NHWC)
 * @param weights     16 x 16 classifier weights (signed 32-bit)
 * @param biases      16-element classifier biases (signed 32-bit)
 * @param out_logits  Output logits array: at least num_classes int32
 * @param num_classes Number of target classes (e.g. 10 or 4)
 * @return int        Predicted top-1 class index (argmax)
 */
int c_gap_and_classify(
    const uint8_t *in_acts,
    const int32_t *weights,
    const int32_t *biases,
    int32_t *out_logits,
    int num_classes
);

#ifdef __cplusplus
}
#endif

#endif /* SCIM_TIER3_ACCEL_H */
