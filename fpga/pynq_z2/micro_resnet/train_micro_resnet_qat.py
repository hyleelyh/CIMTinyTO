# ============================================================================
# Module: train_micro_resnet_qat.py
# Project: CIMTinyTO (Stochastic & Digital Compute-in-Memory Accelerator)
# Target: AMD Xilinx Zynq-7020 (PYNQ-Z2) FPGA & Pre-Silicon Emulation (Pillar 6.1)
# Standard: Python 3.10+ / PyTorch Quantization-Aware Training Pipeline
# ============================================================================

import os
import sys
import argparse
import time
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

# Ensure repository root is on sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fpga.pynq_z2.micro_resnet.micro_resnet_model import MicroResNet16
from fpga.pynq_z2.micro_resnet.micro_resnet_qat import MicroResNetQAT


class HardwareInputTransform:
    """Preprocesses images into 16-channel 32x32 uint8 tensors matching CIMTinyTO hardware."""

    def __init__(self, is_grayscale=False):
        self.is_grayscale = is_grayscale

    def __call__(self, pil_img):
        arr = np.array(pil_img)
        if self.is_grayscale:
            # 28x28 grayscale -> pad to 32x32 with 2 pixels on each border
            arr = np.pad(arr, ((2, 2), (2, 2)), mode='constant', constant_values=0)
            # Replicate to 3 channels for uniform preprocessing
            arr = np.stack([arr, arr, arr], axis=-1)
        elif arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=-1)

        # MicroResNet16.preprocess_image generates (16, 32, 32) uint8
        feat = MicroResNet16.preprocess_image(arr)
        # Convert to float32 tensor in [0.0, 255.0]
        return torch.from_numpy(feat).float()


def get_dataset(dataset_name, data_dir="./data"):
    """Load and prepare selected dataset with hardware preprocessing and class filtering."""
    os.makedirs(data_dir, exist_ok=True)

    if dataset_name == "cifar10_4class":
        # Target classes: Vehicles vs Animals [airplane=0, automobile=1, cat=3, dog=5]
        target_classes = [0, 1, 3, 5]
        class_names = ["airplane", "automobile", "cat", "dog"]
        transform = HardwareInputTransform(is_grayscale=False)

        train_raw = datasets.CIFAR10(root=data_dir, train=True, download=True, transform=transform)
        test_raw = datasets.CIFAR10(root=data_dir, train=False, download=True, transform=transform)

        # Filter indices
        train_indices = [i for i, (_, label) in enumerate(train_raw) if label in target_classes]
        test_indices = [i for i, (_, label) in enumerate(test_raw) if label in target_classes]

        # Remap labels to 0..3
        label_map = {orig: new for new, orig in enumerate(target_classes)}

        class RemappedSubset(torch.utils.data.Dataset):
            def __init__(self, subset, mapping):
                self.subset = subset
                self.mapping = mapping
            def __len__(self):
                return len(self.subset)
            def __getitem__(self, idx):
                x, y = self.subset[idx]
                return x, self.mapping[y]

        train_set = RemappedSubset(Subset(train_raw, train_indices), label_map)
        test_set = RemappedSubset(Subset(test_raw, test_indices), label_map)
        num_classes = 4

    elif dataset_name == "cifar10_10class":
        class_names = MicroResNet16.CLASSES
        transform = HardwareInputTransform(is_grayscale=False)
        train_set = datasets.CIFAR10(root=data_dir, train=True, download=True, transform=transform)
        test_set = datasets.CIFAR10(root=data_dir, train=False, download=True, transform=transform)
        num_classes = 10

    elif dataset_name == "fashion_mnist":
        class_names = [
            "T-shirt/top", "Trouser", "Pullover", "Dress", "Coat",
            "Sandal", "Shirt", "Sneaker", "Bag", "Ankle boot"
        ]
        transform = HardwareInputTransform(is_grayscale=True)
        train_set = datasets.FashionMNIST(root=data_dir, train=True, download=True, transform=transform)
        test_set = datasets.FashionMNIST(root=data_dir, train=False, download=True, transform=transform)
        num_classes = 10

    else:
        raise ValueError(f"Unknown dataset: {dataset_name}. Choose from: cifar10_4class, cifar10_10class, fashion_mnist")

    return train_set, test_set, num_classes, class_names


def train_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for inputs, targets in dataloader:
        inputs, targets = inputs.to(device), targets.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        # Critical BNN Principle: Clip latent weights to [-1.0, +1.0] to keep them responsive
        with torch.no_grad():
            for name, param in model.named_parameters():
                if "weight" in name and param.dim() >= 2:
                    param.clamp_(-1.0, 1.0)

        running_loss += loss.item() * inputs.size(0)
        _, preds = outputs.max(1)
        correct += preds.eq(targets).sum().item()
        total += targets.size(0)

    return running_loss / total, 100.0 * correct / total


def evaluate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, targets in dataloader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)

            running_loss += loss.item() * inputs.size(0)
            _, preds = outputs.max(1)
            correct += preds.eq(targets).sum().item()
            total += targets.size(0)

    return running_loss / total, 100.0 * correct / total


def run_training(dataset_name="cifar10_4class", epochs=35, batch_size=128, lr=1e-3, data_dir="./data"):
    device = torch.device("cpu")
    print(f"============================================================")
    print(f" Starting QAT Training for MicroResNet16 on: {dataset_name}")
    print(f" Target Device: {device} | Epochs: {epochs} | Batch Size: {batch_size}")
    print(f"============================================================")

    train_set, test_set, num_classes, class_names = get_dataset(dataset_name, data_dir)
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=2)
    test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=False, num_workers=2)

    model = MicroResNetQAT(num_classes=num_classes).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    best_acc = 0.0
    best_state = None
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        test_loss, test_acc = evaluate(model, test_loader, criterion, device)
        scheduler.step()
        dt = time.time() - t0

        if test_acc > best_acc:
            best_acc = test_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if epoch % 5 == 0 or epoch == epochs or epoch == 1:
            print(f" Epoch [{epoch:2d}/{epochs:2d}] ({dt:.1f}s) | "
                  f"Train Loss: {train_loss:.4f}, Acc: {train_acc:5.1f}% | "
                  f"Test Loss: {test_loss:.4f}, Acc: {test_acc:5.1f}% (Best: {best_acc:5.1f}%)")

    total_time = time.time() - start_time
    print(f"------------------------------------------------------------")
    print(f" Training Completed in {total_time:.1f} seconds! Best Test Acc: {best_acc:.2f}%")
    print(f"============================================================")

    # Save checkpoint
    out_dir = os.path.dirname(os.path.abspath(__file__))
    ckpt_path = os.path.join(out_dir, f"micro_resnet_qat_{dataset_name}.pt")
    torch.save({
        "state_dict": best_state,
        "dataset_name": dataset_name,
        "num_classes": num_classes,
        "class_names": class_names,
        "best_acc": best_acc
    }, ckpt_path)
    print(f" Saved checkpoint to: {ckpt_path}")

    return ckpt_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train QAT MicroResNet-16 model")
    parser.add_argument("--dataset", type=str, default="cifar10_4class",
                        choices=["cifar10_4class", "cifar10_10class", "fashion_mnist"],
                        help="Target dataset profile")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=128, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Initial learning rate")
    parser.add_argument("--data-dir", type=str, default="./data", help="Directory for dataset downloads")
    args = parser.parse_args()

    run_training(args.dataset, args.epochs, args.batch_size, args.lr, args.data_dir)
