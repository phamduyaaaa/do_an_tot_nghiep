"""
================================================================================
Behavior Cloning Training & Plotting Script

* Purpose: Trains a Policy Network (Behavior Cloning) using Imitation Learning 
           data. It saves the trained model weights and generates a high-quality 
           training loss plot specifically formatted for the Streamlit dashboard.
* Inputs:  - CSV dataset containing downsampled LiDAR scans and velocity commands.
* Outputs: - PyTorch model checkpoint (.pth) saved in the `checkpoints/` directory.
           - Loss curve image (.png) saved in the `plots/` directory.
* Args:    - --data (str): Path to input CSV dataset (default: logs/dataset.csv)
           - --output (str): Path to save the model (default: checkpoints/bc_model.pth)
           - --epochs (int): Number of training epochs (default: 20)
           - --batch (int): Batch size (default: 64)
           - --lr (float): Learning rate (default: 1e-3)
           - --input_dim (int): LiDAR input feature dimension (default: 180)
* Usage:   python scripts/train_plot.py --data logs/data.csv --output checkpoints/model.pth
================================================================================
"""

import argparse
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
from models.model import PolicyNet
import os
import matplotlib.pyplot as plt


class ILDataset(Dataset):
    def __init__(self, csv_file, input_dim=180):
        data = np.loadtxt(csv_file, delimiter=',')
        
        # Split states (X) and actions (y)
        self.X = data[:, :input_dim].astype(np.float32)
        self.y = data[:, input_dim:input_dim+2].astype(np.float32)

        # Normalize LiDAR data: clip to max_range and scale to [0, 1]
        self.X = np.clip(self.X, 0.0, 3.5) / 3.5

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def train(data_path, out_path, epochs=20, batch_size=64, lr=1e-3, input_dim=180):
    # 1. Setup Data
    dataset = ILDataset(data_path, input_dim)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # 2. Setup Device & Model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PolicyNet(input_dim=input_dim).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    loss_history = []

    print(f"[INFO] Starting training on {device} for {epochs} epochs...")
    
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
        
        # Formatted output for better readability in Streamlit logs
        print(f"Epoch {epoch+1:03d}/{epochs:03d} | Loss: {epoch_loss:.6f}")

    # 4. Save PyTorch Model
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    torch.save(model.state_dict(), out_path)
    print(f"[INFO] Saved model to: {out_path}")

    # 5. Generate and Save UI-Friendly Plot
    os.makedirs('plots', exist_ok=True)
    
    # Extract base name to match model name (e.g., 'model.pth' -> 'model_loss.png')
    base_name = os.path.splitext(os.path.basename(out_path))[0]
    plot_path = os.path.join('plots', f"{base_name}_loss.png")

    plt.figure(figsize=(10, 5))  # Optimized ratio for web dashboard
    plt.plot(range(1, epochs + 1), loss_history, label='Train MSE Loss', color='#1f77b4', linewidth=2)
    
    plt.xlabel("Epoch", fontweight='bold')
    plt.ylabel("MSE Loss", fontweight='bold')
    plt.title(f"Behavior Cloning Training Loss ({base_name})", fontsize=14, pad=15)
    
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # bbox_inches='tight' removes unnecessary white margins
    plt.savefig(plot_path, bbox_inches='tight', dpi=150)
    plt.close()

    print(f"[INFO] Saved loss plot to: {plot_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Train PolicyNet and generate loss plot")
    parser.add_argument('--data', type=str, default='logs/dataset.csv', help="Path to input CSV")
    parser.add_argument('--output', type=str, default='checkpoints/bc_model.pth', help="Path to save the model")
    parser.add_argument('--epochs', type=int, default=20, help="Number of training epochs")
    parser.add_argument('--batch', type=int, default=64, help="Batch size")
    parser.add_argument('--lr', type=float, default=1e-3, help="Learning rate")
    parser.add_argument('--input_dim', type=int, default=180, help="LiDAR input dimension")

    args = parser.parse_args()

    train(
        data_path=args.data,
        out_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr,
        input_dim=args.input_dim
    )
