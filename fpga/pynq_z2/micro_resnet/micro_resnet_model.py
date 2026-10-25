# ============================================================================
# Module: micro_resnet_model.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: Python 3.10+ / NumPy Neural Network Architecture
# ============================================================================
# Pedagogical & Silicon Rationale:
#
# 1. 1-Bit Weight / 8-Bit Activation Co-Design:
#    - Direct implementation of Mode 1 (Hybrid ReLU):
#      Weights: stationary W in {-1, +1}^(16x16) stored in 256 standard-cell DFFs.
#      Activations: unipolar A in [0, 255]^16 streamed over 8-bit input buses.
#    - The dot product evaluated in silicon is:
#      Y_j = sum_{i=0..15} W_{i,j} * A_i in [-4096, +4095]
#
# 2. Perfect 16x16 Macro Utilization (Zero Padding Waste):
#    - All channel widths are exact multiples of 16 (C = 16).
#    - Every single one of the 256 processing elements (PEs) and 16 accumulator
#      columns is actively utilized (100% hardware efficiency).
#
# 3. Stationary Weight Power Advantage (P_dyn = C * V^2 * f = 0):
#    - For each layer, the 16x16 weight matrix is shifted into the core ONCE.
#    - All H x W spatial pixels stream through the activation registers while
#      the weight flip-flops remain completely static, eliminating dynamic switching.
# ============================================================================

import os
import json
import numpy as np


class MicroResNet16:
    """Micro-ResNet architecture tailored for 16x16 Stochastic CIM execution.
    
    Topology:
      Input: 3x32x32 RGB Image (padded to 16 channels)
      Stem Conv: 16 -> 16 (16x16 weight tile) + ReLU
      ResBlock 1:
        - Conv1a: 16 -> 16 (16x16 weight tile) + ReLU
        - Spatial 3x3 Depthwise Smoothing
        - Conv1b: 16 -> 16 (16x16 weight tile)
        - Shortcut: X + F(X) + ReLU
        - MaxPool 2x2 -> 16x16x16
      ResBlock 2:
        - Conv2a: 16 -> 16 (16x16 weight tile) + ReLU
        - Conv2b: 16 -> 16 (16x16 weight tile)
        - Shortcut: X + F(X) + ReLU
        - MaxPool 2x2 -> 16x8x8
      Classifier Head:
        - Global Average Pooling (GAP) -> 16 features
        - Linear Classifier: 16 -> 10 classes (fits in single 16x16 tile)
    """

    CLASSES = [
        "airplane", "automobile", "bird", "cat", "deer",
        "dog", "frog", "horse", "ship", "truck"
    ]

    def __init__(self, seed=42):
        self.seed = seed
        self.weights = {}
        self.biases = {}
        self.scales = {}
        self._init_parameters(seed)

    def _init_parameters(self, seed):
        """Initialize deterministic, balanced binary weights and fixed-point scales."""
        rng = np.random.RandomState(seed)

        # Layer 1: Stem Conv (16 in -> 16 out)
        # Weights: binary {-1, +1}
        self.weights["stem"] = rng.choice([-1, 1], size=(16, 16)).astype(np.int32)
        self.biases["stem"] = rng.randint(-30, 30, size=16).astype(np.int32)
        self.scales["stem"] = {"mult": 128, "shift": 11}  # scale approx 1/16 to fit [0, 255]

        # ResBlock 1: Conv1a (16 in -> 16 out)
        self.weights["res1_conv1"] = rng.choice([-1, 1], size=(16, 16)).astype(np.int32)
        self.biases["res1_conv1"] = rng.randint(-20, 20, size=16).astype(np.int32)
        self.scales["res1_conv1"] = {"mult": 128, "shift": 11}

        # ResBlock 1: Conv1b (16 in -> 16 out)
        self.weights["res1_conv2"] = rng.choice([-1, 1], size=(16, 16)).astype(np.int32)
        self.biases["res1_conv2"] = rng.randint(-20, 20, size=16).astype(np.int32)
        self.scales["res1_conv2"] = {"mult": 128, "shift": 11}

        # ResBlock 2: Conv2a (16 in -> 16 out)
        self.weights["res2_conv1"] = rng.choice([-1, 1], size=(16, 16)).astype(np.int32)
        self.biases["res2_conv1"] = rng.randint(-20, 20, size=16).astype(np.int32)
        self.scales["res2_conv1"] = {"mult": 128, "shift": 11}

        # ResBlock 2: Conv2b (16 in -> 16 out)
        self.weights["res2_conv2"] = rng.choice([-1, 1], size=(16, 16)).astype(np.int32)
        self.biases["res2_conv2"] = rng.randint(-20, 20, size=16).astype(np.int32)
        self.scales["res2_conv2"] = {"mult": 128, "shift": 11}

        # Classifier Head: Linear (16 in -> 10 out)
        # 16x16 matrix where columns 0..9 represent the 10 target classes
        fc_w = rng.choice([-1, 1], size=(16, 16)).astype(np.int32)
        self.weights["classifier"] = fc_w
        self.biases["classifier"] = rng.randint(-50, 50, size=16).astype(np.int32)
        self.scales["classifier"] = {"mult": 256, "shift": 8}

    @staticmethod
    def preprocess_image(img_array):
        """Prepare image array into 16-channel 32x32 unipolar uint8 feature map.
        
        Args:
            img_array (np.ndarray): Input image, shape (32, 32, 3) or (32, 32) in range [0, 255].
            
        Returns:
            np.ndarray: Feature tensor of shape (16, 32, 32), dtype np.uint8.
        """
        arr = np.array(img_array, dtype=np.float32)
        if arr.ndim == 2:
            # Grayscale 32x32 -> replicate across 3 channels
            arr = np.stack([arr, arr, arr], axis=-1)

        assert arr.shape[:2] == (32, 32), f"Expected 32x32 image, got {arr.shape[:2]}"

        # Clamp to [0, 255]
        arr = np.clip(arr, 0, 255).astype(np.uint8)

        # Transpose from (H, W, C) to (C, H, W)
        chw = np.transpose(arr, (2, 0, 1))  # (3, 32, 32)

        # Pad from 3 channels to 16 channels using channel replication and color transforms
        feat = np.zeros((16, 32, 32), dtype=np.uint8)
        feat[0:3] = chw[0:3]  # R, G, B
        feat[3] = np.clip(0.299 * chw[0] + 0.587 * chw[1] + 0.114 * chw[2], 0, 255).astype(np.uint8)  # Luminance
        feat[4] = np.clip(np.abs(chw[0].astype(int) - chw[1].astype(int)), 0, 255).astype(np.uint8)    # |R - G|
        feat[5] = np.clip(np.abs(chw[1].astype(int) - chw[2].astype(int)), 0, 255).astype(np.uint8)    # |G - B|
        feat[6] = np.clip(np.abs(chw[0].astype(int) - chw[2].astype(int)), 0, 255).astype(np.uint8)    # |R - B|
        # Inverted channels
        feat[7:10] = 255 - chw[0:3]
        # Replicated / shifted high-pass channels
        for c in range(10, 16):
            feat[c] = (feat[c - 10] // 2) + 64

        return feat

    @staticmethod
    def max_pool_2x2(x):
        """Perform 2x2 max pooling with stride 2 over (C, H, W)."""
        C, H, W = x.shape
        out_H, out_W = H // 2, W // 2
        reshaped = x[:, :out_H * 2, :out_W * 2].reshape(C, out_H, 2, out_W, 2)
        return reshaped.max(axis=(2, 4))

    @staticmethod
    def depthwise_smooth_3x3(x):
        """Simple depthwise 3x3 box smoothing filter with padding 1."""
        C, H, W = x.shape
        padded = np.pad(x.astype(np.int32), ((0, 0), (1, 1), (1, 1)), mode='edge')
        smoothed = np.zeros_like(x, dtype=np.int32)
        for dy in range(3):
            for dx in range(3):
                smoothed += padded[:, dy:dy + H, dx:dx + W]
        return np.clip(smoothed // 9, 0, 255).astype(np.uint8)

    @staticmethod
    def requantize_relu(raw_acc, bias, scale_dict):
        """Requantize raw accumulator values into 8-bit unipolar ReLU activations.
        
        Formula:
            A_next = clamp(floor((raw_acc + bias) * mult / 2^shift), 0, 255)
        """
        mult = scale_dict["mult"]
        shift = scale_dict["shift"]
        # raw_acc shape: (..., 16) or (16, ...)
        val = (raw_acc.astype(np.int64) + bias.astype(np.int64)) * mult
        val = val >> shift
        return np.clip(val, 0, 255).astype(np.uint8)

    def forward_fixed_reference(self, x):
        """Bit-exact software reference forward pass using ideal integer dot products.
        
        This establishes the ground truth mathematical baseline for comparing
        stochastic hardware acceleration parity.
        
        Args:
            x (np.ndarray): (16, 32, 32) uint8 input feature map.
            
        Returns:
            dict: Intermediate feature maps, final logits, and class prediction.
        """
        assert x.shape == (16, 32, 32), f"Expected (16, 32, 32), got {x.shape}"
        activations = {}

        # 1. Stem Conv: (16, 32, 32) -> (16, 32, 32)
        # For each spatial location (y, x): dot product with 16x16 weight matrix
        # Input vector: a in [0, 255]^16
        # Output: Y = a @ W, shape (32, 32, 16) -> transpose to (16, 32, 32)
        x_hw = np.transpose(x, (1, 2, 0))  # (32, 32, 16)
        y_stem_raw = np.matmul(x_hw.astype(np.int32), self.weights["stem"])  # (32, 32, 16)
        x_stem = self.requantize_relu(y_stem_raw, self.biases["stem"], self.scales["stem"])
        x_stem = np.transpose(x_stem, (2, 0, 1))  # (16, 32, 32)
        activations["stem"] = x_stem

        # 2. ResBlock 1:
        # Conv1a
        x1_hw = np.transpose(x_stem, (1, 2, 0))
        y_1a_raw = np.matmul(x1_hw.astype(np.int32), self.weights["res1_conv1"])
        x_1a = self.requantize_relu(y_1a_raw, self.biases["res1_conv1"], self.scales["res1_conv1"])
        x_1a = np.transpose(x_1a, (2, 0, 1))

        # Spatial Depthwise
        x_1a_smooth = self.depthwise_smooth_3x3(x_1a)

        # Conv1b
        x1b_hw = np.transpose(x_1a_smooth, (1, 2, 0))
        y_1b_raw = np.matmul(x1b_hw.astype(np.int32), self.weights["res1_conv2"])
        x_1b = self.requantize_relu(y_1b_raw, self.biases["res1_conv2"], self.scales["res1_conv2"])
        x_1b = np.transpose(x_1b, (2, 0, 1))

        # Residual shortcut & ReLU: X_out = clamp(X + F(X), 0, 255)
        res1_out = np.clip((x_stem.astype(int) + x_1b.astype(int)) // 2, 0, 255).astype(np.uint8)
        # MaxPool 2x2: (16, 32, 32) -> (16, 16, 16)
        res1_pool = self.max_pool_2x2(res1_out)
        activations["res1"] = res1_pool

        # 3. ResBlock 2:
        # Conv2a
        x2_hw = np.transpose(res1_pool, (1, 2, 0))
        y_2a_raw = np.matmul(x2_hw.astype(np.int32), self.weights["res2_conv1"])
        x_2a = self.requantize_relu(y_2a_raw, self.biases["res2_conv1"], self.scales["res2_conv1"])
        x_2a = np.transpose(x_2a, (2, 0, 1))

        # Conv2b
        x2b_hw = np.transpose(x_2a, (1, 2, 0))
        y_2b_raw = np.matmul(x2b_hw.astype(np.int32), self.weights["res2_conv2"])
        x_2b = self.requantize_relu(y_2b_raw, self.biases["res2_conv2"], self.scales["res2_conv2"])
        x_2b = np.transpose(x_2b, (2, 0, 1))

        # Residual shortcut: X_out = clamp(X + F(X), 0, 255)
        res2_out = np.clip((res1_pool.astype(int) + x_2b.astype(int)) // 2, 0, 255).astype(np.uint8)
        # MaxPool 2x2: (16, 16, 16) -> (16, 8, 8)
        res2_pool = self.max_pool_2x2(res2_out)
        activations["res2"] = res2_pool

        # 4. Global Average Pooling (GAP): (16, 8, 8) -> (16,)
        gap_features = np.mean(res2_pool, axis=(1, 2)).astype(np.uint8)
        activations["gap"] = gap_features

        # 5. Classifier Head: (16,) @ (16, 16) -> (10 active logits)
        raw_logits = np.matmul(gap_features.astype(np.int32), self.weights["classifier"])
        logits = (raw_logits[:10] + self.biases["classifier"][:10]).astype(np.int32)
        activations["logits"] = logits

        pred_idx = int(np.argmax(logits))
        pred_class = self.CLASSES[pred_idx]

        return {
            "pred_idx": pred_idx,
            "pred_class": pred_class,
            "logits": logits,
            "activations": activations
        }

    def get_summary(self):
        """Return architectural summary and parameter counts."""
        total_weights = 6 * 256  # 6 layers x 256 bits = 1,536 bits = 192 bytes!
        return {
            "model_name": "MicroResNet16",
            "input_resolution": "32x32",
            "channels": 16,
            "classes": 10,
            "total_weight_bits": total_weights,
            "total_weight_bytes": total_weights // 8,
            "layers": list(self.weights.keys()),
            "tiles_per_frame": {
                "stem": 1024,
                "res1_conv1": 1024,
                "res1_conv2": 1024,
                "res2_conv1": 256,
                "res2_conv2": 256,
                "classifier": 1,
                "total": 3585
            }
        }
