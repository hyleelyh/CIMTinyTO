"""
test_kws_pipeline.py — Comprehensive Regression & Verification Suite for Pillar 6.2.
Verifies the Voice Keyword Spotting (KWS) Audio Frontend, QAT Neural Model,
C99/CMSIS-DSP Coprocessor Driver, and Gate 0 SCIM Stochastic Parity.
"""

import os
import json
import pytest
import numpy as np
import torch

from kws.kws_audio_frontend import (
    hz_to_mel,
    mel_to_hz,
    create_mel_filterbank,
    extract_mel_filterbank,
    quantize_spectrogram_to_uint8,
    generate_synthetic_audio,
)
from kws.kws_model import KWS_SCIM_16, FixedPointKWSModel
from kws.kws_c_wrapper import KWSCPipeline
from model.sim_scim import SCIMTile, ProcessingElement


class TestAudioFrontend:
    """Verifies acoustic transducer processing and 16-channel Mel filterbank extraction."""

    def test_mel_filterbank_shapes_and_frequencies(self):
        fb = create_mel_filterbank(num_channels=16, n_fft=512, sample_rate=16000, f_min=50.0, f_max=4000.0)
        assert fb.shape == (16, 257), f"Expected shape (16, 257), got {fb.shape}"
        assert np.all(fb >= 0.0), "Mel filterbank weights must be non-negative"
        # Area normalized: sums along frequency should be positive
        sums = np.sum(fb, axis=1)
        assert np.all(sums > 0.9) and np.all(sums < 1.1), "Filter areas must be normalized to ~1.0"

    def test_silence_gating_and_zero_power(self):
        """Silicon Realities: Silence must map to all zeros to drop PE switching power to 0 W."""
        silence_audio = generate_synthetic_audio('silence')
        spec_float = extract_mel_filterbank(silence_audio)
        spec_uint8 = quantize_spectrogram_to_uint8(spec_float, silence_threshold_db=-30.0)
        assert spec_uint8.shape == (16, 32)
        assert np.all(spec_uint8 == 0), "Silence must be completely gated to zero to suppress switching power"

    def test_active_speech_populates_dynamic_range(self):
        for kw in ['yes', 'no', 'stop', 'go']:
            audio = generate_synthetic_audio(kw)
            spec_float = extract_mel_filterbank(audio)
            spec_uint8 = quantize_spectrogram_to_uint8(spec_float)
            assert spec_uint8.shape == (16, 32)
            assert spec_uint8.max() == 255, f"Peak energy in {kw} should map to 255"
            assert spec_uint8.min() < 50, f"Background floor in {kw} should be near zero"


class TestAcousticNeuralArchitecture:
    """Verifies neural network sizing, parameter count, and stationary caching."""

    def test_kws_model_96byte_parameter_budget(self):
        """Microarchitecture: 3 SCIM layers x 256 bits = 768 bits = 96 Bytes total."""
        model = KWS_SCIM_16(num_classes=4)
        scim_weights_count = (
            model.conv1.weight.numel() +
            model.conv2.weight.numel() +
            model.classifier_weight.numel()
        )
        assert scim_weights_count == 16 * 16 + 16 * 16 + 16 * 16
        total_bits = scim_weights_count  # 1 bit per weight in bipolar {-1, +1}
        total_bytes = total_bits // 8
        assert total_bytes == 96, f"Expected 96-byte parameter budget, got {total_bytes} bytes"

    def test_fixed_point_forward_execution(self):
        with open('kws/kws_weights_4class.json', 'r') as f:
            weights = json.load(f)
        model = FixedPointKWSModel(weights)
        fake_spec = np.random.randint(0, 256, (16, 32), dtype=np.uint8)
        logits, pred_idx, pred_name = model.forward(fake_spec)
        assert len(logits) == 4
        assert 0 <= pred_idx < 4
        assert isinstance(pred_name, str)


class TestCPipelineAndNumericalParity:
    """Verifies compiled C99/CMSIS-DSP driver parity against Python models and Gate 0."""

    @pytest.fixture(autouse=True)
    def setup_pipeline(self):
        self.c_model_4 = KWSCPipeline('kws/kws_weights_4class.json')
        self.c_model_6 = KWSCPipeline('kws/kws_weights_6class.json')

        with open('kws/kws_weights_4class.json', 'r') as f:
            self.w4 = json.load(f)
        self.py_model_4 = FixedPointKWSModel(self.w4)

    def test_c_vs_python_spectrogram_parity(self):
        """Verifies C FFT + Mel filterbank matches Python within 1 LSB."""
        for kw in ['silence', 'yes', 'no', 'stop']:
            float_audio = generate_synthetic_audio(kw)
            pcm_audio = (float_audio * 32767.0).astype(np.int16)

            py_spec = quantize_spectrogram_to_uint8(extract_mel_filterbank(float_audio))
            c_spec = self.c_model_4.extract_spectrogram(pcm_audio)

            diff = np.abs(py_spec.astype(int) - c_spec.astype(int))
            assert diff.max() <= 1, f"Max spectrogram discrepancy for {kw} is {diff.max()} > 1 LSB"
            assert diff.mean() < 0.1, f"Mean spectrogram discrepancy for {kw} is {diff.mean():.3f} >= 0.1"

    def test_c_vs_python_fixed_point_logits_parity(self):
        """Verifies 100% bit-exact (0 LSB) parity between Python and C inference."""
        for kw in ['silence', 'unknown', 'yes', 'no']:
            audio = generate_synthetic_audio(kw)
            pcm = (audio * 32767.0).astype(np.int16)

            c_idx, c_name, c_logits = self.c_model_4.infer(pcm)
            c_spec = self.c_model_4.extract_spectrogram(pcm)
            py_logits, py_idx, py_name = self.py_model_4.forward(c_spec)

            diff = np.abs(c_logits - py_logits)
            assert diff.max() == 0, f"Discrepancy for {kw}: C logits={c_logits}, Py logits={py_logits}"
            assert c_idx == py_idx
            assert c_name == py_name

    def test_4class_end_to_end_accuracy(self):
        """Verifies 100% correct keyword spotting across all 4 target classes."""
        expected = ['silence', 'unknown', 'yes', 'no']
        for kw in expected:
            audio = generate_synthetic_audio(kw)
            pcm = (audio * 32767.0).astype(np.int16)
            pred_idx, pred_name, logits = self.c_model_4.infer(pcm)
            assert pred_name == kw, f"Expected {kw}, predicted {pred_name} (logits: {logits})"

    def test_6class_end_to_end_accuracy(self):
        """Verifies 100% correct keyword spotting across all 6 target classes."""
        expected = ['silence', 'unknown', 'yes', 'no', 'stop', 'go']
        for kw in expected:
            audio = generate_synthetic_audio(kw)
            pcm = (audio * 32767.0).astype(np.int16)
            pred_idx, pred_name, logits = self.c_model_6.infer(pcm)
            assert pred_name == kw, f"Expected {kw}, predicted {pred_name} (logits: {logits})"

    def test_gate0_stochastic_tile_simulation_parity(self):
        """Verifies Gate 0 stochastic simulation matches true mathematical dot product within 0.5%."""
        tile = SCIMTile()
        rng = np.random.RandomState(42)
        acts = rng.randint(0, 256, 16)
        weights = rng.choice([-1, 1], (16, 16))

        w_bin = np.where(weights > 0, 1, 0)
        tile.load_weights(w_bin)

        res = tile.run_mvm(activations=acts, mode=ProcessingElement.MODE_HYBRID_RELU, N=256)
        stochastic_res = res['results']
        true_math = res['true_math']

        diff = np.abs(stochastic_res - true_math)
        max_possible = 16 * 255  # 4080
        max_err_pct = diff.max() / max_possible * 100.0
        mean_err_pct = diff.mean() / max_possible * 100.0

        assert max_err_pct < 0.5, f"Max stochastic error {max_err_pct:.2f}% exceeds 0.5%"
        assert mean_err_pct < 0.1, f"Mean stochastic error {mean_err_pct:.2f}% exceeds 0.1%"
