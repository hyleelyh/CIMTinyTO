# ============================================================================
# Module: micro_resnet_qat.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: Python 3.10+ / PyTorch 2.0+ Quantization-Aware Training
# ============================================================================
# Pedagogical & Silicon Rationale:
#
# 1. Straight-Through Estimator (STE) for Discrete Binary Weights (W in {-1, +1}):
#    - Standard backpropagation fails because d/dx sign(x) = 0 almost everywhere.
#    - BinaryQuantizeSTE implements forward binarization sign(W) while passing
#      surrogate gradients dL/dW_latent = dL/dW_bin * 1_{|W_latent| <= 1.0}.
#    - This enables continuous latent gradient descent to optimize stationary DFFs.
#
# 2. Activation Fake-Quantization (A in [0, 255]):
#    - Clamps feature maps to [0, 255] and rounds to nearest integer.
#    - Ensures training dynamics strictly reflect the on-chip 8-bit LFSR SNG
#      input resolution and integer accumulators.
#
# 3. Exact 1-to-1 Mapping to MicroResNet16 Hardware Topology:
#    - 6 binary weight matrices of shape 16x16 (192 bytes total memory).
#    - BatchNorm layers designed for subsequent algebraic folding into integer
#      ASIC biases B and multiplier/shift scales (M, S).
# ============================================================================

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class BinaryQuantizeSTE(torch.autograd.Function):
    """Straight-Through Estimator (STE) for binarizing weights to {-1.0, +1.0}."""

    @staticmethod
    def forward(ctx, input_tensor):
        ctx.save_for_backward(input_tensor)
        # Binarize: >= 0 -> +1.0, < 0 -> -1.0
        return torch.where(input_tensor >= 0.0,
                           torch.tensor(1.0, dtype=input_tensor.dtype, device=input_tensor.device),
                           torch.tensor(-1.0, dtype=input_tensor.dtype, device=input_tensor.device))

    @staticmethod
    def backward(ctx, grad_output):
        input_tensor, = ctx.saved_tensors
        # Hardtanh gradient mask: clip gradient when latent weight exceeds [-1.0, +1.0]
        mask = (input_tensor >= -1.0) & (input_tensor <= 1.0)
        return grad_output * mask.float()


class ActivationQuantizeSTE(torch.autograd.Function):
    """Quantizes continuous activations to unsigned 8-bit integers [0.0, 255.0]."""

    @staticmethod
    def forward(ctx, input_tensor):
        ctx.save_for_backward(input_tensor)
        clamped = torch.clamp(input_tensor, 0.0, 255.0)
        return torch.round(clamped)

    @staticmethod
    def backward(ctx, grad_output):
        input_tensor, = ctx.saved_tensors
        # Identity gradient within active activation range [0.0, 255.0]
        mask = (input_tensor >= 0.0) & (input_tensor <= 255.0)
        return grad_output * mask.float()


class BinarizedConv1x1(nn.Module):
    """1x1 Convolution with 1-bit binary weights {-1, +1} matching 16x16 CIM macro."""

    def __init__(self, in_channels=16, out_channels=16):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        # Latent continuous weights (initialized uniformly around 0)
        self.weight = nn.Parameter(torch.empty(out_channels, in_channels, 1, 1))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, x):
        # Binarize weights via STE
        w_bin = BinaryQuantizeSTE.apply(self.weight)
        return F.conv2d(x, w_bin, stride=1, padding=0)

    def get_binary_weights(self):
        """Return binary weights as numpy array of shape (in_channels, out_channels)."""
        w_bin = BinaryQuantizeSTE.apply(self.weight).detach().cpu()
        # Reshape (out_channels, in_channels, 1, 1) -> (in_channels, out_channels) for GEMM
        w_mat = w_bin.squeeze(-1).squeeze(-1).permute(1, 0).numpy().astype(int)
        return w_mat


class BinarizedLinear(nn.Module):
    """Linear layer with 1-bit binary weights {-1, +1} for classifier head."""

    def __init__(self, in_features=16, out_features=10):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, x):
        w_bin = BinaryQuantizeSTE.apply(self.weight)
        return F.linear(x, w_bin)

    def get_binary_weights(self):
        """Return binary weights as numpy array of shape (16, 16) with zero-padding if out < 16."""
        w_bin = BinaryQuantizeSTE.apply(self.weight).detach().cpu()
        w_mat = w_bin.permute(1, 0).numpy().astype(int)  # (in_features, out_features) = (16, out_features)
        
        # Pad to full 16x16 tile with +1 if needed
        full_mat = np.ones((16, 16), dtype=int)
        full_mat[:, :self.out_features] = w_mat
        return full_mat


class DepthwiseSmooth3x3(nn.Module):
    """Fixed non-parametric 3x3 depthwise box averaging filter (replicate padding)."""

    def __init__(self, channels=16):
        super().__init__()
        self.channels = channels
        # Fixed 3x3 kernel with weights 1/9
        kernel = torch.ones(channels, 1, 3, 3, dtype=torch.float32) / 9.0
        self.register_buffer('kernel', kernel)

    def forward(self, x):
        # Replicate padding 1 to match np.pad(..., mode='edge')
        x_pad = F.pad(x, (1, 1, 1, 1), mode='replicate')
        return F.conv2d(x_pad, self.kernel, groups=self.channels)


class MicroResNetQAT(nn.Module):
    """PyTorch Quantization-Aware Training model for MicroResNet16."""

    def __init__(self, num_classes=10, act_scale=64.0):
        super().__init__()
        self.num_classes = num_classes
        self.act_scale = act_scale

        # 1. Stem Conv: (16, 32, 32) -> (16, 32, 32)
        self.stem_conv = BinarizedConv1x1(16, 16)
        self.stem_bn = nn.BatchNorm2d(16)

        # 2. ResBlock 1: (16, 32, 32) -> (16, 16, 16)
        self.res1_conv1 = BinarizedConv1x1(16, 16)
        self.res1_bn1 = nn.BatchNorm2d(16)
        self.res1_smooth = DepthwiseSmooth3x3(16)
        self.res1_conv2 = BinarizedConv1x1(16, 16)
        self.res1_bn2 = nn.BatchNorm2d(16)
        self.res1_pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # 3. ResBlock 2: (16, 16, 16) -> (16, 8, 8)
        self.res2_conv1 = BinarizedConv1x1(16, 16)
        self.res2_bn1 = nn.BatchNorm2d(16)
        self.res2_conv2 = BinarizedConv1x1(16, 16)
        self.res2_bn2 = nn.BatchNorm2d(16)
        self.res2_pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # 4. Classifier Head: (16,) -> (num_classes,)
        self.classifier = BinarizedLinear(16, num_classes)
        self.classifier_bn = nn.BatchNorm1d(num_classes)

    def forward(self, x):
        """Forward pass with simulated 8-bit activation quantization.
        
        Args:
            x (torch.Tensor): Input batch of shape (B, 16, 32, 32) with values in [0.0, 255.0].
            
        Returns:
            torch.Tensor: Logits of shape (B, num_classes).
        """
        # Ensure input is quantized uint8 grid
        x = ActivationQuantizeSTE.apply(x)

        # Stem Conv + BN + Requantize ReLU
        x_stem = self.stem_conv(x)
        x_stem = self.stem_bn(x_stem)
        x_stem = ActivationQuantizeSTE.apply(F.relu(x_stem) * self.act_scale)

        # ResBlock 1:
        # Conv 1a
        x1 = self.res1_conv1(x_stem)
        x1 = self.res1_bn1(x1)
        x1 = ActivationQuantizeSTE.apply(F.relu(x1) * self.act_scale)

        # Spatial Depthwise
        x1_smooth = self.res1_smooth(x1)
        x1_smooth = ActivationQuantizeSTE.apply(x1_smooth)

        # Conv 1b
        x1b = self.res1_conv2(x1_smooth)
        x1b = self.res1_bn2(x1b)
        x1b_scaled = F.relu(x1b) * self.act_scale

        # Residual shortcut: (X + F(X)) / 2 + MaxPool 2x2
        res1_out = ActivationQuantizeSTE.apply((x_stem + x1b_scaled) * 0.5)
        res1_pool = self.res1_pool(res1_out)

        # ResBlock 2:
        # Conv 2a
        x2 = self.res2_conv1(res1_pool)
        x2 = self.res2_bn1(x2)
        x2 = ActivationQuantizeSTE.apply(F.relu(x2) * self.act_scale)

        # Conv 2b
        x2b = self.res2_conv2(x2)
        x2b = self.res2_bn2(x2b)
        x2b_scaled = F.relu(x2b) * self.act_scale

        # Residual shortcut: (X + F(X)) / 2 + MaxPool 2x2
        res2_out = ActivationQuantizeSTE.apply((res1_pool + x2b_scaled) * 0.5)
        res2_pool = self.res2_pool(res2_out)

        # Global Average Pooling: (B, 16, 8, 8) -> (B, 16)
        gap = res2_pool.mean(dim=(2, 3))
        gap = ActivationQuantizeSTE.apply(gap)

        # Classifier Head
        raw_logits = self.classifier(gap)
        logits = self.classifier_bn(raw_logits)

        return logits
