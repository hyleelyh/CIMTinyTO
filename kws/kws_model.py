"""
Acoustic Quantized Neural Network (KWS-SCIM-16) for Voice Keyword Spotting.
Designed for the CIMTinyTO 16x16 Stochastic Compute-in-Memory (SCIM) Macro.

Architecture Specification:
- Input: 16 Mel frequency channels x 32 temporal frames.
- Weights: Bipolar W in {-1, +1} (1-bit binary representation in SCIM DFFs).
- Activations: Unipolar A in [0, 255] (8-bit unsigned integer).
- Compute Primitive: Mode 1 (Hybrid ReLU):
    Delta_j = 2 * sum(w_ij & a_i) - sum(a_i)
    Accumulated over N=256 stochastic clock cycles -> Y_j in [-4096, +4095].
- Stationary Weight Caching:
    Pointwise layers execute with stationary weights. Weight shift register
    is loaded once (256 cycles) per layer, remaining static across all 32 temporal frames.
- Total SCIM Weights: 3 layers x 256 bits = 768 bits = 96 BYTES!
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional


class BinaryQuantizeSTE(torch.autograd.Function):
    """
    Bipolar Weight Quantizer with Straight-Through Estimator (STE).
    Forward: W_b = sign(W) in {-1, +1} (with 0 mapped to +1).
    Backward: Surrogate gradient passing through identity within [-1.0, +1.0], zero outside.
    """
    @staticmethod
    def forward(ctx, w):
        ctx.save_for_backward(w)
        # Sign mapping: >= 0 -> +1.0, < 0 -> -1.0
        return torch.where(w >= 0.0, torch.tensor(1.0, device=w.device), torch.tensor(-1.0, device=w.device))

    @staticmethod
    def backward(ctx, grad_output):
        (w,) = ctx.saved_tensors
        # Hardtanh clipping gate for STE
        grad_w = grad_output.clone()
        grad_w[w.abs() > 1.0] = 0.0
        return grad_w


class ActivationQuantizeSTE(torch.autograd.Function):
    """
    Unipolar Activation Quantizer with Straight-Through Estimator (STE).
    Forward: Clamps to [0, 255] and rounds to nearest integer.
    Backward: Identity gradient within [0, 255].
    """
    @staticmethod
    def forward(ctx, a):
        ctx.save_for_backward(a)
        clamped = torch.clamp(a, 0.0, 255.0)
        return torch.round(clamped)

    @staticmethod
    def backward(ctx, grad_output):
        (a,) = ctx.saved_tensors
        grad_a = grad_output.clone()
        grad_a[(a < 0.0) | (a > 255.0)] = 0.0
        return grad_a


def quantize_weight(w: torch.Tensor) -> torch.Tensor:
    return BinaryQuantizeSTE.apply(w)


def quantize_activation(a: torch.Tensor) -> torch.Tensor:
    return ActivationQuantizeSTE.apply(a)


class SCIMPointwiseConv1x1(nn.Module):
    """
    16x16 Pointwise Convolution layer matching a single CIMTinyTO SCIM Tile.
    Weights are 16x16 bipolar values {-1, +1}.
    Includes per-channel learnable BatchNorm folding and activation gain scale S_act.
    """
    def __init__(self, in_channels: int = 16, out_channels: int = 16, act_gain: float = 64.0):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.act_gain = act_gain

        # Latent continuous weights initialized with standard normal
        self.weight = nn.Parameter(torch.empty(out_channels, in_channels, 1))
        nn.init.kaiming_normal_(self.weight, mode='fan_out', nonlinearity='relu')

        # Batch normalization with learnable affine parameters (gamma, beta)
        self.bn = nn.BatchNorm1d(out_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Quantize latent weights to bipolar {-1, +1}
        w_bipolar = quantize_weight(self.weight)

        # Standard 1x1 conv with bipolar weights
        y = F.conv1d(x, w_bipolar, bias=None)

        # BatchNorm
        y = self.bn(y)

        # Activation gain scaling + ReLU
        y = F.relu(y) * self.act_gain

        # Quantize activations to integer grid [0, 255]
        return quantize_activation(y)


class KWS_SCIM_16(nn.Module):
    """
    End-to-End Acoustic Keyword Spotting Neural Network for CIMTinyTO.
    Processes (B, 16, 32) Mel-filterbank spectrograms.

    Layers:
    1. Layer 1: SCIM Conv1x1 (16 -> 16 channels across 32 frames) [Tile 0]
    2. Layer 2: Host Depthwise Temporal Smoothing (3-tap Conv1d) [ARM Cortex-M33]
    3. Layer 3: SCIM Conv1x1 (16 -> 16 channels across 32 frames) [Tile 1]
    4. Layer 4: Global Temporal Average Pooling (32 -> 1) [ARM Cortex-M33]
    5. Layer 5: SCIM Linear Classifier Head (16 -> num_classes) [Tile 2]
    """
    def __init__(self, num_classes: int = 4, act_gain: float = 64.0):
        super().__init__()
        self.num_classes = num_classes
        self.act_gain = act_gain

        # Tile 0: Acoustic Projection
        self.conv1 = SCIMPointwiseConv1x1(16, 16, act_gain=act_gain)

        # Host DSP: 3-tap temporal depthwise smoothing (separable across channels)
        self.depthwise = nn.Conv1d(
            in_channels=16,
            out_channels=16,
            kernel_size=3,
            padding=1,
            groups=16,
            bias=False,
        )
        # Initialize depthwise filter to 3-tap smoothing kernel [0.25, 0.5, 0.25]
        with torch.no_grad():
            smooth_kernel = torch.tensor([0.25, 0.50, 0.25]).view(1, 1, 3).repeat(16, 1, 1)
            self.depthwise.weight.copy_(smooth_kernel)

        # Tile 1: Acoustic Feature Mixing
        self.conv2 = SCIMPointwiseConv1x1(16, 16, act_gain=act_gain)

        # Tile 2: Linear Classifier Head (16 -> num_classes)
        # Latent weights for 16x16 SCIM array (only first num_classes columns active)
        self.classifier_weight = nn.Parameter(torch.empty(16, 16))
        nn.init.kaiming_uniform_(self.classifier_weight, a=np.sqrt(5))
        self.classifier_bias = nn.Parameter(torch.zeros(num_classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        Args:
            x: Input uint8 Mel-spectrogram tensor of shape (B, 16, 32).
        Returns:
            Logits tensor of shape (B, num_classes).
        """
        # Ensure input is float in [0, 255]
        h = x.float()

        # Tile 0: Pointwise Conv1
        h = self.conv1(h)  # (B, 16, 32)

        # Host DSP: Depthwise smoothing
        h = self.depthwise(h)
        h = quantize_activation(h)

        # Tile 1: Pointwise Conv2
        h = self.conv2(h)  # (B, 16, 32)

        # Host DSP: Global Temporal Average Pooling (GAP) across 32 time frames
        # Result shape: (B, 16)
        gap_vec = torch.mean(h, dim=-1)
        gap_uint8 = quantize_activation(gap_vec)  # (B, 16)

        # Tile 2: Classifier Head
        w_bipolar = quantize_weight(self.classifier_weight)  # (16, 16)
        active_w = w_bipolar[:self.num_classes, :]  # (num_classes, 16)

        # Integer MVM: Y_k = sum_i W_{k,i} * A_i + Bias_k
        logits = F.linear(gap_uint8, active_w, self.classifier_bias)
        return logits


class FixedPointKWSModel:
    """
    Bit-Exact Fixed-Point Model of KWS_SCIM_16 replicating on-chip SCIM execution.
    Used for pre-silicon emulation, C driver parity verification, and firmware validation.
    """
    def __init__(self, weight_dict: Dict):
        self.w_tile0 = np.array(weight_dict['tile0_weights'], dtype=np.int8)  # (16, 16) in {-1, +1}
        self.m_tile0 = np.array(weight_dict['tile0_mult'], dtype=np.int32)    # (16,)
        self.b_tile0 = np.array(weight_dict['tile0_bias'], dtype=np.int32)    # (16,)
        self.shift0 = int(weight_dict.get('tile0_shift', 11))

        self.w_tile1 = np.array(weight_dict['tile1_weights'], dtype=np.int8)  # (16, 16)
        self.m_tile1 = np.array(weight_dict['tile1_mult'], dtype=np.int32)    # (16,)
        self.b_tile1 = np.array(weight_dict['tile1_bias'], dtype=np.int32)    # (16,)
        self.shift1 = int(weight_dict.get('tile1_shift', 11))

        self.w_classifier = np.array(weight_dict['classifier_weights'], dtype=np.int8)  # (num_classes, 16)
        self.b_classifier = np.array(weight_dict['classifier_biases'], dtype=np.int32)  # (num_classes,)
        self.num_classes = len(self.b_classifier)
        self.class_names = weight_dict.get('class_names', ['silence', 'unknown', 'yes', 'no'])

    @staticmethod
    def execute_scim_tile(weights_16x16: np.ndarray, act_16: np.ndarray) -> np.ndarray:
        """
        Simulate a single 16x16 SCIM tile in Mode 1 (Hybrid ReLU):
        Delta_j = 2 * sum(w_ij & a_i) - sum(a_i) = sum(W_ij * A_i)
        Returns: Signed 16-element integer vector Y in [-4096, +4095].
        """
        # Exact dot product of bipolar matrix {-1, +1} with unipolar activation vector [0, 255]
        return np.dot(weights_16x16.astype(np.int32), act_16.astype(np.int32))

    def forward(self, input_spec_16x32: np.ndarray) -> Tuple[np.ndarray, int, str]:
        """
        Bit-exact forward pass matching STM32 + CIMTinyTO execution.
        Args:
            input_spec_16x32: (16, 32) uint8 array.
        Returns:
            (logits, predicted_class_idx, predicted_class_name)
        """
        num_frames = input_spec_16x32.shape[1]

        # 1. Tile 0: Stationary weight execution across 32 frames
        feat1 = np.zeros((16, num_frames), dtype=np.uint8)
        for t in range(num_frames):
            a_vec = input_spec_16x32[:, t]
            y_raw = self.execute_scim_tile(self.w_tile0, a_vec)  # (16,)
            # Requantization: (Y * M + B) >> shift
            y_scaled = (y_raw * self.m_tile0 + self.b_tile0) >> self.shift0
            y_clamped = np.clip(y_scaled, 0, 255).astype(np.uint8)
            feat1[:, t] = y_clamped

        # 2. Host DSP: 3-tap temporal smoothing [0.25, 0.50, 0.25]
        feat1_smooth = np.zeros_like(feat1)
        for c in range(16):
            row = feat1[c, :].astype(np.int32)
            for t in range(num_frames):
                left = row[t - 1] if t > 0 else row[0]
                center = row[t]
                right = row[t + 1] if t < num_frames - 1 else row[-1]
                val = (left + 2 * center + right + 2) >> 2  # integer division by 4
                feat1_smooth[c, t] = np.clip(val, 0, 255).astype(np.uint8)

        # 3. Tile 1: Stationary weight execution across 32 frames
        feat2 = np.zeros((16, num_frames), dtype=np.uint8)
        for t in range(num_frames):
            a_vec = feat1_smooth[:, t]
            y_raw = self.execute_scim_tile(self.w_tile1, a_vec)
            y_scaled = (y_raw * self.m_tile1 + self.b_tile1) >> self.shift1
            y_clamped = np.clip(y_scaled, 0, 255).astype(np.uint8)
            feat2[:, t] = y_clamped

        # 4. Host DSP: Global Temporal Average Pooling (GAP) across 32 frames
        # Integer average: sum(feat2, axis=1) // num_frames
        gap_vec = (np.sum(feat2.astype(np.int32), axis=1) + (num_frames // 2)) // num_frames
        gap_vec = np.clip(gap_vec, 0, 255).astype(np.uint8)

        # 5. Tile 2: Classifier Head
        y_class_raw = np.dot(self.w_classifier.astype(np.int32), gap_vec.astype(np.int32))
        logits = y_class_raw + self.b_classifier

        pred_idx = int(np.argmax(logits))
        pred_name = self.class_names[pred_idx] if pred_idx < len(self.class_names) else f"class_{pred_idx}"

        return logits, pred_idx, pred_name
