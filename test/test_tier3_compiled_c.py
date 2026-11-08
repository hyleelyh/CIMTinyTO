# ============================================================================
# Test Suite: test_tier3_compiled_c.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) & Host Emulation (Pillar 6.1)
# ============================================================================
# Pedagogical & Verification Rationale:
#
# 1. Zero-LSB Discrepancy Mandate:
#    - Software optimizations must never compromise mathematical fidelity.
#    - This suite validates that every compiled C & ARM NEON kernel achieves
#      bit-exact parity (0 LSB error) against the Python/NumPy reference models.
#
# 2. Transparent Fallback Verification:
#    - Validates that when C acceleration is disabled (use_c_accel=False) or
#      unavailable, the pipeline safely falls back to standard NumPy execution.
# ============================================================================

import os
import sys
import pytest
import numpy as np

# Ensure repository root is on sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fpga.pynq_z2.micro_resnet.micro_resnet_model import MicroResNet16
from fpga.pynq_z2.micro_resnet.scim_tier3_c_accel import SCIMTier3CAccelerator
from fpga.pynq_z2.micro_resnet.scim_tier3_dma import SCIMTier3Engine


@pytest.fixture(scope="module")
def c_accel():
    accel = SCIMTier3CAccelerator()
    assert accel.is_available, "libscim_tier3_accel.so failed to load"
    return accel


def test_c_accelerator_library_loads(c_accel):
    """Verify that libscim_tier3_accel.so loads cleanly with all exported symbols."""
    assert c_accel.is_available is True
    assert c_accel.c_lib is not None
    assert hasattr(c_accel.c_lib, "c_preprocess_and_pack_input")
    assert hasattr(c_accel.c_lib, "c_requantize_relu_16b_to_8b")
    assert hasattr(c_accel.c_lib, "c_depthwise_smooth_3x3")
    assert hasattr(c_accel.c_lib, "c_fused_residual_add_and_maxpool2x2")
    assert hasattr(c_accel.c_lib, "c_pack_dma_input")
    assert hasattr(c_accel.c_lib, "c_gap_and_classify")


def test_preprocess_and_pack_input_parity(c_accel):
    """Verify C input preprocessing & DMA packing is bit-exact to Python reference."""
    np.random.seed(42)
    for _ in range(5):
        img = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)

        # Python reference: returns (16, 32, 32) uint8
        py_feat = MicroResNet16.preprocess_image(img)
        py_hwc = np.transpose(py_feat, (1, 2, 0))  # (32, 32, 16)

        # C kernel
        dma_buf = np.zeros(1 + 1024 * 4, dtype=np.uint32)
        words_written = c_accel.preprocess_and_pack_input(img, dma_buf)
        assert words_written == 1 + 1024 * 4
        assert dma_buf[0] == ((0x03 << 24) | 1024)

        c_hwc = dma_buf[1:].view(np.uint8).reshape(32, 32, 16)
        diff = np.abs(py_hwc.astype(int) - c_hwc.astype(int))
        assert np.max(diff) == 0, f"Preprocess mismatch: max diff = {np.max(diff)}"


def test_requantize_relu_parity(c_accel):
    """Verify C requantization and ReLU is bit-exact across diverse ranges."""
    np.random.seed(101)
    for num_tiles in [1024, 256, 64]:
        raw_acc = np.random.randint(-4096, 4095, (num_tiles, 16), dtype=np.int16)
        bias = np.random.randint(-100, 100, (16,), dtype=np.int32)
        scale_dict = {
            "mult": np.random.randint(50, 500, (16,)).tolist(),
            "shift": 11
        }

        py_req = MicroResNet16.requantize_relu(raw_acc, bias, scale_dict)
        c_req = c_accel.requantize_relu(raw_acc, bias, scale_dict)

        diff = np.abs(py_req.astype(int) - c_req.astype(int))
        assert np.max(diff) == 0, f"Requantize mismatch: max diff = {np.max(diff)}"


def test_depthwise_smooth_3x3_parity(c_accel):
    """Verify C depthwise 3x3 box smoothing is bit-exact to Python edge-padded filter."""
    np.random.seed(202)
    for _ in range(3):
        acts_hwc = np.random.randint(0, 256, (32, 32, 16), dtype=np.uint8)
        acts_chw = np.transpose(acts_hwc, (2, 0, 1))

        py_smooth_chw = MicroResNet16.depthwise_smooth_3x3(acts_chw)
        py_smooth_hwc = np.transpose(py_smooth_chw, (1, 2, 0))

        c_smooth_hwc = c_accel.depthwise_smooth_3x3(acts_hwc)
        diff = np.abs(py_smooth_hwc.astype(int) - c_smooth_hwc.astype(int))
        assert np.max(diff) == 0, f"Depthwise smooth mismatch: max diff = {np.max(diff)}"


def test_fused_residual_add_and_maxpool2x2_parity(c_accel):
    """Verify fused residual addition and 2x2 max pooling matches Python separate ops."""
    np.random.seed(303)
    for (H, W) in [(32, 32), (16, 16)]:
        shortcut = np.random.randint(0, 256, (H, W, 16), dtype=np.uint8)
        conv_out = np.random.randint(0, 256, (H, W, 16), dtype=np.uint8)

        # Python reference: elementwise halving add followed by maxpool
        py_res = np.clip((shortcut.astype(int) + conv_out.astype(int)) // 2, 0, 255).astype(np.uint8)
        py_res_chw = np.transpose(py_res, (2, 0, 1))
        py_pooled_chw = MicroResNet16.max_pool_2x2(py_res_chw)
        py_pooled_hwc = np.transpose(py_pooled_chw, (1, 2, 0))

        # C fused kernel
        c_pooled_hwc = c_accel.fused_residual_add_and_maxpool2x2(shortcut, conv_out)
        diff = np.abs(py_pooled_hwc.astype(int) - c_pooled_hwc.astype(int))
        assert np.max(diff) == 0, f"Fused pool mismatch: max diff = {np.max(diff)}"


def test_gap_and_classify_parity(c_accel):
    """Verify C Global Average Pooling and classification is bit-exact to Python."""
    np.random.seed(404)
    for num_classes in [4, 10]:
        feat_hwc = np.random.randint(0, 256, (8, 8, 16), dtype=np.uint8)
        weights = np.random.choice([-1, 1], size=(16, 16)).astype(np.int32)
        biases = np.random.randint(-100, 100, size=16).astype(np.int32)

        feat_chw = np.transpose(feat_hwc, (2, 0, 1))
        py_gap = np.mean(feat_chw, axis=(1, 2)).astype(np.uint8)
        py_raw = np.matmul(py_gap.astype(np.int32), weights)
        py_logits = (py_raw[:num_classes] + biases[:num_classes]).astype(np.int32)
        py_pred = int(np.argmax(py_logits))

        c_pred, c_logits = c_accel.gap_and_classify(feat_hwc, weights, biases, num_classes)
        assert np.array_equal(py_logits, c_logits)
        assert py_pred == c_pred


def test_full_model_c_parity_all_profiles():
    """Verify bit-exact end-to-end forward pass parity across all 3 trained models."""
    profiles = [
        "fpga/pynq_z2/micro_resnet/micro_resnet_weights_cifar10_4class.json",
        "fpga/pynq_z2/micro_resnet/micro_resnet_weights_cifar10_10class.json",
        "fpga/pynq_z2/micro_resnet/micro_resnet_weights_fashion_mnist.json"
    ]

    for p in profiles:
        weights_path = os.path.join(_REPO_ROOT, p)
        if not os.path.exists(weights_path):
            continue

        eng_py = SCIMTier3Engine(force_emulation=True, use_c_accel=False)
        eng_py.model.load_weights(weights_path)

        eng_c = SCIMTier3Engine(force_emulation=True, use_c_accel=True)
        eng_c.model.load_weights(weights_path)

        np.random.seed(505)
        for _ in range(5):
            img = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)
            r_py = eng_py.infer(img)
            r_c = eng_c.infer(img)

            diff = np.abs(r_py["logits"] - r_c["logits"])
            assert np.max(diff) == 0, f"Profile {p} discrepancy: {np.max(diff)}"
            assert r_py["pred_class"] == r_c["pred_class"]


def test_graceful_fallback_when_disabled():
    """Verify that setting use_c_accel=False transparently falls back to Python."""
    engine = SCIMTier3Engine(force_emulation=True, use_c_accel=False)
    assert engine.use_c_accel is False

    test_img = np.full((32, 32, 3), 128, dtype=np.uint8)
    res = engine.infer(test_img)
    assert "pred_class" in res
    assert "logits" in res
    assert res["pred_idx"] >= 0
