/**
 * @file kws_pipeline.h
 * @brief End-to-End Voice Keyword Spotting Pipeline for STM32 B-U585I-IOT02A.
 */

#ifndef KWS_PIPELINE_H
#define KWS_PIPELINE_H

#include "kws_mfcc.h"
#include "scim_coprocessor.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int num_classes;
    char class_names[16][16];
    int8_t tile0_weights[SCIM_ROWS][SCIM_COLS];
    int32_t tile0_mult[SCIM_COLS];
    int32_t tile0_bias[SCIM_COLS];
    int tile0_shift;

    int8_t tile1_weights[SCIM_ROWS][SCIM_COLS];
    int32_t tile1_mult[SCIM_COLS];
    int32_t tile1_bias[SCIM_COLS];
    int tile1_shift;

    int8_t classifier_weights[SCIM_COLS][SCIM_ROWS];
    int32_t classifier_biases[SCIM_COLS];
} KWSConfig_t;

/**
 * @brief Initialize pipeline with model configuration weights.
 */
void kws_pipeline_init(const KWSConfig_t *config);

/**
 * @brief Run complete end-to-end inference on 1-second 16 kHz audio buffer.
 * @param[in]  config     Pointer to model configuration (or NULL to use last initialized).
 * @param[in]  pcm_audio  Pointer to 16,000 signed 16-bit PCM samples.
 * @param[out] logits_out Array of class logits.
 * @return Index of predicted keyword class.
 */
int kws_pipeline_run(const KWSConfig_t *config, const int16_t *pcm_audio, int32_t logits_out[SCIM_COLS]);

/**
 * @brief Get human-readable keyword name for class index.
 */
const char* kws_pipeline_get_class_name(const KWSConfig_t *config, int class_idx);

#ifdef __cplusplus
}
#endif

#endif /* KWS_PIPELINE_H */
