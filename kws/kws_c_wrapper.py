"""
Python ctypes wrapper for libkws_pipeline.so.
Bridges Python NumPy audio buffers to high-performance C99 audio processing
and SCIM coprocessor execution.
"""

import os
import ctypes
import json
import numpy as np
from typing import Tuple, Dict, Any, List


class KWSConfigStruct(ctypes.Structure):
    _fields_ = [
        ('num_classes', ctypes.c_int),
        ('class_names', (ctypes.c_char * 16) * 16),
        ('tile0_weights', (ctypes.c_int8 * 16) * 16),
        ('tile0_mult', ctypes.c_int32 * 16),
        ('tile0_bias', ctypes.c_int32 * 16),
        ('tile0_shift', ctypes.c_int),

        ('tile1_weights', (ctypes.c_int8 * 16) * 16),
        ('tile1_mult', ctypes.c_int32 * 16),
        ('tile1_bias', ctypes.c_int32 * 16),
        ('tile1_shift', ctypes.c_int),

        ('classifier_weights', (ctypes.c_int8 * 16) * 16),
        ('classifier_biases', ctypes.c_int32 * 16),
    ]


class KWSCPipeline:
    def __init__(self, weights_json_path: str, so_path: str = None):
        if so_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            so_path = os.path.join(base_dir, 'firmware', 'stm32_kws', 'libkws_pipeline.so')

        if not os.path.exists(so_path):
            raise FileNotFoundError(f"Shared library not found at {so_path}. Run 'make -C firmware/stm32_kws host'.")

        self.lib = ctypes.CDLL(so_path)

        # Function signatures
        self.lib.kws_pipeline_init.argtypes = [ctypes.POINTER(KWSConfigStruct)]
        self.lib.kws_pipeline_init.restype = None

        self.lib.kws_pipeline_run.argtypes = [
            ctypes.POINTER(KWSConfigStruct),
            ctypes.POINTER(ctypes.c_int16),
            ctypes.POINTER(ctypes.c_int32),
        ]
        self.lib.kws_pipeline_run.restype = ctypes.c_int

        self.lib.kws_pipeline_get_class_name.argtypes = [
            ctypes.POINTER(KWSConfigStruct),
            ctypes.c_int,
        ]
        self.lib.kws_pipeline_get_class_name.restype = ctypes.c_char_p

        self.lib.kws_mfcc_extract_spectrogram.argtypes = [
            ctypes.POINTER(ctypes.c_int16),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint8),
        ]
        self.lib.kws_mfcc_extract_spectrogram.restype = None

        # Load configuration from JSON
        self.load_config(weights_json_path)

    def load_config(self, weights_json_path: str):
        with open(weights_json_path, 'r') as f:
            data = json.load(f)

        self.class_names = data['class_names']
        self.num_classes = len(self.class_names)

        cfg = KWSConfigStruct()
        cfg.num_classes = self.num_classes

        # Class names
        for i, name in enumerate(self.class_names):
            cfg.class_names[i].value = name.encode('utf-8')[:15]

        # Tile 0
        w0 = np.array(data['tile0_weights'], dtype=np.int8)
        for r in range(16):
            for c in range(16):
                cfg.tile0_weights[r][c] = int(w0[r, c])

        m0 = np.array(data['tile0_mult'], dtype=np.int32)
        b0 = np.array(data['tile0_bias'], dtype=np.int32)
        for c in range(16):
            cfg.tile0_mult[c] = int(m0[c])
            cfg.tile0_bias[c] = int(b0[c])
        cfg.tile0_shift = int(data.get('tile0_shift', 11))

        # Tile 1
        w1 = np.array(data['tile1_weights'], dtype=np.int8)
        for r in range(16):
            for c in range(16):
                cfg.tile1_weights[r][c] = int(w1[r, c])

        m1 = np.array(data['tile1_mult'], dtype=np.int32)
        b1 = np.array(data['tile1_bias'], dtype=np.int32)
        for c in range(16):
            cfg.tile1_mult[c] = int(m1[c])
            cfg.tile1_bias[c] = int(b1[c])
        cfg.tile1_shift = int(data.get('tile1_shift', 11))

        # Classifier
        wc = np.array(data['classifier_weights'], dtype=np.int8)
        bc = np.array(data['classifier_biases'], dtype=np.int32)
        for k in range(self.num_classes):
            for r in range(16):
                cfg.classifier_weights[k][r] = int(wc[k, r])
            cfg.classifier_biases[k] = int(bc[k])

        self.cfg = cfg
        self.lib.kws_pipeline_init(ctypes.byref(self.cfg))

    def extract_spectrogram(self, pcm_audio: np.ndarray) -> np.ndarray:
        """
        Extract 16x32 uint8 Mel-spectrogram using C implementation.
        """
        pcm_16 = np.ascontiguousarray(pcm_audio, dtype=np.int16)
        spec_out = np.zeros((16, 32), dtype=np.uint8)

        pcm_ptr = pcm_16.ctypes.data_as(ctypes.POINTER(ctypes.c_int16))
        spec_ptr = spec_out.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))

        self.lib.kws_mfcc_extract_spectrogram(pcm_ptr, len(pcm_16), spec_ptr)
        return spec_out

    def infer(self, pcm_audio: np.ndarray) -> Tuple[int, str, np.ndarray]:
        """
        Execute complete C pipeline inference on audio buffer.
        Returns:
            (class_idx, class_name, logits_array)
        """
        pcm_16 = np.ascontiguousarray(pcm_audio, dtype=np.int16)
        logits = np.zeros(16, dtype=np.int32)

        pcm_ptr = pcm_16.ctypes.data_as(ctypes.POINTER(ctypes.c_int16))
        logits_ptr = logits.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))

        pred_idx = self.lib.kws_pipeline_run(ctypes.byref(self.cfg), pcm_ptr, logits_ptr)
        name_bytes = self.lib.kws_pipeline_get_class_name(ctypes.byref(self.cfg), pred_idx)
        class_name = name_bytes.decode('utf-8') if name_bytes else "unknown"

        return pred_idx, class_name, logits[:self.num_classes]
