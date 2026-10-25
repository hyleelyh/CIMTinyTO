# ============================================================================
# Test Suite: test_micro_resnet.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: pytest / Production Verification Harness
# ============================================================================

import os
import sys
import pytest
import numpy as np

# Ensure project root is in system path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(TEST_DIR, ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from fpga.pynq_z2.micro_resnet.micro_resnet_model import MicroResNet16
from fpga.pynq_z2.micro_resnet.micro_resnet_tiler import MicroResNetTiler
from fpga.pynq_z2.micro_resnet.scim_tier1_mmio import SCIMTier1Engine
from fpga.pynq_z2.micro_resnet.scim_tier2_wrapper import SCIMTier2Engine
from fpga.pynq_z2.micro_resnet.scim_tier3_dma import SCIMTier3Engine
from fpga.pynq_z2.micro_resnet.vision_pipeline import EdgeVisionPipeline
from model.sim_scim import SCIMTile, ProcessingElement


class TestMicroResNetArchitecture:
    """Validate neural network architecture, shapes, and parameter counts."""

    def test_model_summary_and_parameter_count(self):
        model = MicroResNet16(seed=42)
        summary = model.get_summary()

        assert summary["model_name"] == "MicroResNet16"
        assert summary["channels"] == 16
        assert summary["classes"] == 10
        # 6 layers x 256 bits = 1,536 bits = 192 bytes total memory footprint!
        assert summary["total_weight_bits"] == 1536
        assert summary["total_weight_bytes"] == 192
        assert len(summary["layers"]) == 6
        assert summary["tiles_per_frame"]["total"] == 3585

    def test_image_preprocessing_channels(self):
        model = MicroResNet16(seed=42)
        dummy_img = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)
        feat = model.preprocess_image(dummy_img)

        assert feat.shape == (16, 32, 32)
        assert feat.dtype == np.uint8
        assert np.all(feat >= 0) and np.all(feat <= 255)

    def test_fixed_point_reference_forward(self):
        model = MicroResNet16(seed=42)
        dummy_img = np.zeros((32, 32, 3), dtype=np.uint8)
        dummy_img[8:24, 8:24] = 200  # Center bright box
        feat = model.preprocess_image(dummy_img)

        out = model.forward_fixed_reference(feat)
        assert "pred_idx" in out
        assert "pred_class" in out
        assert out["pred_idx"] in range(10)
        assert len(out["logits"]) == 10
        assert out["activations"]["stem"].shape == (16, 32, 32)
        assert out["activations"]["res1"].shape == (16, 16, 16)
        assert out["activations"]["res2"].shape == (16, 8, 8)
        assert out["activations"]["gap"].shape == (16,)


class TestStationaryWeightCaching:
    """Verify that stationary standard-cell DFF memory eliminates redundant weight shifts."""

    def test_weight_shift_caching(self):
        from fpga.pynq_z2.jupyter.scim_pynq_driver import SCIMPynqDriver

        driver = SCIMPynqDriver(force_emulation=True)
        tiler = MicroResNetTiler(driver)

        W1 = np.ones((16, 16), dtype=int)
        W2 = -np.ones((16, 16), dtype=int)

        # 1. First load of W1: must increment weight_loads
        tiler.load_layer_weights("layer_stem", W1)
        assert tiler.stats["weight_loads"] == 1

        # 2. Subsequent accesses to layer_stem: must NOT reload
        tiler.load_layer_weights("layer_stem", W1)
        tiler.load_layer_weights("layer_stem", W1)
        assert tiler.stats["weight_loads"] == 1

        # 3. Switching to layer_res1: must reload
        tiler.load_layer_weights("layer_res1", W2)
        assert tiler.stats["weight_loads"] == 2


class TestGate0NumericalParity:
    """Verify that MVM tiles executed via drivers match Gate 0 golden model."""

    def test_mode1_hybrid_relu_parity(self):
        from fpga.pynq_z2.jupyter.scim_pynq_driver import SCIMPynqDriver

        driver = SCIMPynqDriver(force_emulation=True)
        rng = np.random.RandomState(123)

        # Generate realistic weights {-1, +1} and activations [0, 255]
        W = rng.choice([-1, 1], size=(16, 16)).astype(int)
        binary_w = np.where(W > 0, 1, 0).astype(int)
        act = rng.randint(0, 256, size=16).astype(int)

        # 1. Driver execution
        driver.reset()
        driver.load_weights(binary_w)
        res_driver = driver.run_mvm(act, mode=SCIMPynqDriver.MODE_HYBRID_RELU)
        hw_out = res_driver["results"]

        # 2. Gate 0 Golden Model
        tile = SCIMTile()
        tile.load_weights(binary_w)
        res_golden = tile.run_mvm(act, mode=ProcessingElement.MODE_HYBRID_RELU, N=256)
        golden_out = res_golden["results"]

        # Assert 100% bit-exact parity
        diff = np.abs(hw_out - golden_out)
        assert np.all(diff == 0), f"Parity mismatch: max diff {np.max(diff)} LSBs"


class TestMultiTierEngines:
    """Validate Tier 1, Tier 2, and Tier 3 execution engines."""

    def test_tier2_c_driver_functional(self):
        engine2 = SCIMTier2Engine(force_sim=True, seed=42)
        test_pattern = np.zeros((32, 32, 3), dtype=np.uint8)
        test_pattern[10:22, 10:22] = 255

        res = engine2.infer(test_pattern)
        assert res["tier"] == "Tier 2: Compiled C MMIO"
        assert res["total_tiles"] == 3585
        assert res["pred_idx"] in range(10)
        assert len(res["logits"]) == 10

    def test_tier3_dma_line_rate(self):
        engine3 = SCIMTier3Engine(seed=42)
        test_pattern = np.zeros((32, 32, 3), dtype=np.uint8)

        res = engine3.infer(test_pattern)
        assert res["tier"] == "Tier 3: Autonomous Feeder / AXI-DMA"
        assert res["total_tiles"] == 3585
        assert res["tile_latency_us"] == pytest.approx(6.08, abs=0.1)
        assert res["fps"] > 20.0  # Line rate sustains >20 FPS
        assert res["stationary_power_saving_pct"] > 99.0

    def test_vision_pipeline_hud_generation(self):
        pipeline = EdgeVisionPipeline(force_emulation=True, seed=42)
        pattern = pipeline.generate_synthetic_pattern("circle")

        # Run Tier 2 inference (fast)
        res = pipeline.run_inference(pattern, tier=2)
        assert len(res["top3"]) == 3
        assert sum(res["probabilities"]) == pytest.approx(1.0, abs=1e-4)

        # Render HUD
        hud_img = pipeline.render_hud_overlay(res, scale=4)
        assert hud_img.size == (32 * 4, (32 * 4) + 90)
