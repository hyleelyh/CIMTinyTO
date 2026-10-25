#!/usr/bin/env python3
# ============================================================================
# Script: run_live_camera_demo.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) / Raspberry Pi 5 / Desktop PC (Pillar 6.1)
# Standard: Python 3.10+ / Live Camera Ingestion Demonstration
# ============================================================================

import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../.."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from fpga.pynq_z2.micro_resnet.vision_pipeline import EdgeVisionPipeline


def main():
    print("=" * 75)
    print(" CIMTinyTO Pillar 6.1: Real-Time Edge Vision Camera Stream")
    print(" Target: 16x16 SCIM Macro @ 50 MHz (Application #6 / Tier 2)")
    print("=" * 75)

    pipeline = EdgeVisionPipeline(force_emulation=True, seed=42)

    total_frames = 15
    print(f"\n>>> Starting Live Camera Stream ({total_frames} frames)...")

    def on_frame(f_idx, res, hud_img):
        pred = res['pred_class'].upper()
        prob = res['probabilities'][res['pred_idx']] * 100.0
        fps = res['fps']
        lat = res['total_time_sec'] * 1000.0
        print(f" Frame [{f_idx+1:02d}/{total_frames:02d}] -> Class: {pred:<12} ({prob:5.1f}%) | Latency: {lat:6.2f} ms | Speed: {fps:6.1f} FPS")

    results = pipeline.stream_live_camera(
        num_frames=total_frames,
        tier=2,
        device_id=0,
        on_frame=on_frame
    )

    if results:
        last_hud = results[-1][1]
        out_path = os.path.join(CURRENT_DIR, "live_camera_hud.png")
        last_hud.save(out_path)
        print(f"\n[Success] Stream completed! Latest annotated HUD frame saved to: {out_path}")
    print("=" * 75)


if __name__ == "__main__":
    main()
