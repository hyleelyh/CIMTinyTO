/* ============================================================================
 * Source: scim_tier3_accel.c
 * Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
 * Target: AMD Xilinx Zynq-7020 (PYNQ-Z2 ARM Cortex-A9) & Host Emulation (Pillar 6.1)
 * Standard: C99 / POSIX Shared Library
 * ============================================================================
 */

#include "scim_tier3_accel.h"
#include <string.h>
#include <stdlib.h>

#if defined(__ARM_NEON) || defined(__ARM_NEON__)
#include <arm_neon.h>
#define USE_NEON 1
#else
#define USE_NEON 0
#endif

/* ----------------------------------------------------------------------------
 * Kernel 1: Fast Input Ingestion & CMA Buffer Packing
 * ----------------------------------------------------------------------------
 */
int c_preprocess_and_pack_input(
    const uint8_t *rgb_in,
    uint32_t *dma_in_buf,
    int H,
    int W
) {
    if (!rgb_in || !dma_in_buf || H <= 0 || W <= 0) {
        return -1;
    }

    int num_tiles = H * W;
    /* Command Header Word: [31:24] = CMD_MVM_BATCH (0x03), [15:0] = num_tiles */
    dma_in_buf[0] = (uint32_t)((SCIM_CMD_MVM_BATCH << 24) | (num_tiles & 0xFFFF));

    uint8_t *dst_bytes = (uint8_t *)(&dma_in_buf[1]);

    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            int src_idx = (y * W + x) * 3;
            uint8_t r = rgb_in[src_idx + 0];
            uint8_t g = rgb_in[src_idx + 1];
            uint8_t b = rgb_in[src_idx + 2];

            /* Channel 3: Luminance in uint8 matching Python:
             * np.clip(0.299*r + 0.587*g + 0.114*b, 0, 255).astype(np.uint8)
             */
            float lum_f = 0.299f * (float)r + 0.587f * (float)g + 0.114f * (float)b;
            if (lum_f < 0.0f) lum_f = 0.0f;
            else if (lum_f > 255.0f) lum_f = 255.0f;
            uint8_t lum = (uint8_t)lum_f;

            /* Channels 4..6: Color differences |R-G|, |G-B|, |R-B| */
            uint8_t diff_rg = (r >= g) ? (r - g) : (g - r);
            uint8_t diff_gb = (g >= b) ? (g - b) : (b - g);
            uint8_t diff_rb = (r >= b) ? (r - b) : (b - r);

            /* Channels 7..9: Inverted channels */
            uint8_t inv_r = (uint8_t)(255 - r);
            uint8_t inv_g = (uint8_t)(255 - g);
            uint8_t inv_b = (uint8_t)(255 - b);

            /* Channels 10..15: Shifted channels (feat[c - 10] // 2) + 64 */
            uint8_t c10 = (uint8_t)((r >> 1) + 64);
            uint8_t c11 = (uint8_t)((g >> 1) + 64);
            uint8_t c12 = (uint8_t)((b >> 1) + 64);
            uint8_t c13 = (uint8_t)((lum >> 1) + 64);
            uint8_t c14 = (uint8_t)((diff_rg >> 1) + 64);
            uint8_t c15 = (uint8_t)((diff_gb >> 1) + 64);

            int dst_tile = (y * W + x) * 16;
            dst_bytes[dst_tile + 0]  = r;
            dst_bytes[dst_tile + 1]  = g;
            dst_bytes[dst_tile + 2]  = b;
            dst_bytes[dst_tile + 3]  = lum;
            dst_bytes[dst_tile + 4]  = diff_rg;
            dst_bytes[dst_tile + 5]  = diff_gb;
            dst_bytes[dst_tile + 6]  = diff_rb;
            dst_bytes[dst_tile + 7]  = inv_r;
            dst_bytes[dst_tile + 8]  = inv_g;
            dst_bytes[dst_tile + 9]  = inv_b;
            dst_bytes[dst_tile + 10] = c10;
            dst_bytes[dst_tile + 11] = c11;
            dst_bytes[dst_tile + 12] = c12;
            dst_bytes[dst_tile + 13] = c13;
            dst_bytes[dst_tile + 14] = c14;
            dst_bytes[dst_tile + 15] = c15;
        }
    }

    return 1 + (num_tiles * 4);
}

/* ----------------------------------------------------------------------------
 * Kernel 2: Vectorized Requantization & ReLU (16-bit -> 8-bit)
 * ----------------------------------------------------------------------------
 */
void c_requantize_relu_16b_to_8b(
    const int16_t *raw_acc,
    uint8_t *out_acts,
    const int32_t *bias,
    const int32_t *mult,
    int shift,
    int num_tiles
) {
    if (!raw_acc || !out_acts || !bias || !mult || num_tiles <= 0) {
        return;
    }

    for (int t = 0; t < num_tiles; t++) {
        const int16_t *tile_in = &raw_acc[t * 16];
        uint8_t *tile_out = &out_acts[t * 16];

#if USE_NEON
        /* Process 16 channels in two 8-channel NEON chunks */
        for (int chunk = 0; chunk < 2; chunk++) {
            int offset = chunk * 8;
            int16x8_t in_vec = vld1q_s16(&tile_in[offset]);

            /* Split 8 int16 values into two 4-element int32 vectors */
            int32x4_t in_low = vmovl_s16(vget_low_s16(in_vec));
            int32x4_t in_high = vmovl_s16(vget_high_s16(in_vec));

            int32x4_t b_low = vld1q_s32(&bias[offset]);
            int32x4_t b_high = vld1q_s32(&bias[offset + 4]);

            int32x4_t m_low = vld1q_s32(&mult[offset]);
            int32x4_t m_high = vld1q_s32(&mult[offset + 4]);

            int32x4_t sum_low = vaddq_s32(in_low, b_low);
            int32x4_t sum_high = vaddq_s32(in_high, b_high);

            int32x4_t prod_low = vmulq_s32(sum_low, m_low);
            int32x4_t prod_high = vmulq_s32(sum_high, m_high);

            /* Right shift (shift must be a constant or variable vector) */
            int32x4_t shift_vec = vdupq_n_s32(-shift);
            int32x4_t shifted_low = vshlq_s32(prod_low, shift_vec);
            int32x4_t shifted_high = vshlq_s32(prod_high, shift_vec);

            /* Saturate down to 16-bit, then unsigned 8-bit */
            int16x4_t narrow_low = vqmovn_s32(shifted_low);
            int16x4_t narrow_high = vqmovn_s32(shifted_high);
            int16x8_t narrow_16 = vcombine_s16(narrow_low, narrow_high);

            uint8x8_t clamped_u8 = vqmovun_s16(narrow_16);
            vst1_u8(&tile_out[offset], clamped_u8);
        }
#else
        for (int c = 0; c < 16; c++) {
            int64_t val = ((int64_t)tile_in[c] + (int64_t)bias[c]) * (int64_t)mult[c];
            val >>= shift;
            if (val < 0) {
                val = 0;
            } else if (val > 255) {
                val = 255;
            }
            tile_out[c] = (uint8_t)val;
        }
#endif
    }
}

/* ----------------------------------------------------------------------------
 * Kernel 3: Depthwise 3x3 Box Smoothing Filter with Edge Padding
 * ----------------------------------------------------------------------------
 */
void c_depthwise_smooth_3x3(
    const uint8_t *in_acts,
    uint8_t *out_acts,
    int H,
    int W
) {
    if (!in_acts || !out_acts || H <= 0 || W <= 0) {
        return;
    }

    for (int y = 0; y < H; y++) {
        int y_prev = (y > 0) ? (y - 1) : 0;
        int y_next = (y < H - 1) ? (y + 1) : (H - 1);

        const uint8_t *row_prev = &in_acts[y_prev * W * 16];
        const uint8_t *row_curr = &in_acts[y * W * 16];
        const uint8_t *row_next = &in_acts[y_next * W * 16];
        uint8_t *row_out = &out_acts[y * W * 16];

        for (int x = 0; x < W; x++) {
            int x_prev = (x > 0) ? (x - 1) : 0;
            int x_next = (x < W - 1) ? (x + 1) : (W - 1);

            const uint8_t *p00 = &row_prev[x_prev * 16];
            const uint8_t *p01 = &row_prev[x * 16];
            const uint8_t *p02 = &row_prev[x_next * 16];

            const uint8_t *p10 = &row_curr[x_prev * 16];
            const uint8_t *p11 = &row_curr[x * 16];
            const uint8_t *p12 = &row_curr[x_next * 16];

            const uint8_t *p20 = &row_next[x_prev * 16];
            const uint8_t *p21 = &row_next[x * 16];
            const uint8_t *p22 = &row_next[x_next * 16];

            uint8_t *dst = &row_out[x * 16];

            for (int c = 0; c < 16; c++) {
                uint16_t sum = (uint16_t)p00[c] + (uint16_t)p01[c] + (uint16_t)p02[c] +
                               (uint16_t)p10[c] + (uint16_t)p11[c] + (uint16_t)p12[c] +
                               (uint16_t)p20[c] + (uint16_t)p21[c] + (uint16_t)p22[c];
                uint16_t avg = sum / 9;
                dst[c] = (uint8_t)((avg > 255) ? 255 : avg);
            }
        }
    }
}

/* ----------------------------------------------------------------------------
 * Kernel 4: Fused Residual Halving Addition and 2x2 Max-Pooling
 * ----------------------------------------------------------------------------
 */
void c_fused_residual_add_and_maxpool2x2(
    const uint8_t *res_shortcut,
    const uint8_t *res_conv_out,
    uint8_t *pooled_out,
    int H,
    int W
) {
    if (!res_shortcut || !res_conv_out || !pooled_out || H <= 0 || W <= 0) {
        return;
    }

    int out_H = H / 2;
    int out_W = W / 2;

    for (int py = 0; py < out_H; py++) {
        int y0 = py * 2;
        int y1 = py * 2 + 1;

        const uint8_t *s_row0 = &res_shortcut[y0 * W * 16];
        const uint8_t *s_row1 = &res_shortcut[y1 * W * 16];
        const uint8_t *c_row0 = &res_conv_out[y0 * W * 16];
        const uint8_t *c_row1 = &res_conv_out[y1 * W * 16];
        uint8_t *out_row = &pooled_out[py * out_W * 16];

        for (int px = 0; px < out_W; px++) {
            int x0 = px * 2;
            int x1 = px * 2 + 1;

            const uint8_t *s00 = &s_row0[x0 * 16];
            const uint8_t *s01 = &s_row0[x1 * 16];
            const uint8_t *s10 = &s_row1[x0 * 16];
            const uint8_t *s11 = &s_row1[x1 * 16];

            const uint8_t *c00 = &c_row0[x0 * 16];
            const uint8_t *c01 = &c_row0[x1 * 16];
            const uint8_t *c10 = &c_row1[x0 * 16];
            const uint8_t *c11 = &c_row1[x1 * 16];

            uint8_t *dst = &out_row[px * 16];

#if USE_NEON
            /* Process 16 channels in one 128-bit vector */
            uint8x16_t s00_v = vld1q_u8(s00);
            uint8x16_t c00_v = vld1q_u8(c00);
            uint8x16_t v00_v = vrhaddq_u8(s00_v, c00_v);

            uint8x16_t s01_v = vld1q_u8(s01);
            uint8x16_t c01_v = vld1q_u8(c01);
            uint8x16_t v01_v = vrhaddq_u8(s01_v, c01_v);

            uint8x16_t s10_v = vld1q_u8(s10);
            uint8x16_t c10_v = vld1q_u8(c10);
            uint8x16_t v10_v = vrhaddq_u8(s10_v, c10_v);

            uint8x16_t s11_v = vld1q_u8(s11);
            uint8x16_t c11_v = vld1q_u8(c11);
            uint8x16_t v11_v = vrhaddq_u8(s11_v, c11_v);

            uint8x16_t max0 = vmaxq_u8(v00_v, v01_v);
            uint8x16_t max1 = vmaxq_u8(v10_v, v11_v);
            uint8x16_t final_max = vmaxq_u8(max0, max1);

            vst1q_u8(dst, final_max);
#else
            for (int c = 0; c < 16; c++) {
                uint8_t v00 = (uint8_t)(((int)s00[c] + (int)c00[c]) / 2);
                uint8_t v01 = (uint8_t)(((int)s01[c] + (int)c01[c]) / 2);
                uint8_t v10 = (uint8_t)(((int)s10[c] + (int)c10[c]) / 2);
                uint8_t v11 = (uint8_t)(((int)s11[c] + (int)c11[c]) / 2);

                uint8_t m0 = (v00 >= v01) ? v00 : v01;
                uint8_t m1 = (v10 >= v11) ? v10 : v11;
                dst[c] = (m0 >= m1) ? m0 : m1;
            }
#endif
        }
    }
}

/* ----------------------------------------------------------------------------
 * Kernel 5: Arbitrary NHWC Activation Packing into AXI-DMA Buffer
 * ----------------------------------------------------------------------------
 */
int c_pack_dma_input(
    const uint8_t *in_acts,
    uint32_t *dma_in_buf,
    int num_tiles
) {
    if (!in_acts || !dma_in_buf || num_tiles <= 0) {
        return -1;
    }

    dma_in_buf[0] = (uint32_t)((SCIM_CMD_MVM_BATCH << 24) | (num_tiles & 0xFFFF));
    memcpy(&dma_in_buf[1], in_acts, (size_t)num_tiles * 16);
    return 1 + (num_tiles * 4);
}

/* ----------------------------------------------------------------------------
 * Kernel 6: Global Average Pooling (GAP) and Linear Classifier Head
 * ----------------------------------------------------------------------------
 */
int c_gap_and_classify(
    const uint8_t *in_acts,
    const int32_t *weights,
    const int32_t *biases,
    int32_t *out_logits,
    int num_classes
) {
    if (!in_acts || !weights || !biases || num_classes <= 0) {
        return -1;
    }

    /* Compute 16-channel spatial mean over 8x8 = 64 spatial positions */
    uint32_t channel_sums[16] = {0};
    for (int i = 0; i < 64; i++) {
        const uint8_t *tile = &in_acts[i * 16];
        for (int c = 0; c < 16; c++) {
            channel_sums[c] += tile[c];
        }
    }

    uint8_t gap[16];
    for (int c = 0; c < 16; c++) {
        /* Integer division by 64 is bit-exact to Python np.mean().astype(np.uint8) */
        gap[c] = (uint8_t)(channel_sums[c] / 64);
    }

    int best_class = 0;
    int32_t best_logit = -2147483647;

    for (int k = 0; k < num_classes; k++) {
        int32_t dot = 0;
        for (int c = 0; c < 16; c++) {
            /* Classifier weights are stored as shape (16, 16) row-major: weights[c * 16 + k] */
            dot += (int32_t)gap[c] * weights[c * 16 + k];
        }
        int32_t logit = dot + biases[k];
        if (out_logits) {
            out_logits[k] = logit;
        }
        if (logit > best_logit) {
            best_logit = logit;
            best_class = k;
        }
    }

    return best_class;
}
