# ============================================================================
# Module: calibrate_fashion_biases.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: Python 3.10+ / Classifier Head DC Offset Calibration
# ============================================================================

import os
import sys
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets

# Ensure repository root is on sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fpga.pynq_z2.micro_resnet.vision_pipeline import EdgeVisionPipeline


def extract_gap_features(pipeline, dataset, num_samples=500):
    """Run samples through the feature extractor up to Global Average Pooling (GAP)."""
    gap_features = []
    labels = []
    model = pipeline.tier2_engine.model
    
    print(f"Extracting GAP features for {num_samples} samples...")
    for i in range(num_samples):
        img, label = dataset[i]
        arr_28 = np.array(img)
        arr_32 = np.pad(arr_28, ((2, 2), (2, 2)), mode="constant", constant_values=0)
        arr_rgb = np.stack([arr_32, arr_32, arr_32], axis=-1)

        feat = model.preprocess_image(arr_rgb)
        s = pipeline.tier2_engine.execute_conv1x1_layer("stem", feat, model.weights["stem"], model.biases["stem"], model.scales["stem"])
        r1a = pipeline.tier2_engine.execute_conv1x1_layer("res1_conv1", s, model.weights["res1_conv1"], model.biases["res1_conv1"], model.scales["res1_conv1"])
        r1_smooth = model.depthwise_smooth_3x3(r1a)
        r1b = pipeline.tier2_engine.execute_conv1x1_layer("res1_conv2", r1_smooth, model.weights["res1_conv2"], model.biases["res1_conv2"], model.scales["res1_conv2"])
        res1_out = np.clip(((s.astype(np.int32) + r1b.astype(np.int32)) // 2), 0, 255).astype(np.uint8)
        res1_pool = model.max_pool_2x2(res1_out)

        r2a = pipeline.tier2_engine.execute_conv1x1_layer("res2_conv1", res1_pool, model.weights["res2_conv1"], model.biases["res2_conv1"], model.scales["res2_conv1"])
        r2b = pipeline.tier2_engine.execute_conv1x1_layer("res2_conv2", r2a, model.weights["res2_conv2"], model.biases["res2_conv2"], model.scales["res2_conv2"])
        res2_out = np.clip(((res1_pool.astype(np.int32) + r2b.astype(np.int32)) // 2), 0, 255).astype(np.uint8)
        res2_pool = model.max_pool_2x2(res2_out)
        gap = np.mean(res2_pool, axis=(1, 2)).astype(np.float32)

        gap_features.append(gap)
        labels.append(label)

    return np.array(gap_features), np.array(labels)


def calibrate_biases(weights_json_path=None, num_calib_samples=500):
    """Compute empirical GAP mean, cancel DC offset, and optimize integer biases."""
    if weights_json_path is None:
        weights_json_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "micro_resnet_weights_fashion_mnist.json"
        )

    pipeline = EdgeVisionPipeline(force_emulation=True, profile="fashion_mnist")
    ds = datasets.FashionMNIST(root="./data", train=False, download=True)

    # 1. Extract GAP features
    X_gap, Y_labels = extract_gap_features(pipeline, ds, num_samples=num_calib_samples)

    W = pipeline.tier2_engine.model.weights["classifier"][:, :10]
    X_raw_logits = np.dot(X_gap, W)  # (N, 10)

    # 2. Compute empirical DC offset: D_c = mean(GAP) * W
    mean_gap = np.mean(X_gap, axis=0)
    dc_offset = np.dot(mean_gap, W)
    print("\n--- Empirical DC Offset Analysis ---")
    print("Mean GAP activation per channel:", np.round(mean_gap, 1).tolist())
    print("Expected DC offset per class:", np.round(dc_offset, 1).tolist())

    # Initial DC cancellation bias
    b_init = -dc_offset

    # 3. Optimize integer biases via cross-entropy loss with PyTorch
    t_X = torch.tensor(X_raw_logits, dtype=torch.float32)
    t_Y = torch.tensor(Y_labels, dtype=torch.long)

    bias_param = nn.Parameter(torch.tensor(b_init, dtype=torch.float32))
    optimizer = optim.Adam([bias_param], lr=1.0)
    criterion = nn.CrossEntropyLoss()

    for step in range(500):
        optimizer.zero_grad()
        loss = criterion(t_X + bias_param, t_Y)
        loss.backward()
        optimizer.step()

    opt_b_int = np.round(bias_param.detach().cpu().numpy()).astype(np.int32)
    print("\n--- Calibration Results ---")
    print("Calibrated integer bias vector:", opt_b_int.tolist())

    # Pad to 16 elements for hardware format
    full_bias_16 = np.zeros(16, dtype=int)
    full_bias_16[:10] = opt_b_int

    # 4. Update JSON file
    with open(weights_json_path, "r") as f:
        data = json.load(f)

    data["biases"]["classifier"] = full_bias_16.tolist()

    with open(weights_json_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nUpdated {weights_json_path} successfully!")

    # 5. Evaluate on independent test set
    test_start = num_calib_samples
    test_count = 1000
    print(f"\nEvaluating on independent test slice (samples {test_start} to {test_start + test_count})...")
    
    pipeline_eval = EdgeVisionPipeline(force_emulation=True, profile="fashion_mnist")
    preds = []
    true_labels = []
    
    for i in range(test_start, test_start + test_count):
        img, label = ds[i]
        arr_28 = np.array(img)
        arr_32 = np.pad(arr_28, ((2, 2), (2, 2)), mode="constant", constant_values=0)
        arr_rgb = np.stack([arr_32, arr_32, arr_32], axis=-1)
        
        res = pipeline_eval.run_inference(arr_rgb, tier=2)
        preds.append(res["pred_idx"])
        true_labels.append(label)

    unique, counts = np.unique(preds, return_counts=True)
    classes = pipeline_eval.tier2_engine.model.CLASSES
    print("\nIndependent Test Set Prediction Distribution:")
    for cls_idx in range(10):
        cnt = counts[list(unique).index(cls_idx)] if cls_idx in unique else 0
        print(f"Class {cls_idx:2d} ({classes[cls_idx]:<12s}): {cnt:4d}/{test_count} ({cnt / test_count * 100.0:4.1f}%)")

    acc = (np.array(preds) == np.array(true_labels)).mean() * 100.0
    print(f"\nIndependent Test Accuracy: {acc:.2f}% (vs 10.0% random baseline)")

    return opt_b_int.tolist(), acc


if __name__ == "__main__":
    calibrate_biases()
