# ============================================================================
# Module: export_qat_weights.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: Python 3.10+ / BatchNorm Folding & JSON Exporter
# ============================================================================

import os
import json
import argparse
import numpy as np
import sys
import torch

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fpga.pynq_z2.micro_resnet.micro_resnet_qat import MicroResNetQAT, BinaryQuantizeSTE


def fold_batchnorm(bn_module, shift=11):
    """Algebraically fold BatchNorm parameters into integer bias and fixed-point scale.
    
    Formula:
      y = gamma * (x - mu) / sqrt(var + eps) + beta
        = alpha * x + delta
        = alpha * (x + delta / alpha)
      where:
        alpha = gamma / sqrt(var + eps)
        delta = beta - alpha * mu
        B = round(delta / alpha)
        M = round(mean(|alpha|) * 2^shift)
    """
    gamma = bn_module.weight.detach().cpu().numpy()
    beta = bn_module.bias.detach().cpu().numpy()
    mu = bn_module.running_mean.detach().cpu().numpy()
    var = bn_module.running_var.detach().cpu().numpy()
    eps = bn_module.eps

    alpha = gamma / np.sqrt(var + eps)
    delta = beta - alpha * mu

    # Integer bias per channel: B = round(delta / alpha)
    # Guard against division by near-zero alpha
    safe_alpha = np.where(np.abs(alpha) < 1e-6, np.sign(alpha + 1e-9) * 1e-6, alpha)
    bias = np.round(delta / safe_alpha).astype(int)

    # Scale: select power-of-two shift (e.g. 11 -> 2^11 = 2048)
    mean_alpha = float(np.mean(np.abs(alpha)))
    mult = int(np.round(mean_alpha * (1 << shift)))
    if mult <= 0:
        mult = 1

    return bias, {"mult": mult, "shift": shift}


def export_checkpoint(ckpt_path, output_json=None):
    """Load PyTorch checkpoint, extract binary weights, fold BN, and export to JSON."""
    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")

    data = torch.load(ckpt_path, map_location="cpu")
    state_dict = data["state_dict"]
    dataset_name = data.get("dataset_name", "cifar10_4class")
    num_classes = data.get("num_classes", 10)
    class_names = data.get("class_names", [])
    best_acc = data.get("best_acc", 0.0)

    model = MicroResNetQAT(num_classes=num_classes)
    model.load_state_dict(state_dict)
    model.eval()

    weights = {}
    biases = {}
    scales = {}

    # 1. Stem Conv
    w_stem = model.stem_conv.get_binary_weights()  # (16, 16)
    b_stem, s_stem = fold_batchnorm(model.stem_bn, shift=11)
    weights["stem"] = w_stem.tolist()
    biases["stem"] = b_stem.tolist()
    scales["stem"] = s_stem

    # 2. ResBlock 1 - Conv 1a
    w_r1c1 = model.res1_conv1.get_binary_weights()
    b_r1c1, s_r1c1 = fold_batchnorm(model.res1_bn1, shift=11)
    weights["res1_conv1"] = w_r1c1.tolist()
    biases["res1_conv1"] = b_r1c1.tolist()
    scales["res1_conv1"] = s_r1c1

    # 3. ResBlock 1 - Conv 1b
    w_r1c2 = model.res1_conv2.get_binary_weights()
    b_r1c2, s_r1c2 = fold_batchnorm(model.res1_bn2, shift=11)
    weights["res1_conv2"] = w_r1c2.tolist()
    biases["res1_conv2"] = b_r1c2.tolist()
    scales["res1_conv2"] = s_r1c2

    # 4. ResBlock 2 - Conv 2a
    w_r2c1 = model.res2_conv1.get_binary_weights()
    b_r2c1, s_r2c1 = fold_batchnorm(model.res2_bn1, shift=11)
    weights["res2_conv1"] = w_r2c1.tolist()
    biases["res2_conv1"] = b_r2c1.tolist()
    scales["res2_conv1"] = s_r2c1

    # 5. ResBlock 2 - Conv 2b
    w_r2c2 = model.res2_conv2.get_binary_weights()
    b_r2c2, s_r2c2 = fold_batchnorm(model.res2_bn2, shift=11)
    weights["res2_conv2"] = w_r2c2.tolist()
    biases["res2_conv2"] = b_r2c2.tolist()
    scales["res2_conv2"] = s_r2c2

    # 6. Classifier Head
    w_clf = model.classifier.get_binary_weights()  # (16, 16)
    b_clf, s_clf = fold_batchnorm(model.classifier_bn, shift=8)
    # Pad bias to 16 if num_classes < 16
    if len(b_clf) < 16:
        b_clf_padded = np.zeros(16, dtype=int)
        b_clf_padded[:len(b_clf)] = b_clf
        b_clf = b_clf_padded

    weights["classifier"] = w_clf.tolist()
    biases["classifier"] = b_clf.tolist()
    scales["classifier"] = s_clf

    out_data = {
        "dataset_name": dataset_name,
        "num_classes": num_classes,
        "class_names": class_names,
        "best_acc": best_acc,
        "weights": weights,
        "biases": biases,
        "scales": scales
    }

    if output_json is None:
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        output_json = os.path.join(curr_dir, f"micro_resnet_weights_{dataset_name}.json")

    with open(output_json, "w") as f:
        json.dump(out_data, f, indent=2)

    print(f"============================================================")
    print(f" Exported QAT Parameters to: {output_json}")
    print(f" Profile: {dataset_name} | Classes ({num_classes}): {class_names}")
    print(f" Total Weight Bits: 1536 (192 bytes) | Best Accuracy: {best_acc:.2f}%")
    print(f"============================================================")
    return output_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export trained QAT weights to JSON for MicroResNet16")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to .pt checkpoint")
    parser.add_argument("--output", type=str, default=None, help="Path to output JSON")
    args = parser.parse_args()

    export_checkpoint(args.checkpoint, args.output)
