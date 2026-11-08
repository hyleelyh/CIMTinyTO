"""
Quantization-Aware Training (QAT) Pipeline for KWS-SCIM-16.
Trains the acoustic keyword spotting network with Straight-Through Estimators (STE)
and latent weight clamping discipline.

Silicon Realities:
- Latent weights clamped to [-1.0, +1.0] after every gradient update prevents weight
  gradient saturation and maintains maximum flipping agility across binary states.
- Requantization gain S_act = 64.0 ensures intermediate activations populate the full
  8-bit dynamic range [0, 255] matching the physical LFSR SNG comparator.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Tuple, List

from kws.kws_model import KWS_SCIM_16, FixedPointKWSModel
from kws.kws_audio_frontend import generate_synthetic_audio, extract_mel_filterbank, quantize_spectrogram_to_uint8
from kws.export_kws_weights import export_kws_model_to_json


def create_synthetic_kws_dataset(
    class_names: List[str],
    samples_per_class: int = 60,
    seed: int = 42,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Generate synthetic audio dataset and extract uint8 Mel-spectrograms.
    Returns:
        (spectrograms_tensor, labels_tensor) where spec shape is (N, 16, 32).
    """
    rng = np.random.RandomState(seed)
    specs = []
    labels = []

    for class_idx, kw in enumerate(class_names):
        for i in range(samples_per_class):
            # Base audio
            audio = generate_synthetic_audio(kw)

            # Acoustic data augmentations (temporal jitter, noise injection, volume variation)
            jitter = rng.randint(-1600, 1600)  # +/- 100 ms jitter
            if jitter > 0:
                audio = np.pad(audio, (jitter, 0))[:len(audio)]
            elif jitter < 0:
                audio = np.pad(audio, (0, -jitter))[-jitter:]

            # Additive acoustic noise
            noise_amp = rng.uniform(0.002, 0.02)
            audio = audio + rng.normal(0.0, noise_amp, size=len(audio))

            # Amplitude scaling
            scale = rng.uniform(0.6, 1.2)
            audio = audio * scale

            # Extract 16-channel Mel filterbank & quantize to uint8 [0, 255]
            spec_float = extract_mel_filterbank(audio)
            spec_uint8 = quantize_spectrogram_to_uint8(spec_float)

            specs.append(spec_uint8)
            labels.append(class_idx)

    # Convert to tensors
    specs_tensor = torch.tensor(np.array(specs), dtype=torch.float32)  # (N, 16, 32)
    labels_tensor = torch.tensor(labels, dtype=torch.long)             # (N,)

    # Shuffle
    perm = torch.randperm(len(labels_tensor))
    return specs_tensor[perm], labels_tensor[perm]


def train_kws_qat(
    class_names: List[str] = None,
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 0.01,
    act_gain: float = 64.0,
    export_path: str = None,
) -> Tuple[KWS_SCIM_16, FixedPointKWSModel, float]:
    """
    Execute Quantization-Aware Training with latent weight clamping.
    """
    if class_names is None:
        class_names = ['silence', 'unknown', 'yes', 'no']

    num_classes = len(class_names)
    print(f"\n==================================================================")
    print(f"Starting QAT for KWS-SCIM-16 ({num_classes} Classes: {class_names})")
    print(f"==================================================================")

    # 1. Generate Training & Validation Data
    x_train, y_train = create_synthetic_kws_dataset(class_names, samples_per_class=80, seed=101)
    x_val, y_val = create_synthetic_kws_dataset(class_names, samples_per_class=20, seed=202)
    print(f"Training samples: {len(x_train)}, Validation samples: {len(x_val)}")

    # 2. Instantiate Model & Optimizer
    model = KWS_SCIM_16(num_classes=num_classes, act_gain=act_gain)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    # 3. Training Loop with Latent Weight Clamping and Best Checkpoint
    model.train()
    dataset_size = len(x_train)
    best_val_acc = -1.0
    best_state_dict = None

    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        correct = 0

        # Mini-batch shuffle
        perm = torch.randperm(dataset_size)
        for i in range(0, dataset_size, batch_size):
            indices = perm[i : i + batch_size]
            batch_x, batch_y = x_train[indices], y_train[indices]

            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            # Silicon Clamping Discipline:
            # Clamp latent continuous weights to [-1.0, +1.0] after each optimizer step.
            with torch.no_grad():
                model.conv1.weight.clamp_(-1.0, 1.0)
                model.conv2.weight.clamp_(-1.0, 1.0)
                model.classifier_weight.clamp_(-1.0, 1.0)

            running_loss += loss.item() * len(batch_y)
            preds = torch.argmax(logits, dim=-1)
            correct += (preds == batch_y).sum().item()

        train_acc = 100.0 * correct / dataset_size

        # Evaluate validation set every epoch to track best weights
        model.eval()
        with torch.no_grad():
            val_logits = model(x_val)
            val_preds = torch.argmax(val_logits, dim=-1)
            val_acc = 100.0 * (val_preds == y_val).sum().item() / len(y_val)
        model.train()

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state_dict = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch {epoch:2d}/{epochs} | Loss: {running_loss/dataset_size:.4f} | Train Acc: {train_acc:5.1f}% | Val Acc: {val_acc:5.1f}% (Best: {best_val_acc:5.1f}%)")

    # Restore best checkpoint
    if best_state_dict is not None:
        model.load_state_dict(best_state_dict)

    # 4. Final Evaluation with best checkpoint
    model.eval()
    with torch.no_grad():
        val_logits = model(x_val)
        val_preds = torch.argmax(val_logits, dim=-1)
        final_val_acc = 100.0 * (val_preds == y_val).sum().item() / len(y_val)

    print(f"\nFinal Best Validation Accuracy: {final_val_acc:.2f}%")

    # 5. Export to Fixed-Point JSON
    if export_path is None:
        export_path = f"kws/kws_weights_{num_classes}class.json"

    export_dict = export_kws_model_to_json(model, export_path, class_names=class_names)
    print(f"Exported folded integer weights to {export_path}")

    # 6. Verify Parity against Fixed-Point Hardware Reference
    fixed_model = FixedPointKWSModel(export_dict)
    parity_matches = 0
    total_val = len(x_val)

    for i in range(total_val):
        input_spec = x_val[i].numpy().astype(np.uint8)
        _, fixed_pred, _ = fixed_model.forward(input_spec)
        pt_pred = int(val_preds[i].item())
        if fixed_pred == pt_pred:
            parity_matches += 1

    parity_rate = 100.0 * parity_matches / total_val
    print(f"PyTorch QAT vs. Fixed-Point Hardware Reference Parity: {parity_rate:.1f}% ({parity_matches}/{total_val} matches)")

    return model, fixed_model, final_val_acc


if __name__ == '__main__':
    # Train 4-class profile with 35 epochs
    train_kws_qat(class_names=['silence', 'unknown', 'yes', 'no'], epochs=35, export_path="kws/kws_weights_4class.json")

    # Train 6-class profile with 35 epochs
    train_kws_qat(class_names=['silence', 'unknown', 'yes', 'no', 'stop', 'go'], epochs=35, export_path="kws/kws_weights_6class.json")
