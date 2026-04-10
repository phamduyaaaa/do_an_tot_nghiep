"""Module containing the Policy Network architecture for Behavior Cloning."""

import torch.nn as nn


class PolicyNet(nn.Module):
    """Multi-layer Perceptron for robotics control policy."""

    def __init__(
        self,
        input_dim: int = 180,
        hidden: list[int] | None = None,
        output_dim: int = 2,
    ):
        """Initializes the network layers.

        Args:
            input_dim: Dimension of the input state (e.g., LiDAR scans).
            hidden: List of hidden layer sizes. Defaults to [256, 128, 64].
            output_dim: Dimension of the action space (e.g., v, w).
        """
        super().__init__()

        if hidden is None:
            hidden = [256, 128, 64]

        layers: list[nn.Module] = []
        prev = input_dim

        for h in hidden:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            prev = h

        # Final output layer without activation (regression)
        layers.append(nn.Linear(prev, output_dim))

        self.net = nn.Sequential(*layers)

    def forward(self, x: nn.Module) -> nn.Module:
        """Performs a forward pass.

        Args:
            x: Input tensor of shape (batch_size, input_dim).

        Returns:
            Output tensor of shape (batch_size, output_dim).
        """
        return self.net(x)
