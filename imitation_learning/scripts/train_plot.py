"""Behavior Cloning Training & Plotting Script.

Trains a Policy Network using Imitation Learning data, saves model weights,
and generates a loss curve plot for the Streamlit dashboard.
"""

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from models.model import PolicyNet
from torch.utils.data import DataLoader, Dataset


class ILDataset(Dataset):
    """Custom Dataset for loading LiDAR-Action pairs from CSV."""

    def __init__(self, csv_file: str, input_dim: int = 180):
        """Initializes dataset and normalizes features.

        Args:
            csv_file: Path to the CSV dataset.
            input_dim: Number of LiDAR features.
        """
        data = np.loadtxt(csv_file, delimiter=",")

        # Split states (X) and actions (y)
        self.X = data[:, :input_dim].astype(np.float32)
        self.y = data[:, input_dim : input_dim + 2].astype(np.float32)

        # Normalize LiDAR data: clip to max_range and scale to [0, 1]
        self.X = np.clip(self.X, 0.0, 3.5) / 3.5

    def __len__(self) -> int:
        """Returns the total number of samples."""
        return len(self.X)

    def __getitem__(self, idx: int) -> tuple[np.ndarray, np.ndarray]:
        """Gets a single sample pair."""
        return self.X[idx], self.y[idx]


def train(
    data_path: str,
    out_path: str,
    epochs: int = 20,
    batch_size: int = 64,
    lr: float = 1e-3,
    input_dim: int = 180,
) -> None:
    """Trains the model and saves results.

    Args:
        data_path: Path to the training CSV.
        out_path: Path to save the .pth checkpoint.
        epochs: Total training epochs.
        batch_size: Size of mini-batches.
        lr: Learning rate for Adam.
        input_dim: LiDAR feature count.
    """
    # 1. Setup Data
    dataset = ILDataset(data_path, input_dim)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # 2. Setup Device & Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PolicyNet(input_dim=input_dim).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    loss_history = []

    print(f"[INFO] Training on {device} for {epochs} epochs...")

    # 3. Training Loop
    for epoch in range(epochs):
        epoch_loss = 0.0
        for Xb, yb in loader:
            Xb, yb = Xb.to(device), yb.to(device)

            preds = model(Xb)
            loss = criterion(preds, yb)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item() * Xb.size(0)

        epoch_loss /= len(dataset)
        loss_history.append(epoch_loss)
        print(f"Epoch {epoch+1:03d}/{epochs:03d} | Loss: {epoch_loss:.6f}")

    # 4. Save PyTorch Model
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    torch.save(model.state_dict(), out_path)
    print(f"[INFO] Saved model to: {out_path}")

    # 5. Generate and Save UI-Friendly Plot
    os.makedirs("plots", exist_ok=True)
    base_name = os.path.splitext(os.path.basename(out_path))[0]
    plot_path = os.path.join("plots", f"{base_name}_loss.png")

    plt.figure(figsize=(10, 5))
    plt.plot(
        range(1, epochs + 1),
        loss_history,
        label="Train MSE Loss",
        color="#1f77b4",
        linewidth=2,
    )

    plt.xlabel("Epoch", fontweight="bold")
    plt.ylabel("MSE Loss", fontweight="bold")
    plt.title(f"BC Training Loss ({base_name})", fontsize=14, pad=15)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)

    plt.savefig(plot_path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"[INFO] Saved loss plot to: {plot_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="logs/dataset.csv")
    parser.add_argument("--output", type=str, default="checkpoints/bc_model.pth")  # noqa: E501
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--input_dim", type=int, default=180)

    args = parser.parse_args()

    train(
        data_path=args.data,
        out_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr,
        input_dim=args.input_dim,
    )
