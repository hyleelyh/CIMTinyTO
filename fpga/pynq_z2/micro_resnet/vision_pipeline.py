# ============================================================================
# Module: vision_pipeline.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Host Emulation (Pillar 6.1)
# Standard: Python 3.10+ / PIL & NumPy Edge Vision Pipeline
# ============================================================================
# Pedagogical & Silicon Rationale:
#
# 1. Edge Camera Ingestion & Resizing:
#    - In physical edge robotics/vision, incoming camera streams (1080p / 720p)
#      are cropped and downsampled to 32x32 patches for real-time classification.
#    - Preprocessing normalizes dynamic range to [0, 255] unipolar uint8, perfectly
#      matching the 8-bit DAC/comparators in our on-chip SNG bank.
#
# 2. Live HUD Annotation:
#    - Renders real-time telemetry (top-1 class, confidence, inference latency, FPS)
#      directly onto video frames for HDMI display (PMOD/HDMI on PYNQ / RPi 5).
# ============================================================================

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .micro_resnet_model import MicroResNet16
from .scim_tier1_mmio import SCIMTier1Engine
from .scim_tier2_wrapper import SCIMTier2Engine
from .scim_tier3_dma import SCIMTier3Engine


class EdgeVisionPipeline:
    """End-to-End Real-Time Edge Vision Pipeline with Multi-Tier Acceleration."""

    def __init__(self, force_emulation=True, seed=42):
        self.seed = seed
        self.force_emulation = force_emulation
        self.tier1_engine = SCIMTier1Engine(force_emulation=force_emulation, seed=seed)
        self.tier2_engine = SCIMTier2Engine(force_sim=force_emulation, seed=seed)
        self.tier3_engine = SCIMTier3Engine(seed=seed)

    @staticmethod
    def load_image(image_input):
        """Load and resize image to 32x32 RGB uint8 array.
        
        Args:
            image_input: File path (str) or PIL.Image or np.ndarray.
            
        Returns:
            np.ndarray: (32, 32, 3) uint8 array.
        """
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            img = image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            if image_input.dtype != np.uint8:
                image_input = np.clip(image_input, 0, 255).astype(np.uint8)
            img = Image.fromarray(image_input).convert("RGB")
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        img_32x32 = img.resize((32, 32), Image.Resampling.BILINEAR)
        return np.array(img_32x32, dtype=np.uint8)

    @staticmethod
    def generate_synthetic_pattern(pattern_type="checkerboard"):
        """Generate a deterministic synthetic visual pattern for testing."""
        img = np.zeros((32, 32, 3), dtype=np.uint8)

        if pattern_type == "checkerboard":
            # Alternating 4x4 blocks
            for y in range(32):
                for x in range(32):
                    if ((x // 4) + (y // 4)) % 2 == 0:
                        img[y, x] = [220, 220, 220]
                    else:
                        img[y, x] = [30, 30, 30]

        elif pattern_type == "horizontal_stripes":
            for y in range(32):
                color = [240, 50, 50] if (y // 4) % 2 == 0 else [50, 50, 240]
                img[y, :] = color

        elif pattern_type == "circle":
            # Concentric circular target
            for y in range(32):
                for x in range(32):
                    r = np.sqrt((x - 15.5)**2 + (y - 15.5)**2)
                    if r < 8.0:
                        img[y, x] = [50, 220, 50]
                    elif r < 14.0:
                        img[y, x] = [220, 180, 50]
                    else:
                        img[y, x] = [40, 40, 40]

        elif pattern_type == "gradient":
            for y in range(32):
                for x in range(32):
                    img[y, x] = [int(x * 8), int(y * 8), int((x + y) * 4)]

        return img

    def run_inference(self, image_input, tier=1):
        """Run classification using the requested transport tier.
        
        Args:
            image_input: Image path, PIL Image, or numpy array.
            tier (int): 1 (Pure Python MMIO), 2 (Compiled C MMIO), or 3 (Line-Rate DMA).
            
        Returns:
            dict: Classification metrics, logits, probabilities, and timing stats.
        """
        img_arr = self.load_image(image_input)

        if tier == 1:
            res = self.tier1_engine.infer(img_arr)
        elif tier == 2:
            res = self.tier2_engine.infer(img_arr)
        elif tier == 3:
            res = self.tier3_engine.infer(img_arr)
        else:
            raise ValueError(f"Invalid tier {tier}. Supported tiers: 1, 2, 3.")

        # Compute Softmax probabilities
        logits = res["logits"].astype(np.float64)
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        res["probabilities"] = probs

        # Top 3 classes
        top3_indices = np.argsort(probs)[::-1][:3]
        res["top3"] = [
            (MicroResNet16.CLASSES[idx], float(probs[idx]))
            for idx in top3_indices
        ]

        res["input_image_32x32"] = img_arr
        return res

    def render_hud_overlay(self, inference_result, scale=8):
        """Render an informative HUD overlay on top of the upscaled image.
        
        Args:
            inference_result (dict): Output from run_inference().
            scale (int): Upscale factor for display (default 8 -> 256x256 image).
            
        Returns:
            PIL.Image: Annotated HUD image.
        """
        img_arr = inference_result["input_image_32x32"]
        orig_img = Image.fromarray(img_arr).resize((32 * scale, 32 * scale), Image.Resampling.NEAREST)

        # Create image with HUD panel
        hud_height = 90
        total_w = 32 * scale
        total_h = (32 * scale) + hud_height
        canvas = Image.new("RGB", (total_w, total_h), color=(20, 24, 30))
        canvas.paste(orig_img, (0, 0))

        draw = ImageDraw.Draw(canvas)

        # Draw border
        draw.rectangle([(0, 0), (total_w - 1, 32 * scale - 1)], outline=(0, 200, 255), width=2)

        # Draw HUD text
        pred_class = inference_result["pred_class"].upper()
        top_prob = inference_result["probabilities"][inference_result["pred_idx"]] * 100.0
        tier_name = inference_result["tier"]
        fps = inference_result["fps"]
        tile_us = inference_result["tile_latency_us"]
        time_ms = inference_result["total_time_sec"] * 1000.0

        # Header: Class and Confidence
        draw.text((10, 32 * scale + 8), f"CLASS: {pred_class} ({top_prob:.1f}%)", fill=(0, 255, 120))
        # Line 2: Tier and Latency
        draw.text((10, 32 * scale + 28), f"TIER:  {tier_name}", fill=(200, 220, 255))
        draw.text((10, 32 * scale + 48), f"SPEED: {fps:5.1f} FPS | Tile: {tile_us:5.1f} us | Lat: {time_ms:.1f} ms", fill=(255, 215, 0))
        # Line 3: Hardware info
        draw.text((10, 32 * scale + 68), f"HW:    16x16 SCIM @ 50 MHz (256 Stationary DFFs)", fill=(160, 180, 200))

        return canvas

    def stream_live_camera(self, num_frames=20, tier=2, device_id=0, force_synthetic=False, on_frame=None):
        """Stream live camera frames, execute real-time inference, and render HUD telemetry.
        
        Args:
            num_frames (int): Number of video frames to process.
            tier (int): Acceleration tier (1, 2, or 3).
            device_id (int): V4L2 video device index (default 0 for /dev/video0).
            force_synthetic (bool): Force animated synthetic video stream even if camera exists.
            on_frame (callable, optional): Callback func(frame_idx, inference_result, hud_image).
            
        Returns:
            list: List of (inference_result, hud_image) tuples.
        """
        cam = LiveCameraCapture(device_id=device_id, force_synthetic=force_synthetic)
        results = []
        try:
            for f in range(num_frames):
                ret, frame = cam.read_frame()
                if not ret:
                    break
                res = self.run_inference(frame, tier=tier)
                hud_img = self.render_hud_overlay(res, scale=8)
                if on_frame:
                    on_frame(f, res, hud_img)
                results.append((res, hud_img))
        finally:
            cam.release()
        return results


class LiveCameraCapture:
    """Universal Camera Interface: Supports physical USB Webcams, CSI Cameras, and Synthetic Video."""

    def __init__(self, device_id=0, force_synthetic=False):
        self.device_id = device_id
        self.cap = None
        self.backend = "synthetic"
        self.frame_idx = 0

        if not force_synthetic:
            # Check for OpenCV
            try:
                import cv2
                cap = cv2.VideoCapture(device_id)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.cap = cap
                        self.backend = "opencv"
                        print(f"[LiveCamera] Connected to physical video device /dev/video{device_id} via OpenCV.")
                    else:
                        cap.release()
            except Exception:
                pass

        if self.backend == "synthetic":
            print("[LiveCamera] No physical camera attached (or OpenCV absent). Using Animated Synthetic Video Stream.")

    def read_frame(self):
        """Capture or generate a single 32x32 RGB frame.
        
        Returns:
            tuple: (success: bool, frame: np.ndarray of shape (32, 32, 3) uint8)
        """
        if self.backend == "opencv" and self.cap is not None:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # BGR to RGB
                rgb = frame[:, :, ::-1]
                h, w, _ = rgb.shape
                min_dim = min(h, w)
                top = (h - min_dim) // 2
                left = (w - min_dim) // 2
                cropped = rgb[top:top + min_dim, left:left + min_dim]
                resized = Image.fromarray(cropped).resize((32, 32), Image.Resampling.BILINEAR)
                return True, np.array(resized, dtype=np.uint8)

        # Synthetic animated video stream (moving target across visual field)
        self.frame_idx += 1
        t = self.frame_idx * 0.15
        img = np.zeros((32, 32, 3), dtype=np.uint8)

        cx = 15.5 + 8.0 * np.sin(t)
        cy = 15.5 + 8.0 * np.cos(t * 0.7)

        for y in range(32):
            for x in range(32):
                dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                if dist < 6.0:
                    img[y, x] = [50, 230, 60]  # Foreground target
                elif dist < 12.0:
                    img[y, x] = [230, 160, 40]  # Outer boundary
                else:
                    bg = int(25 + 15 * np.sin(x * 0.2 + t))
                    img[y, x] = [bg, bg, bg + 25]  # Dynamic background

        return True, img

    def release(self):
        """Release underlying camera hardware handles."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
