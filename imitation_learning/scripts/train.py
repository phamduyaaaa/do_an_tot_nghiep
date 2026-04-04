import argparse
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
from model import PolicyNet
import os


class ILDataset(Dataset):
    def __init__(self, csv_file, input_dim=180):
        data = np.loadtxt(csv_file, delimiter=',')
        # last two columns are actions
        self.X = data[:, :input_dim].astype(np.float32)
        self.y = data[:, input_dim:input_dim+2].astype(np.float32)

        # simple normalization: clip and divide by max_range
        self.X = np.clip(self.X, 0.0, 3.5) / 3.5

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def train(data_path, out_path, epochs=20, batch_size=64, lr=1e-3, input_dim=180):
    dataset = ILDataset(data_path, input_dim)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PolicyNet(input_dim=input_dim).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    for epoch in range(epochs):
        epoch_loss = 0.0
        for Xb, yb in loader:
            Xb = Xb.to(device)
            yb = yb.to(device)

            preds = model(Xb)
            loss = criterion(preds, yb)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item() * Xb.size(0)

        epoch_loss /= len(dataset)
        print(f"Epoch {epoch+1}/{epochs}, Loss: {epoch_loss:.6f}")

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    torch.save(model.state_dict(), out_path)
    print("Saved model to", out_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default='dataset_14.csv')
    parser.add_argument('--output', type=str, default='bc_model_14.pth')
    parser.add_argument('--epochs', type=int, default=500)
    parser.add_argument('--batch', type=int, default=64)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--input_dim', type=int, default=180)

    args = parser.parse_args()

    train(
        data_path=args.data,
        out_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr,
        input_dim=args.input_dim
    )

