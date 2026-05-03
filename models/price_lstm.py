"""
MarketIntel AI: Price LSTM Architecture
=======================================

Defines the PyTorch architecture for the core deep learning sequence model.
"""
import torch
import torch.nn as nn

class PriceLSTM(nn.Module):
    """
    Long Short-Term Memory (LSTM) network designed for multivariate 
    time-series forecasting.

    It maps a sequential window of technical indicators and prices to a 
    single continuous price prediction.
    """
    def __init__(self, input_dim=5, hidden_dim=64, num_layers=2, output_dim=1):
        """
        Initializes the PyTorch module.

        Args:
            input_dim (int): Number of features per time step.
            hidden_dim (int): Dimensionality of the hidden state.
            num_layers (int): Number of stacked LSTM layers.
            output_dim (int): Target prediction dimension.
        """
        super(PriceLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # LSTM Layer
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        
        # Fully Connected Layer
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        # Initialize hidden state and cell state
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        
        # Forward propagate LSTM
        out, _ = self.lstm(x, (h0, c0))
        
        # Decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        return out
