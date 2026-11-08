# ============================================================================
# Module: scim_tier3_c_accel.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) & Host Emulation (Pillar 6.1)
# Standard: Python 3.10+ / ctypes C99 Shared Library Wrapper
# ============================================================================
# Pedagogical & Silicon Rationale:
#
# 1. Zero-Copy DMA CMA Pointer Bridging:
#    - PYNQ contiguous memory allocation (pynq.allocate) produces contiguous
#      physical memory mapped into user virtual space.
#    - By passing the virtual pointer directly to libscim_tier3_accel.so via
#      ctypes, the ARM CPU preprocesses and post-processes data in-place.
#    - Zero memory copies are performed between C and Python.
#
# 2. Transparent Safe Fallback:
#    - If libscim_tier3_accel.so is missing, incompatible, or fails to load,
#      is_available is set to False and the engine seamlessly executes the
#      proven NumPy reference pipeline.
# ============================================================================

import os
import ctypes
import numpy as np

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_SO_PATH = os.path.join(_CURRENT_DIR, "scim_tier3_c", "libscim_tier3_accel.so")


class SCIMTier3CAccelerator:
    """Python ctypes wrapper for libscim_tier3_accel.so SIMD/NEON library."""

    def __init__(self, so_path=None):
        self.so_path = so_path or _DEFAULT_SO_PATH
        self.c_lib = None
        self.is_available = False
        self._load_library()

    def _load_library(self):
        """Attempt to load the compiled C shared library and configure prototypes."""
        if not os.path.exists(self.so_path):
            return

        try:
            self.c_lib = ctypes.CDLL(self.so_path)

            # 1. c_preprocess_and_pack_input
            self.c_lib.c_preprocess_and_pack_input.argtypes = [
                ctypes.c_void_p,  # const uint8_t *rgb_in
                ctypes.c_void_p,  # uint32_t *dma_in_buf
                ctypes.c_int,     # int H
                ctypes.c_int      # int W
            ]
            self.c_lib.c_preprocess_and_pack_input.restype = ctypes.c_int

            # 2. c_requantize_relu_16b_to_8b
            self.c_lib.c_requantize_relu_16b_to_8b.argtypes = [
                ctypes.c_void_p,  # const int16_t *raw_acc
                ctypes.c_void_p,  # uint8_t *out_acts
                ctypes.c_void_p,  # const int32_t *bias
                ctypes.c_void_p,  # const int32_t *mult
                ctypes.c_int,     # int shift
                ctypes.c_int      # int num_tiles
            ]
            self.c_lib.c_requantize_relu_16b_to_8b.restype = None

            # 3. c_depthwise_smooth_3x3
            self.c_lib.c_depthwise_smooth_3x3.argtypes = [
                ctypes.c_void_p,  # const uint8_t *in_acts
                ctypes.c_void_p,  # uint8_t *out_acts
                ctypes.c_int,     # int H
                ctypes.c_int      # int W
            ]
            self.c_lib.c_depthwise_smooth_3x3.restype = None

            # 4. c_fused_residual_add_and_maxpool2x2
            self.c_lib.c_fused_residual_add_and_maxpool2x2.argtypes = [
                ctypes.c_void_p,  # const uint8_t *res_shortcut
                ctypes.c_void_p,  # const uint8_t *res_conv_out
                ctypes.c_void_p,  # uint8_t *pooled_out
                ctypes.c_int,     # int H
                ctypes.c_int      # int W
            ]
            self.c_lib.c_fused_residual_add_and_maxpool2x2.restype = None

            # 5. c_pack_dma_input
            self.c_lib.c_pack_dma_input.argtypes = [
                ctypes.c_void_p,  # const uint8_t *in_acts
                ctypes.c_void_p,  # uint32_t *dma_in_buf
                ctypes.c_int      # int num_tiles
            ]
            self.c_lib.c_pack_dma_input.restype = ctypes.c_int

            # 6. c_gap_and_classify
            self.c_lib.c_gap_and_classify.argtypes = [
                ctypes.c_void_p,  # const uint8_t *in_acts
                ctypes.c_void_p,  # const int32_t *weights
                ctypes.c_void_p,  # const int32_t *biases
                ctypes.c_void_p,  # int32_t *out_logits
                ctypes.c_int      # int num_classes
            ]
            self.c_lib.c_gap_and_classify.restype = ctypes.c_int

            self.is_available = True
        except Exception as e:
            print(f"[SCIM C Accel] Warning: Failed to initialize C accelerator library ({e})")
            self.c_lib = None
            self.is_available = False

    def preprocess_and_pack_input(self, rgb_in, dma_in_buf):
        """Preprocess 32x32 RGB and pack directly into dma_in_buf."""
        assert rgb_in.shape == (32, 32, 3), f"Expected (32, 32, 3), got {rgb_in.shape}"
        assert rgb_in.dtype == np.uint8, f"Expected uint8, got {rgb_in.dtype}"
        rgb_c = np.ascontiguousarray(rgb_in, dtype=np.uint8)

        words_written = self.c_lib.c_preprocess_and_pack_input(
            rgb_c.ctypes.data_as(ctypes.c_void_p),
            dma_in_buf.ctypes.data_as(ctypes.c_void_p),
            32,
            32
        )
        return words_written

    def requantize_relu(self, raw_acc, bias, scale_dict, out_acts=None):
        """Requantize int16 raw accumulators to uint8 ReLU activations."""
        mult = np.ascontiguousarray(scale_dict["mult"], dtype=np.int32)
        shift = int(scale_dict["shift"])
        bias_c = np.ascontiguousarray(bias, dtype=np.int32)

        raw_c = np.ascontiguousarray(raw_acc, dtype=np.int16)
        num_tiles = raw_c.size // 16

        if out_acts is None:
            out_acts = np.empty(raw_acc.shape, dtype=np.uint8)
        else:
            assert out_acts.dtype == np.uint8

        self.c_lib.c_requantize_relu_16b_to_8b(
            raw_c.ctypes.data_as(ctypes.c_void_p),
            out_acts.ctypes.data_as(ctypes.c_void_p),
            bias_c.ctypes.data_as(ctypes.c_void_p),
            mult.ctypes.data_as(ctypes.c_void_p),
            shift,
            num_tiles
        )
        return out_acts

    def depthwise_smooth_3x3(self, in_acts, out_acts=None):
        """Depthwise 3x3 box smoothing with replicated edge padding (NHWC)."""
        H, W, C = in_acts.shape
        assert C == 16, f"Expected 16 channels, got {C}"
        in_c = np.ascontiguousarray(in_acts, dtype=np.uint8)

        if out_acts is None:
            out_acts = np.empty((H, W, 16), dtype=np.uint8)
        else:
            assert out_acts.dtype == np.uint8

        self.c_lib.c_depthwise_smooth_3x3(
            in_c.ctypes.data_as(ctypes.c_void_p),
            out_acts.ctypes.data_as(ctypes.c_void_p),
            H,
            W
        )
        return out_acts

    def fused_residual_add_and_maxpool2x2(self, res_shortcut, res_conv_out, pooled_out=None):
        """Fused residual shortcut addition and 2x2 max-pooling (NHWC)."""
        H, W, C = res_shortcut.shape
        assert C == 16 and res_conv_out.shape == (H, W, 16), "Shape mismatch"

        s_c = np.ascontiguousarray(res_shortcut, dtype=np.uint8)
        c_c = np.ascontiguousarray(res_conv_out, dtype=np.uint8)

        out_H, out_W = H // 2, W // 2
        if pooled_out is None:
            pooled_out = np.empty((out_H, out_W, 16), dtype=np.uint8)
        else:
            assert pooled_out.dtype == np.uint8

        self.c_lib.c_fused_residual_add_and_maxpool2x2(
            s_c.ctypes.data_as(ctypes.c_void_p),
            c_c.ctypes.data_as(ctypes.c_void_p),
            pooled_out.ctypes.data_as(ctypes.c_void_p),
            H,
            W
        )
        return pooled_out

    def pack_dma_input(self, in_acts, dma_in_buf):
        """Pack arbitrary NHWC uint8 activations into dma_in_buf."""
        in_c = np.ascontiguousarray(in_acts, dtype=np.uint8)
        num_tiles = in_c.size // 16
        words_written = self.c_lib.c_pack_dma_input(
            in_c.ctypes.data_as(ctypes.c_void_p),
            dma_in_buf.ctypes.data_as(ctypes.c_void_p),
            num_tiles
        )
        return words_written

    def gap_and_classify(self, in_acts, weights, biases, num_classes):
        """Global Average Pooling and dense linear classification."""
        in_c = np.ascontiguousarray(in_acts, dtype=np.uint8)
        w_c = np.ascontiguousarray(weights, dtype=np.int32)
        b_c = np.ascontiguousarray(biases, dtype=np.int32)
        logits = np.empty((num_classes,), dtype=np.int32)

        pred_idx = self.c_lib.c_gap_and_classify(
            in_c.ctypes.data_as(ctypes.c_void_p),
            w_c.ctypes.data_as(ctypes.c_void_p),
            b_c.ctypes.data_as(ctypes.c_void_p),
            logits.ctypes.data_as(ctypes.c_void_p),
            num_classes
        )
        return pred_idx, logits
