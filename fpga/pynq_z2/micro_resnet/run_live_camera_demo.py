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


import argparse


def main():
    parser = argparse.ArgumentParser(description="Run Live Edge Vision Camera Stream with Trained QAT Models")
    parser.add_argument("--profile", type=str, default="cifar10_4class",
                        choices=["cifar10_4class", "cifar10_10class", "fashion_mnist"],
                        help="Trained QAT weight profile to load")
    parser.add_argument("--hw", action="store_true",
                        help="Run on physical PYNQ-Z2 hardware (force_emulation=False)")
    parser.add_argument("--frames", type=int, default=20,
                        help="Number of frames to stream")
    parser.add_argument("--device", type=int, default=0,
                        help="V4L2 video capture device index (/dev/video0)")
    args = parser.parse_args()

    print("=" * 75)
    print(" CIMTinyTO Pillar 6.1: Real-Time Edge Vision Camera Stream")
    mode_str = "Physical PYNQ-Z2 FPGA (AXI-Lite @ 50 MHz)" if args.hw else "Bit-Exact Software Emulation"
    print(f" Target Mode: {mode_str}")
    print(f" Loaded Model Profile: {args.profile}")
    print("=" * 75)

    pipeline = EdgeVisionPipeline(force_emulation=(not args.hw), profile=args.profile)

    print(f"\n>>> Starting Live Camera Stream ({args.frames} frames)...")
    print(f" Active Classes: {pipeline.tier2_engine.model.CLASSES}")

    def on_frame(f_idx, res, hud_img):
        pred = res['pred_class'].upper()
        prob = res['probabilities'][res['pred_idx']] * 100.0
        fps = res['fps']
        lat = res['total_time_sec'] * 1000.0
        print(f" Frame [{f_idx+1:02d}/{args.frames:02d}] -> Class: {pred:<14} ({prob:5.1f}%) | Latency: {lat:6.2f} ms | Speed: {fps:6.1f} FPS")

    results = pipeline.stream_live_camera(
        num_frames=args.frames,
        tier=2,
        device_id=args.device,
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
