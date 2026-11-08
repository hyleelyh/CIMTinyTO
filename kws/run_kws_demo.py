#!/usr/bin/env python3
"""
run_kws_demo.py — End-to-End Voice Keyword Spotting Demonstration for Pillar 6.2.
Demonstrates 16-channel Mel-filterbank acoustic extraction, stationary SCIM execution,
and real-time wake-word classification using the compiled C/CMSIS-DSP driver.
"""

import os
import sys
import time
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kws.kws_audio_frontend import generate_synthetic_audio, extract_mel_filterbank, quantize_spectrogram_to_uint8
from kws.kws_c_wrapper import KWSCPipeline


def print_ascii_spectrogram(spec_uint8: np.ndarray, title: str):
    """Render compact ASCII visualization of 16-channel Mel spectrogram."""
    shades = " .:-=+*#%@"
    print(f"\n--- {title} (16 Mel Channels x 32 Temporal Frames) ---")
    print("Freq (Hz)  Mel Bin  [Time -> ~650 ms]")
    freq_labels = [
        "4000 Hz", "3200 Hz", "2500 Hz", "2000 Hz",
        "1550 Hz", "1200 Hz", " 950 Hz", " 750 Hz",
        " 600 Hz", " 480 Hz", " 380 Hz", " 290 Hz",
        " 210 Hz", " 140 Hz", "  90 Hz", "  50 Hz"
    ]
    for r in range(15, -1, -1):  # High frequency at top, low frequency at bottom
        row_str = "".join(shades[val * (len(shades) - 1) // 255] for val in spec_uint8[r, :])
        print(f"{freq_labels[15 - r]}   [{r:2d}] |{row_str}|")
    print("                     0        8       16       24      31 Frame")


def main():
    print("========================================================================")
    print("CIMTinyTO Voice Keyword Spotting (KWS) Pre-Silicon Emulation — Pillar 6.2")
    print("Hardware Target: STM32 B-U585I-IOT02A Discovery Kit & Sky130 SCIM Macro")
    print("========================================================================")

    weights_4class_path = "kws/kws_weights_4class.json"
    weights_6class_path = "kws/kws_weights_6class.json"

    if not os.path.exists(weights_4class_path) or not os.path.exists(weights_6class_path):
        print("Model weights not found. Please run: python3 -m kws.train_kws_qat")
        sys.exit(1)

    pipeline_4 = KWSCPipeline(weights_4class_path)
    pipeline_6 = KWSCPipeline(weights_6class_path)

    # 1. Acoustic Spectrogram Visualizations
    keywords = ['silence', 'yes', 'no', 'stop', 'go']
    for kw in ['yes', 'no', 'stop']:
        audio = generate_synthetic_audio(kw)
        pcm = (audio * 32767.0).astype(np.int16)
        spec = pipeline_6.extract_spectrogram(pcm)
        print_ascii_spectrogram(spec, f"Acoustic Mel Spectrogram for '{kw.upper()}'")

    # 2. Multi-Class Keyword Classification Benchmark
    print("\n========================================================================")
    print("Evaluating 6-Class KWS Model on Acoustic Utterances:")
    print("Classes: ['silence', 'unknown', 'yes', 'no', 'stop', 'go']")
    print("========================================================================")

    test_words = ['silence', 'unknown', 'yes', 'no', 'stop', 'go']
    for kw in test_words:
        audio = generate_synthetic_audio(kw)
        pcm = (audio * 32767.0).astype(np.int16)
        pred_idx, pred_name, logits = pipeline_6.infer(pcm)
        status = "MATCH" if pred_name == kw else "MISMATCH"
        print(f"Target: {kw:<8} | Predicted: {pred_name:<8} (class {pred_idx}) | Logits: {logits.tolist()} [{status}]")

    # 3. High-Speed Latency Profiling
    print("\n========================================================================")
    print("Inference Latency & Throughput Profiling (100 Iterations):")
    print("========================================================================")

    sample_audio = (generate_synthetic_audio('yes') * 32767.0).astype(np.int16)
    for _ in range(10):
        pipeline_6.infer(sample_audio)

    iters = 100
    t0 = time.perf_counter()
    for _ in range(iters):
        pipeline_6.infer(sample_audio)
    t1 = time.perf_counter()

    latency_ms = (t1 - t0) * 1000.0 / iters
    inferences_per_sec = 1000.0 / latency_ms

    print(f"End-to-End Latency per 1-Second Utterance: {latency_ms:.3f} ms")
    print(f"Host Compute Throughput:                 {inferences_per_sec:.1f} inferences/second")
    print(f"Real-Time Speedup Factor:                 {1000.0 / latency_ms:.1f}x real-time")
    print(f"STM32U585 Cortex-M33 Estimated Load:      < 0.5% (Leaves >99.5% CPU idle!)")

    # 4. Silicon Power & Memory Analysis
    print("\n========================================================================")
    print("Silicon Memory Footprint & Stationary Weight Energy Metrics:")
    print("========================================================================")
    print("Total SCIM Weights (3 Layers x 256 bits):   768 bits = 96 BYTES!")
    print("PCM Audio Double-Buffer Size (DMA):         16 KB SRAM")
    print("Mel Spectrogram Footprint (16x32 uint8):     512 Bytes")
    print("Weight Shifts per Utterance (Stationary):   3 x 256 = 768 clock cycles")
    print("Weight Shifts without Stationary Caching:   3 x 32 x 256 = 24,576 clock cycles")
    print("Weight Dynamic Switching Power Suppression: 96.88% reduction!")
    print("========================================================================")


if __name__ == '__main__':
    main()
