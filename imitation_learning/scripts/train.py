"""Behavior Cloning Training Script.

Trains a Policy Network using Imitation Learning (Behavior Cloning).
Reads LiDAR and velocity data from a CSV, trains the PyTorch model,
and saves the weights.
"""

import argparse
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from models.model import PolicyNet
from torch.utils.data import DataLoader, Dataset


class ILDataset(Dataset):
    """Dataset class for Imitation Learning data."""

    def __init__(self, csv_file: str, input_dim: int = 180):
        """Initializes the dataset and performs normalization.

        Args:
            csv_file: Path to the CSV dataset.
            input_dim: Number of LiDAR features.

        Raises:
            FileNotFoundError: If the dataset file does not exist.
        """
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"Dataset file not found: {csv_file}")

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
        """Gets a sample at the specified index."""
        return self.X[idx], self.y[idx]


def train(
    data_path: str,
    out_path: str,
    epochs: int = 20,
    batch_size: int = 64,
    lr: float = 1e-3,
    input_dim: int = 180,
) -> None:
    """Trains the PolicyNet model.

    Args:
        data_path: Path to the input CSV.
        out_path: Path to save the trained .pth model.
        epochs: Number of training iterations.
        batch_size: Size of training batches.
        lr: Learning rate for Adam optimizer.
        input_dim: Dimension of the LiDAR input.
    """
    # 1. Setup Data
    try:
        dataset = ILDataset(data_path, input_dim)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # 2. Setup Device & Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PolicyNet(input_dim=input_dim).to(device)
    model.train()

    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

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
        print(f"Epoch {epoch+1:03d}/{epochs:03d} | Loss: {epoch_loss:.6f}")

    # 4. Save PyTorch Model
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    torch.save(model.state_dict(), out_path)
    print(f"[INFO] Saved model to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="logs/dataset.csv")
    parser.add_argument("--output", type=str, default="checkpoints/bc_model.pth")  # noqa: E501
    parser.add_argument("--epochs", type=int, default=100)
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
