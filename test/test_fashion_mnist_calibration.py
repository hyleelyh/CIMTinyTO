# ============================================================================
# Module: test_fashion_mnist_calibration.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: pytest regression suite for Fashion-MNIST dynamic range calibration
# ============================================================================

import os
import sys
import glob
import json
import numpy as np
import pytest
from PIL import Image

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fpga.pynq_z2.micro_resnet.vision_pipeline import EdgeVisionPipeline
from fpga.pynq_z2.micro_resnet.scim_tier1_mmio import SCIMTier1Engine
from fpga.pynq_z2.micro_resnet.scim_tier2_wrapper import SCIMTier2Engine
from fpga.pynq_z2.micro_resnet.scim_tier3_dma import SCIMTier3Engine


def test_biases_format_and_cancellation():
    """Verify that fashion_mnist weights JSON contains valid 16-element calibrated biases."""
    json_path = os.path.join(_REPO_ROOT, "fpga/pynq_z2/micro_resnet/micro_resnet_weights_fashion_mnist.json")
    assert os.path.exists(json_path), f"File not found: {json_path}"

    with open(json_path, "r") as f:
        data = json.load(f)

    clf_bias = data["biases"]["classifier"]
    assert len(clf_bias) == 16, f"Expected 16 classifier biases, got {len(clf_bias)}"

    # Class 2 (Pullover) has weight sum +10 -> requires strong negative bias (< -400)
    assert clf_bias[2] < -400, f"Class 2 bias must cancel positive DC offset, got {clf_bias[2]}"

    # Class 1 (Trouser) and Class 7 (Sneaker) have negative weight sums -> require positive biases (> +200)
    assert clf_bias[1] > 200, f"Class 1 bias must cancel negative DC offset, got {clf_bias[1]}"
    assert clf_bias[7] > 200, f"Class 7 bias must cancel negative DC offset, got {clf_bias[7]}"


def test_benchmark_samples_diverse_predictions():
    """Verify that the 10 benchmark samples predict diverse categories and do not collapse to Pullover."""
    sample_dir = os.path.join(_REPO_ROOT, "fpga/pynq_z2/jupyter/samples")
    sample_files = sorted(glob.glob(os.path.join(sample_dir, "fashion_sample_*.png")))
    assert len(sample_files) == 10, f"Expected 10 Fashion-MNIST sample images, found {len(sample_files)}"

    pipe = EdgeVisionPipeline(force_emulation=True, profile="fashion_mnist")
    classes = pipe.tier2_engine.model.CLASSES

    preds = []
    for fpath in sample_files:
        img = Image.open(fpath)
        res = pipe.run_inference(np.array(img), tier=2)
        preds.append(res["pred_idx"])

    unique_preds = set(preds)
    pullover_count = preds.count(2)

    print("\nBenchmark Sample Predictions:", [classes[p] for p in preds])
    print(f"Unique classes predicted: {len(unique_preds)}/10")

    # Anti-collapse assertion: Pullover must NOT exceed 30% of sample predictions
    assert pullover_count <= 3, f"Class collapse detected: Pullover predicted {pullover_count}/10 times"
    # Diversity assertion: At least 4 distinct classes must be predicted across the 10 samples
    assert len(unique_preds) >= 4, f"Insufficient diversity: only {len(unique_preds)} distinct classes predicted"


def test_multi_tier_exact_parity_on_fashion_mnist():
    """Verify bit-exact prediction parity between Tier 1, Tier 2, and Tier 3 on Fashion-MNIST."""
    sample_dir = os.path.join(_REPO_ROOT, "fpga/pynq_z2/jupyter/samples")
    sample_files = sorted(glob.glob(os.path.join(sample_dir, "fashion_sample_*.png")))[:3]

    t1 = SCIMTier1Engine(force_emulation=True, profile="fashion_mnist")
    t2 = SCIMTier2Engine(force_sim=True, profile="fashion_mnist")
    t3 = SCIMTier3Engine(profile="fashion_mnist")

    for fpath in sample_files:
        img_arr = np.array(Image.open(fpath))

        out1 = t1.infer(img_arr)
        out2 = t2.infer(img_arr)
        out3 = t3.infer(img_arr)

        assert out1["pred_idx"] == out2["pred_idx"], f"Mismatch between Tier 1 ({out1['pred_idx']}) and Tier 2 ({out2['pred_idx']})"
        assert out2["pred_idx"] == out3["pred_idx"], f"Mismatch between Tier 2 ({out2['pred_idx']}) and Tier 3 ({out3['pred_idx']})"
