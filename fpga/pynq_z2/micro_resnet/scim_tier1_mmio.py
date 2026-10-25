# ============================================================================
# Module: scim_tier1_mmio.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: Python 3.10+ / Tier 1 Pure Python MMIO Driver
# ============================================================================
# Pedagogical & Silicon Rationale:
#
# 1. The Python Bytecode & OS Context Bottleneck (Tier 1 Baseline):
#    - In Tier 1, each 16x16 tile requires:
#      - 16 AXI writes for activations (REG_DATA_IN + REG_CTRL strobe)
#      - 1 AXI write to assert start_req in REG_CTRL
#      - Polling REG_STATUS in a Python `while not done:` loop
#      - 32 AXI writes/reads to fetch low/high accumulator bytes across 16 columns
#    - Although the hardware core computes the 256 cycles in 5.12 us @ 50 MHz,
#      Python interpreter overhead, object allocations, and un-pipelined AXI transactions
#      stretch each tile to ~180 us!
#    - For ~3,585 tiles/frame: 3,585 * 180 us = ~0.65 to 1.4 seconds (~0.7 to 1.5 FPS).
#    - Tier 1 establishes the baseline for correctness, functional verification, and debug.
# ============================================================================

import os
import sys
import time
import numpy as np

# Ensure model and driver paths are available
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../.."))
for candidate in [os.path.join(CURRENT_DIR, "..", "jupyter"), os.path.join(PROJ_ROOT, "fpga/pynq_z2/jupyter")]:
    if os.path.exists(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

from scim_pynq_driver import SCIMPynqDriver
from .micro_resnet_model import MicroResNet16
from .micro_resnet_tiler import MicroResNetTiler


class SCIMTier1Engine:
    """Tier 1: Pure Python MMIO Micro-ResNet Inference Engine."""

    def __init__(self, bitstream_path=None, force_emulation=False, seed=42):
        self.driver = SCIMPynqDriver(bitstream_path=bitstream_path, force_emulation=force_emulation)
        self.model = MicroResNet16(seed=seed)
        self.tiler = MicroResNetTiler(self.driver)

    def infer(self, img_array):
        """Run complete end-to-end Micro-ResNet inference on a single image.
        
        Args:
            img_array (np.ndarray): (32, 32, 3) or (32, 32) image in [0, 255].
            
        Returns:
            dict: {
                "pred_class": str,
                "pred_idx": int,
                "logits": np.ndarray (10,),
                "total_time_sec": float,
                "fps": float,
                "tile_latency_us": float,
                "total_tiles": int,
                "hardware_cycles": int,
                "sparsity_pct": float,
                "weight_loads": int
            }
        """
        self.tiler.reset_stats()
        t_start = time.perf_counter()

        # Step 1: Image preprocessing
        x = self.model.preprocess_image(img_array)

        # Step 2: Stem Conv (16 in -> 16 out @ 32x32)
        x_stem = self.tiler.execute_conv1x1_layer(
            layer_id="stem",
            input_feat_16xHxW=x,
            weight_matrix_16x16=self.model.weights["stem"],
            bias_16=self.model.biases["stem"],
            scale_dict=self.model.scales["stem"]
        )

        # Step 3: ResBlock 1
        x_1a = self.tiler.execute_conv1x1_layer(
            layer_id="res1_conv1",
            input_feat_16xHxW=x_stem,
            weight_matrix_16x16=self.model.weights["res1_conv1"],
            bias_16=self.model.biases["res1_conv1"],
            scale_dict=self.model.scales["res1_conv1"]
        )
        x_1a_smooth = self.model.depthwise_smooth_3x3(x_1a)

        x_1b = self.tiler.execute_conv1x1_layer(
            layer_id="res1_conv2",
            input_feat_16xHxW=x_1a_smooth,
            weight_matrix_16x16=self.model.weights["res1_conv2"],
            bias_16=self.model.biases["res1_conv2"],
            scale_dict=self.model.scales["res1_conv2"]
        )
        res1_out = np.clip((x_stem.astype(int) + x_1b.astype(int)) // 2, 0, 255).astype(np.uint8)
        res1_pool = self.model.max_pool_2x2(res1_out)  # 16x16x16

        # Step 4: ResBlock 2
        x_2a = self.tiler.execute_conv1x1_layer(
            layer_id="res2_conv1",
            input_feat_16xHxW=res1_pool,
            weight_matrix_16x16=self.model.weights["res2_conv1"],
            bias_16=self.model.biases["res2_conv1"],
            scale_dict=self.model.scales["res2_conv1"]
        )
        x_2b = self.tiler.execute_conv1x1_layer(
            layer_id="res2_conv2",
            input_feat_16xHxW=x_2a,
            weight_matrix_16x16=self.model.weights["res2_conv2"],
            bias_16=self.model.biases["res2_conv2"],
            scale_dict=self.model.scales["res2_conv2"]
        )
        res2_out = np.clip((res1_pool.astype(int) + x_2b.astype(int)) // 2, 0, 255).astype(np.uint8)
        res2_pool = self.model.max_pool_2x2(res2_out)  # 16x8x8

        # Step 5: Global Average Pooling (GAP)
        gap_vec = np.mean(res2_pool, axis=(1, 2)).astype(np.uint8)

        # Step 6: Classification Head (16 in -> 10 classes)
        logits = self.tiler.execute_linear_layer(
            layer_id="classifier",
            input_vec_16=gap_vec,
            weight_matrix_16x16=self.model.weights["classifier"],
            bias_16=self.model.biases["classifier"]
        )

        t_end = time.perf_counter()
        total_time = t_end - t_start
        total_tiles = self.tiler.stats["total_tiles"]
        avg_tile_us = (total_time / total_tiles * 1e6) if total_tiles > 0 else 0.0

        pred_idx = int(np.argmax(logits))
        pred_class = self.model.CLASSES[pred_idx]

        return {
            "tier": "Tier 1: Pure Python MMIO",
            "pred_class": pred_class,
            "pred_idx": pred_idx,
            "logits": logits,
            "total_time_sec": total_time,
            "fps": (1.0 / total_time) if total_time > 0 else 0.0,
            "tile_latency_us": avg_tile_us,
            "total_tiles": total_tiles,
            "hardware_cycles": self.tiler.stats["total_hardware_cycles"],
            "sparsity_pct": self.tiler.get_sparsity_percentage(),
            "weight_loads": self.tiler.stats["weight_loads"]
        }
