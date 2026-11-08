/**
 * @file kws_mfcc.c
 * @brief High-Performance 16-Channel Mel Filterbank Extraction in C99.
 *
 * Supports both ARM Cortex-M33 (CMSIS-DSP) and Native Host testing (x86-64 / ARMv7-A).
 */

#include "kws_mfcc.h"
#include <math.h>
#include <string.h>
#include <stdio.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* Pre-computed Hann window for 480 samples */
static float s_hann_window[KWS_FRAME_LEN];
static int s_initialized = 0;

/* Triangular Mel Filterbank parameters */
typedef struct {
    int left_bin;
    int center_bin;
    int right_bin;
    float norm_factor;
} MelFilter_t;

static MelFilter_t s_mel_filters[KWS_NUM_MEL_BINS];

static float hz_to_mel(float f_hz) {
    return 2595.0f * log10f(1.0f + f_hz / 700.0f);
}

static float mel_to_hz(float mel) {
    return 700.0f * (powf(10.0f, mel / 2595.0f) - 1.0f);
}

void kws_mfcc_init(void) {
    if (s_initialized) return;

    /* 1. Generate Hann window: w(n) = 0.5 - 0.5 * cos(2*pi*n / (N-1)) */
    for (int n = 0; n < KWS_FRAME_LEN; n++) {
        s_hann_window[n] = 0.5f - 0.5f * cosf(2.0f * (float)M_PI * (float)n / (float)(KWS_FRAME_LEN - 1));
    }

    /* 2. Generate 16 Mel Filterbank bin boundaries (50 Hz to 4000 Hz) */
    float mel_min = hz_to_mel(50.0f);
    float mel_max = hz_to_mel(4000.0f);
    float mel_step = (mel_max - mel_min) / (float)(KWS_NUM_MEL_BINS + 1);

    int bin_pts[KWS_NUM_MEL_BINS + 2];
    for (int i = 0; i < KWS_NUM_MEL_BINS + 2; i++) {
        float mel = mel_min + (float)i * mel_step;
        float hz = mel_to_hz(mel);
        int bin = (int)floorf((float)(KWS_FFT_SIZE + 1) * hz / (float)KWS_SAMPLE_RATE);
        if (bin < 0) bin = 0;
        if (bin > (KWS_FFT_SIZE / 2)) bin = KWS_FFT_SIZE / 2;
        bin_pts[i] = bin;
    }

    for (int m = 0; m < KWS_NUM_MEL_BINS; m++) {
        s_mel_filters[m].left_bin   = bin_pts[m];
        s_mel_filters[m].center_bin = bin_pts[m + 1];
        s_mel_filters[m].right_bin  = bin_pts[m + 2];

        /* Calculate triangle area for normalization */
        float area = 0.0f;
        int l = s_mel_filters[m].left_bin;
        int c = s_mel_filters[m].center_bin;
        int r = s_mel_filters[m].right_bin;

        if (c > l) {
            for (int k = l; k < c; k++) {
                area += (float)(k - l) / (float)(c - l);
            }
        }
        if (r > c) {
            for (int k = c; k <= r; k++) {
                area += (float)(r - k) / (float)(r - c);
            }
        }
        s_mel_filters[m].norm_factor = (area > 1e-6f) ? (1.0f / area) : 1.0f;
    }

    s_initialized = 1;
}

/* Fast Real FFT for 512 points */
static void compute_rfft_512(const float *input_480, float *power_spectrum_257) {
    /* Zero-padded 512-point buffer */
    float real[KWS_FFT_SIZE];
    float imag[KWS_FFT_SIZE];

    for (int i = 0; i < KWS_FRAME_LEN; i++) {
        real[i] = input_480[i];
        imag[i] = 0.0f;
    }
    for (int i = KWS_FRAME_LEN; i < KWS_FFT_SIZE; i++) {
        real[i] = 0.0f;
        imag[i] = 0.0f;
    }

    /* Standard Cooley-Tukey Radix-2 Decimation-in-Time FFT */
    int n = KWS_FFT_SIZE;
    int j = 0;
    for (int i = 0; i < n - 1; i++) {
        if (i < j) {
            float tr = real[i]; real[i] = real[j]; real[j] = tr;
            float ti = imag[i]; imag[i] = imag[j]; imag[j] = ti;
        }
        int k = n / 2;
        while (k <= j) {
            j -= k;
            k /= 2;
        }
        j += k;
    }

    for (int len = 2; len <= n; len <<= 1) {
        float angle = -2.0f * (float)M_PI / (float)len;
        float wlen_r = cosf(angle);
        float wlen_i = sinf(angle);
        int half_len = len >> 1;

        for (int i = 0; i < n; i += len) {
            float w_r = 1.0f;
            float w_i = 0.0f;
            for (int k = 0; k < half_len; k++) {
                int u = i + k;
                int v = i + k + half_len;
                float vr = real[v] * w_r - imag[v] * w_i;
                float vi = real[v] * w_i + imag[v] * w_r;

                real[v] = real[u] - vr;
                imag[v] = imag[u] - vi;
                real[u] = real[u] + vr;
                imag[u] = imag[u] + vi;

                float next_wr = w_r * wlen_r - w_i * wlen_i;
                float next_wi = w_r * wlen_i + w_i * wlen_r;
                w_r = next_wr;
                w_i = next_wi;
            }
        }
    }

    /* Power spectrum: P(k) = (real^2 + imag^2) / 512 */
    float inv_n = 1.0f / (float)KWS_FFT_SIZE;
    for (int k = 0; k < 257; k++) {
        power_spectrum_257[k] = (real[k] * real[k] + imag[k] * imag[k]) * inv_n;
    }
}

void kws_mfcc_compute_frame(const int16_t *pcm_frame, float *mel_out_16) {
    if (!s_initialized) {
        kws_mfcc_init();
    }

    /* 1. Apply Hann window and scale from int16 to normalized float [-1.0, 1.0] */
    float windowed[KWS_FRAME_LEN];
    for (int i = 0; i < KWS_FRAME_LEN; i++) {
        windowed[i] = ((float)pcm_frame[i] / 32768.0f) * s_hann_window[i];
    }

    /* 2. 512-point Real FFT and Power Spectrum */
    float power_spec[257];
    compute_rfft_512(windowed, power_spec);

    /* 3. Mel Filterbank Dot Products & Log Compression */
    for (int m = 0; m < KWS_NUM_MEL_BINS; m++) {
        int l = s_mel_filters[m].left_bin;
        int c = s_mel_filters[m].center_bin;
        int r = s_mel_filters[m].right_bin;
        float energy = 0.0f;

        if (c > l) {
            for (int k = l; k < c; k++) {
                float weight = (float)(k - l) / (float)(c - l);
                energy += power_spec[k] * weight;
            }
        }
        if (r > c) {
            for (int k = c; k <= r; k++) {
                float weight = (float)(r - k) / (float)(r - c);
                energy += power_spec[k] * weight;
            }
        }

        energy *= s_mel_filters[m].norm_factor;

        /* Log10 compression with epsilon = 1e-6 */
        mel_out_16[m] = log10f(energy + 1e-6f);
    }
}

void kws_mfcc_extract_spectrogram(
    const int16_t *pcm_audio,
    size_t total_samples,
    uint8_t spec_uint8_16x32[KWS_NUM_MEL_BINS][KWS_NUM_FRAMES]
) {
    if (!s_initialized) {
        kws_mfcc_init();
    }

    float raw_spec[KWS_NUM_MEL_BINS][KWS_NUM_FRAMES];
    float max_val = -1000.0f;

    /* Extract 32 frames */
    for (int t = 0; t < KWS_NUM_FRAMES; t++) {
        size_t offset = (size_t)t * KWS_FRAME_HOP;
        int16_t frame_buf[KWS_FRAME_LEN];

        if (offset + KWS_FRAME_LEN <= total_samples) {
            memcpy(frame_buf, &pcm_audio[offset], KWS_FRAME_LEN * sizeof(int16_t));
        } else {
            /* Zero-pad boundary */
            size_t available = (offset < total_samples) ? (total_samples - offset) : 0;
            if (available > 0) {
                memcpy(frame_buf, &pcm_audio[offset], available * sizeof(int16_t));
            }
            memset(&frame_buf[available], 0, (KWS_FRAME_LEN - available) * sizeof(int16_t));
        }

        float mel_16[KWS_NUM_MEL_BINS];
        kws_mfcc_compute_frame(frame_buf, mel_16);

        for (int m = 0; m < KWS_NUM_MEL_BINS; m++) {
            raw_spec[m][t] = mel_16[m];
            if (mel_16[m] > max_val) {
                max_val = mel_16[m];
            }
        }
    }

    /* Silence gating threshold: -3.0 in log10 power is -30 dB */
    if (max_val < -3.0f) {
        memset(spec_uint8_16x32, 0, KWS_NUM_MEL_BINS * KWS_NUM_FRAMES * sizeof(uint8_t));
        return;
    }

    /* Normalize dynamic range (60 dB = 6.0 in log10 domain) */
    float min_val = max_val - 6.0f;
    float range_inv = 1.0f / (max_val - min_val + 1e-9f);

    for (int m = 0; m < KWS_NUM_MEL_BINS; m++) {
        for (int t = 0; t < KWS_NUM_FRAMES; t++) {
            float norm = (raw_spec[m][t] - min_val) * range_inv;
            if (norm < 0.0f) norm = 0.0f;
            if (norm > 1.0f) norm = 1.0f;
            spec_uint8_16x32[m][t] = (uint8_t)(roundf(norm * 255.0f));
        }
    }
}
