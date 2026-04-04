import torch
import torch.nn as nn


class PolicyNet(nn.Module):
    def __init__(self, input_dim=180, hidden=[256, 128, 64], output_dim=2):
        super().__init__()

        layers = []
        prev = input_dim

        for h in hidden:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            prev = h

        layers.append(nn.Linear(prev, output_dim))

        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

