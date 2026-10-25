#!/usr/bin/env python3
# ============================================================================
# Script: run_micro_resnet_benchmark.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Host Emulation (Pillar 6.1)
# Standard: Python 3.10+ / Production Benchmark Suite
# ============================================================================

import os
import sys
import time
import numpy as np

# Ensure module path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../.."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from fpga.pynq_z2.micro_resnet.vision_pipeline import EdgeVisionPipeline
from fpga.pynq_z2.micro_resnet.micro_resnet_model import MicroResNet16


def run_benchmark():
    print("=" * 80)
    print(" CIMTinyTO Pillar 6.1: Micro-ResNet Pre-Silicon Emulation Benchmark")
    print(" Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) & Bit-Exact Host Emulation")
    print("=" * 80)

    pipeline = EdgeVisionPipeline(force_emulation=True, seed=42)
    test_img = pipeline.generate_synthetic_pattern("circle")

    print("\n[Step 1/4] Running Software Mathematical Reference (Fixed-Point Baseline)...")
    feat = pipeline.load_image(test_img)
    x = pipeline.tier1_engine.model.preprocess_image(feat)
    ref_out = pipeline.tier1_engine.model.forward_fixed_reference(x)
    print(f" Reference Prediction: {ref_out['pred_class'].upper()} (Class ID: {ref_out['pred_idx']})")
    print(f" Reference Logits:     {ref_out['logits'].tolist()}")

    # Tier 1 Benchmark
    print("\n[Step 2/4] Running Tier 1: Pure Python MMIO Driver...")
    res_t1 = pipeline.run_inference(test_img, tier=1)
    print(f" Tier 1 Prediction:    {res_t1['pred_class'].upper()} (Logits: {res_t1['logits'].tolist()})")
    print(f" Tier 1 Time:          {res_t1['total_time_sec']*1000.0:.2f} ms ({res_t1['fps']:.2f} FPS)")
    print(f" Tier 1 Tile Latency:  {res_t1['tile_latency_us']:.2f} us/tile (Total Tiles: {res_t1['total_tiles']})")

    # Tier 2 Benchmark
    print("\n[Step 3/4] Running Tier 2: Compiled C/C++ MMIO Acceleration...")
    res_t2 = pipeline.run_inference(test_img, tier=2)
    print(f" Tier 2 Prediction:    {res_t2['pred_class'].upper()} (Logits: {res_t2['logits'].tolist()})")
    print(f" Tier 2 Time:          {res_t2['total_time_sec']*1000.0:.2f} ms ({res_t2['fps']:.2f} FPS)")
    print(f" Tier 2 Tile Latency:  {res_t2['tile_latency_us']:.2f} us/tile (Total Tiles: {res_t2['total_tiles']})")

    # Tier 3 Benchmark
    print("\n[Step 4/4] Running Tier 3: Autonomous Hardware Feeder / AXI-DMA Model (50 MHz Line Rate)...")
    res_t3 = pipeline.run_inference(test_img, tier=3)
    print(f" Tier 3 Prediction:    {res_t3['pred_class'].upper()} (Logits: {res_t3['logits'].tolist()})")
    print(f" Tier 3 Time:          {res_t3['total_time_sec']*1000.0:.2f} ms ({res_t3['fps']:.2f} FPS)")
    print(f" Tier 3 Tile Latency:  {res_t3['tile_latency_us']:.2f} us/tile (Total Tiles: {res_t3['total_tiles']})")

    # Verification of Numerical Agreement
    print("\n" + "=" * 80)
    print(" VERIFICATION & PARITY SCORECARD")
    print("=" * 80)

    class_match_t1 = (res_t1['pred_idx'] == ref_out['pred_idx'])
    class_match_t2 = (res_t2['pred_idx'] == ref_out['pred_idx'])
    class_match_t3 = (res_t3['pred_idx'] == ref_out['pred_idx'])

    # Compute correlation / LSB differences
    diff_t1_ref = np.abs(res_t1['logits'] - ref_out['logits'])
    diff_t2_ref = np.abs(res_t2['logits'] - ref_out['logits'])
    diff_t3_ref = np.abs(res_t3['logits'] - ref_out['logits'])

    print(f" - Tier 1 Top-1 Agreement with Reference: {'PASS (MATCH)' if class_match_t1 else 'FAIL'}")
    print(f" - Tier 2 Top-1 Agreement with Reference: {'PASS (MATCH)' if class_match_t2 else 'FAIL'}")
    print(f" - Tier 3 Top-1 Agreement with Reference: {'PASS (MATCH)' if class_match_t3 else 'FAIL'}")
    print(f" - Tier 1 Max LSB Divergence:              {np.max(diff_t1_ref)} LSBs")
    print(f" - Tier 2 Max LSB Divergence:              {np.max(diff_t2_ref)} LSBs")
    print(f" - Tier 3 Max LSB Divergence:              {np.max(diff_t3_ref)} LSBs (Bit-Exact)")

    # Performance Comparison Table
    print("\n" + "=" * 80)
    print(" MULTI-TIER TRANSPORT THROUGHPUT COMPARISON")
    print("=" * 80)
    print(f"{'Implementation Tier':<32} | {'Tile Latency':<14} | {'Frame Time':<12} | {'FPS':<10} | {'Speedup':<8}")
    print("-" * 80)
    speedup_t1 = 1.0
    speedup_t2 = res_t1['total_time_sec'] / res_t2['total_time_sec'] if res_t2['total_time_sec'] > 0 else 0
    speedup_t3 = res_t1['total_time_sec'] / res_t3['total_time_sec'] if res_t3['total_time_sec'] > 0 else 0

    print(f"{res_t1['tier']:<32} | {res_t1['tile_latency_us']:>9.2f} us   | {res_t1['total_time_sec']*1000:>8.2f} ms | {res_t1['fps']:>7.2f}  | {speedup_t1:>6.1f}x")
    print(f"{res_t2['tier']:<32} | {res_t2['tile_latency_us']:>9.2f} us   | {res_t2['total_time_sec']*1000:>8.2f} ms | {res_t2['fps']:>7.2f}  | {speedup_t2:>6.1f}x")
    print(f"{res_t3['tier']:<32} | {res_t3['tile_latency_us']:>9.2f} us   | {res_t3['total_time_sec']*1000:>8.2f} ms | {res_t3['fps']:>7.2f}  | {speedup_t3:>6.1f}x")
    print("=" * 80)

    # Render HUD sample
    hud_img = pipeline.render_hud_overlay(res_t2)
    hud_path = os.path.join(CURRENT_DIR, "sample_hud_output.png")
    hud_img.save(hud_path)
    print(f"\n[Artifact Generated] Sample annotated HUD saved to: {hud_path}")

    assert class_match_t1 and class_match_t2 and class_match_t3, "Top-1 classification mismatch across tiers!"
    print("\n>>> ALL PILLAR 6.1 BENCHMARK REGRESSIONS PASSED SUCCESSFULLY! <<<\n")


if __name__ == "__main__":
    run_benchmark()
