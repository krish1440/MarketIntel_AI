"""
MarketIntel AI: Price Prediction Training Utilities
===================================================

Contains hardware-optimized PyTorch utilities to build and train the LSTM model.
Includes built-in optimizations for Intel hardware (IPEX).
"""
import torch
import torch.nn as nn
import torch.optim as optim
import os

try:
    import intel_extension_for_pytorch as ipex
    IPEX_AVAILABLE = True
except ImportError:
    IPEX_AVAILABLE = False
    print("Intel Extension for PyTorch not found. Falling back to CPU.")

class StockLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, output_dim):
        super(StockLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

def train_model(X_train, y_train, input_dim, hidden_dim=64, num_layers=2, output_dim=1, epochs=50, lr=0.001):
    """
    Trains the StockLSTM model using PyTorch.

    Args:
        X_train (torch.Tensor): Training sequence inputs.
        y_train (torch.Tensor): Training target outputs.
        input_dim (int): Number of features.
        hidden_dim (int): Dimensionality of the hidden state.
        num_layers (int): Number of LSTM layers.
        output_dim (int): Target dimension.
        epochs (int): Training iterations.
        lr (float): Learning rate.

    Returns:
        torch.nn.Module: The trained PyTorch model.
    """
    model = StockLSTM(input_dim, hidden_dim, num_layers, output_dim)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    if IPEX_AVAILABLE:
        # Optimize model and optimizer for Intel hardware
        model, optimizer = ipex.optimize(model, optimizer=optimizer)
        print("Model optimized with Intel Extension for PyTorch.")

    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_train)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()
        
        if (epoch+1) % 10 == 0:
            print(f'Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}')
            
    return model

def save_model(model, path='models/checkpoints/price_model.pth'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(model.state_state(), path)
    print(f"Model saved to {path}")
