/**
 * @file kws_mfcc.h
 * @brief 16-Channel Mel-Filterbank Feature Extraction for STM32 B-U585I-IOT02A & CIMTinyTO.
 *
 * Microarchitecture:
 * - Sampling Rate: 16 kHz, 16-bit signed PCM audio.
 * - Window: 480 samples (30 ms) with Hann windowing.
 * - Hop: 320 samples (20 ms frame advancement).
 * - FFT: 512-point Real FFT.
 * - Filterbank: 16 triangular Mel filters (50 Hz to 4000 Hz).
 * - Output: uint8_t spectrogram of shape (16 channels, 32 temporal frames) in [0, 255].
 */

#ifndef KWS_MFCC_H
#define KWS_MFCC_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define KWS_SAMPLE_RATE         16000
#define KWS_FRAME_LEN           480    /* 30 ms @ 16 kHz */
#define KWS_FRAME_HOP           320    /* 20 ms @ 16 kHz */
#define KWS_FFT_SIZE            512
#define KWS_NUM_MEL_BINS        16     /* Exact 1:1 match with 16x16 SCIM array */
#define KWS_NUM_FRAMES          32     /* ~650 ms temporal window */

/**
 * @brief Initialize Hann window, Mel filterbank weights, and FFT tables.
 */
void kws_mfcc_init(void);

/**
 * @brief Process single 480-sample audio frame and extract 16 Mel energy bins.
 * @param[in]  pcm_frame   Pointer to 480 signed 16-bit PCM samples.
 * @param[out] mel_out_16  Pointer to output buffer of 16 float log-energies.
 */
void kws_mfcc_compute_frame(const int16_t *pcm_frame, float *mel_out_16);

/**
 * @brief Extract full 16x32 Mel-spectrogram from 1-second PCM audio buffer.
 * @param[in]  pcm_audio        Pointer to 16,000 signed 16-bit PCM samples.
 * @param[in]  total_samples    Number of samples in buffer (minimum 10,400 for 32 frames).
 * @param[out] spec_uint8_16x32 Output 16x32 array of quantized uint8_t activations.
 */
void kws_mfcc_extract_spectrogram(
    const int16_t *pcm_audio,
    size_t total_samples,
    uint8_t spec_uint8_16x32[KWS_NUM_MEL_BINS][KWS_NUM_FRAMES]
);

#ifdef __cplusplus
}
#endif

#endif /* KWS_MFCC_H */
