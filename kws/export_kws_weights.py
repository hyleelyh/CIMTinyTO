"""
Weight Exporter & BatchNorm Folding Engine for KWS-SCIM-16.
Folds continuous BatchNorm parameters and activation gain into integer multipliers and biases.

Silicon Realities:
- Bipolar weights W in {-1, +1} are exported as signed int8 values and packed 256-bit bitstreams.
- BatchNorm statistics (gamma, beta, mean, var) are algebraically folded into 16-element integer
  multiplier vectors M_c and bias vectors B_c.
- Hardware requantization on host Cortex-M33 or MMIO driver:
    Y_uint8 = clamp(((Y_raw * M_c + B_c) >> shift), 0, 255)
  Completely eliminates floating-point arithmetic from the inference datapath!
"""

import json
import torch
import numpy as np
from typing import Dict, Any, Tuple


def fold_batchnorm_and_gain(
    bn_weight: np.ndarray,      # gamma (16,)
    bn_bias: np.ndarray,        # beta (16,)
    bn_running_mean: np.ndarray,# mu (16,)
    bn_running_var: np.ndarray, # sigma^2 (16,)
    bn_eps: float = 1e-5,
    act_gain: float = 64.0,
    shift: int = 11,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fold continuous BatchNorm parameters (gamma, beta, mu, sigma^2) and activation gain S_act
    into integer fixed-point multipliers M_c and integer biases B_c.

    Equation:
        alpha_c = gamma_c / sqrt(sigma_c^2 + eps)
        delta_c = beta_c - mu_c * alpha_c
        M_c = round(S_act * alpha_c * 2^shift)
        B_c = round(S_act * delta_c * 2^shift)
    """
    scale = bn_weight / np.sqrt(bn_running_var + bn_eps)
    offset = bn_bias - bn_running_mean * scale

    mult = np.round(act_gain * scale * (2 ** shift)).astype(np.int32)
    bias = np.round(act_gain * offset * (2 ** shift)).astype(np.int32)

    return mult, bias


def export_kws_model_to_json(
    model: torch.nn.Module,
    filepath: str,
    class_names: list = None,
    shift: int = 11,
) -> Dict[str, Any]:
    """
    Extract, fold, and serialize KWS-SCIM-16 weights to JSON.
    """
    model.eval()
    if class_names is None:
        class_names = ['silence', 'unknown', 'yes', 'no']

    num_classes = len(class_names)

    # 1. Tile 0: Conv1
    with torch.no_grad():
        w0_raw = model.conv1.weight.squeeze(-1).cpu().numpy()  # (16, 16)
        w0_bipolar = np.where(w0_raw >= 0.0, 1, -1).astype(np.int8)

        gamma0 = model.conv1.bn.weight.cpu().numpy()
        beta0 = model.conv1.bn.bias.cpu().numpy()
        mean0 = model.conv1.bn.running_mean.cpu().numpy()
        var0 = model.conv1.bn.running_var.cpu().numpy()
        eps0 = model.conv1.bn.eps
        act_gain0 = float(model.conv1.act_gain)

        mult0, bias0 = fold_batchnorm_and_gain(gamma0, beta0, mean0, var0, eps0, act_gain0, shift)

    # 2. Tile 1: Conv2
    with torch.no_grad():
        w1_raw = model.conv2.weight.squeeze(-1).cpu().numpy()  # (16, 16)
        w1_bipolar = np.where(w1_raw >= 0.0, 1, -1).astype(np.int8)

        gamma1 = model.conv2.bn.weight.cpu().numpy()
        beta1 = model.conv2.bn.bias.cpu().numpy()
        mean1 = model.conv2.bn.running_mean.cpu().numpy()
        var1 = model.conv2.bn.running_var.cpu().numpy()
        eps1 = model.conv2.bn.eps
        act_gain1 = float(model.conv2.act_gain)

        mult1, bias1 = fold_batchnorm_and_gain(gamma1, beta1, mean1, var1, eps1, act_gain1, shift)

    # 3. Tile 2: Classifier Head
    with torch.no_grad():
        w_class_raw = model.classifier_weight.cpu().numpy()  # (16, 16)
        w_class_bipolar = np.where(w_class_raw >= 0.0, 1, -1).astype(np.int8)
        active_w_class = w_class_bipolar[:num_classes, :]    # (num_classes, 16)

        b_class = model.classifier_bias.cpu().numpy()
        int_b_class = np.round(b_class).astype(np.int32)

    export_dict = {
        'model_name': 'KWS_SCIM_16',
        'target_macro': 'CIMTinyTO_Sky130_16x16',
        'num_classes': num_classes,
        'class_names': class_names,
        'shift': shift,
        'tile0_weights': w0_bipolar.tolist(),
        'tile0_mult': mult0.tolist(),
        'tile0_bias': bias0.tolist(),
        'tile0_shift': shift,
        'tile1_weights': w1_bipolar.tolist(),
        'tile1_mult': mult1.tolist(),
        'tile1_bias': bias1.tolist(),
        'tile1_shift': shift,
        'classifier_weights': active_w_class.tolist(),
        'classifier_biases': int_b_class.tolist(),
    }

    with open(filepath, 'w') as f:
        json.dump(export_dict, f, indent=2)

    return export_dict
