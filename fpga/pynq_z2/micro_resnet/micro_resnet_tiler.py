# ============================================================================
# Module: micro_resnet_tiler.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: Python 3.10+ / GEMM Tiling & Stationary Weight Scheduler
# ============================================================================
# Pedagogical & Silicon Rationale:
#
# 1. Stationary Weight Memory Scheduling:
#    - Shifting 256 bits serially through `w_din` requires 256 clock cycles.
#    - In continuous mission-mode vision (e.g. 1024 spatial pixels in a 32x32 feature map),
#      reloading weights for each pixel would waste 1024 * 256 = 262,144 unnecessary shift cycles!
#    - The Tiler tracks the currently loaded weight state. It loads W ONCE per layer,
#      achieving a 262,144 -> 256 cycle reduction (99.9% reduction in weight shift traffic).
#
# 2. im2col Lowering to 16x16 CIM Macro:
#    - For 1x1 convolutions (pointwise), each spatial pixel (y, x) is an independent
#      16-element unipolar activation vector A in [0, 255]^16.
#    - Output accumulators directly form the output channel activations at (y, x).
# ============================================================================

import time
import numpy as np


class MicroResNetTiler:
    """Manages GEMM lowering, 16x16 tile execution, and stationary weight caching."""

    def __init__(self, driver):
        """Initialize the tiler with an underlying hardware or emulated driver.
        
        Args:
            driver: Instance of SCIMPynqDriver or equivalent MMIO engine.
        """
        self.driver = driver
        self.current_layer_id = None
        self.stats = {
            "total_tiles": 0,
            "weight_loads": 0,
            "total_hardware_cycles": 0,
            "total_execution_time_sec": 0.0,
            "zero_activation_count": 0,
            "total_activation_count": 0,
        }

    def reset_stats(self):
        """Reset profiling statistics."""
        for key in self.stats:
            self.stats[key] = 0 if isinstance(self.stats[key], int) else 0.0

    def load_layer_weights(self, layer_id, weight_matrix_16x16):
        """Load 16x16 binary weights if not already resident in the macro's DFFs."""
        W = np.array(weight_matrix_16x16, dtype=int)
        assert W.shape == (16, 16), f"Expected 16x16 matrix, got {W.shape}"

        if self.current_layer_id != layer_id:
            # Shift binary weights into stationary memory
            # Map bipolar {-1, +1} to binary bits: +1 -> 1, -1 -> 0
            binary_w = np.where(W > 0, 1, 0).astype(int)
            self.driver.load_weights(binary_w)
            self.current_layer_id = layer_id
            self.stats["weight_loads"] += 1

    def execute_conv1x1_layer(self, layer_id, input_feat_16xHxW, weight_matrix_16x16,
                              bias_16, scale_dict):
        """Execute a 1x1 conv layer across all HxW spatial pixels using stationary weights.
        
        Args:
            layer_id (str): Unique identifier for weight caching.
            input_feat_16xHxW (np.ndarray): Shape (16, H, W), dtype uint8.
            weight_matrix_16x16 (np.ndarray): Shape (16, 16) bipolar weights {-1, +1}.
            bias_16 (np.ndarray): 16-element integer bias vector.
            scale_dict (dict): Requantization scale {'mult': int, 'shift': int}.
            
        Returns:
            np.ndarray: Requantized output feature map of shape (16, H, W), dtype uint8.
        """
        C, H, W = input_feat_16xHxW.shape
        assert C == 16, f"Expected 16 input channels, got {C}"

        t_start = time.perf_counter()

        # Step 1: Ensure layer weights are resident in stationary DFFs
        self.load_layer_weights(layer_id, weight_matrix_16x16)

        # Step 2: Transpose feature map from (C, H, W) to (H, W, C) for spatial streaming
        feat_hw_c = np.transpose(input_feat_16xHxW, (1, 2, 0))  # (H, W, 16)
        out_hw_c = np.zeros((H, W, 16), dtype=np.uint8)

        mult = scale_dict["mult"]
        shift = scale_dict["shift"]

        # Step 3: Stream each spatial pixel through the 16 activation registers
        for y in range(H):
            for x in range(W):
                act_vec = feat_hw_c[y, x]  # 16-element uint8

                # Record ReLU sparsity statistics
                zeros = np.count_nonzero(act_vec == 0)
                self.stats["zero_activation_count"] += zeros
                self.stats["total_activation_count"] += 16
                self.stats["total_tiles"] += 1

                # Execute stochastic MVM in Mode 1 (Hybrid ReLU)
                res = self.driver.run_mvm(act_vec, mode=1)
                raw_acc = res["results"]  # 16 signed 13-bit values
                self.stats["total_hardware_cycles"] += res.get("cycles", 257)

                # Requantize and apply ReLU: clamp(floor((acc + bias) * mult / 2^shift), 0, 255)
                val = (raw_acc.astype(np.int64) + bias_16.astype(np.int64)) * mult
                val = val >> shift
                out_hw_c[y, x] = np.clip(val, 0, 255).astype(np.uint8)

        # Step 4: Transpose back to (16, H, W)
        out_feat = np.transpose(out_hw_c, (2, 0, 1))

        t_end = time.perf_counter()
        self.stats["total_execution_time_sec"] += (t_end - t_start)

        return out_feat

    def execute_linear_layer(self, layer_id, input_vec_16, weight_matrix_16x16, bias_16):
        """Execute a dense/linear layer for classification (16 in -> 10 active outputs).
        
        Args:
            layer_id (str): Unique layer name.
            input_vec_16 (np.ndarray): 16-element activation vector in [0, 255].
            weight_matrix_16x16 (np.ndarray): 16x16 weight matrix.
            bias_16 (np.ndarray): 16-element bias vector.
            
        Returns:
            np.ndarray: 10 signed integer class logits.
        """
        assert len(input_vec_16) == 16, f"Expected 16 input features, got {len(input_vec_16)}"

        t_start = time.perf_counter()

        self.load_layer_weights(layer_id, weight_matrix_16x16)

        self.stats["total_tiles"] += 1
        self.stats["total_activation_count"] += 16
        self.stats["zero_activation_count"] += np.count_nonzero(input_vec_16 == 0)

        res = self.driver.run_mvm(input_vec_16, mode=1)
        raw_acc = res["results"]
        self.stats["total_hardware_cycles"] += res.get("cycles", 257)

        # Output logits: take first 10 columns (for 10 classes) + bias
        logits = (raw_acc[:10].astype(np.int32) + bias_16[:10].astype(np.int32))

        t_end = time.perf_counter()
        self.stats["total_execution_time_sec"] += (t_end - t_start)

        return logits

    def get_sparsity_percentage(self):
        """Return percentage of zero activations processed (ReLU zero-suppression)."""
        tot = self.stats["total_activation_count"]
        return (self.stats["zero_activation_count"] / tot * 100.0) if tot > 0 else 0.0
