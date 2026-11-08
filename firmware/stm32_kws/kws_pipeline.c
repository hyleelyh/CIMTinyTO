/**
 * @file kws_pipeline.c
 * @brief End-to-End Voice Keyword Spotting Pipeline Implementation.
 */

#include "kws_pipeline.h"
#include <string.h>

static KWSConfig_t s_config;
static bool s_configured = false;

void kws_pipeline_init(const KWSConfig_t *config) {
    memcpy(&s_config, config, sizeof(KWSConfig_t));
    kws_mfcc_init();
    scim_coprocessor_init();
    s_configured = true;
}

int kws_pipeline_run(const KWSConfig_t *config, const int16_t *pcm_audio, int32_t logits_out[SCIM_COLS]) {
    const KWSConfig_t *cfg = config ? config : &s_config;
    if (!config && !s_configured) {
        return -1;
    }

    /* 1. Acoustic Frontend: 16-channel Mel-filterbank spectrogram */
    uint8_t spec[SCIM_ROWS][SCIM_NUM_FRAMES];
    kws_mfcc_extract_spectrogram(pcm_audio, KWS_SAMPLE_RATE, spec);

    /* 2. Layer 1 (SCIM Tile 0): Stationary acoustic projection */
    scim_load_weights(cfg->tile0_weights);
    uint8_t feat1[SCIM_COLS][SCIM_NUM_FRAMES];
    scim_execute_stationary_layer(spec, cfg->tile0_mult, cfg->tile0_bias, cfg->tile0_shift, feat1);

    /* 3. Host DSP: 3-tap temporal smoothing */
    uint8_t feat1_smooth[SCIM_COLS][SCIM_NUM_FRAMES];
    scim_depthwise_smoothing_3tap(feat1, feat1_smooth);

    /* 4. Layer 2 (SCIM Tile 1): Stationary acoustic mixing */
    scim_load_weights(cfg->tile1_weights);
    uint8_t feat2[SCIM_COLS][SCIM_NUM_FRAMES];
    scim_execute_stationary_layer(feat1_smooth, cfg->tile1_mult, cfg->tile1_bias, cfg->tile1_shift, feat2);

    /* 5. Host DSP: Global Temporal Average Pooling (GAP) */
    uint8_t gap_vec[SCIM_ROWS];
    scim_global_average_pool(feat2, gap_vec);

    /* 6. Classifier Head (SCIM Tile 2): Dense linear projection */
    scim_classify_head(gap_vec, cfg->classifier_weights, cfg->classifier_biases, cfg->num_classes, logits_out);

    /* 7. Argmax decision */
    int best_idx = 0;
    int32_t max_logit = logits_out[0];
    for (int k = 1; k < cfg->num_classes; k++) {
        if (logits_out[k] > max_logit) {
            max_logit = logits_out[k];
            best_idx = k;
        }
    }

    return best_idx;
}

const char* kws_pipeline_get_class_name(const KWSConfig_t *config, int class_idx) {
    const KWSConfig_t *cfg = config ? config : &s_config;
    if (class_idx >= 0 && class_idx < cfg->num_classes) {
        return cfg->class_names[class_idx];
    }
    return "unknown";
}
