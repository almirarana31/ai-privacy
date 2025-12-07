"""
PyTorch model architectures for Privacy Playground.
Includes FNN, FNN-DP (Opacus compatible), and Logistic Regression models.
"""

import torch
import torch.nn as nn


class FeedforwardNN(nn.Module):
    """
    Feedforward Neural Network with BatchNorm.
    Used for baseline (non-DP) training.
    
    Architecture: Input -> [128, 64, 32] -> Output (2 classes)
    """
    def __init__(self, input_size: int, hidden_sizes: list = None, output_size: int = 2, dropout_rate: float = 0.3):
        super(FeedforwardNN, self).__init__()
        
        if hidden_sizes is None:
            hidden_sizes = [128, 64, 32]
        
        layers = []
        prev_size = input_size
        
        # Create hidden layers
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.BatchNorm1d(hidden_size))
            layers.append(nn.Dropout(dropout_rate))
            prev_size = hidden_size
        
        # Output layer
        layers.append(nn.Linear(prev_size, output_size))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


class FeedforwardNN_DP(nn.Module):
    """
    Differential Privacy compatible FNN using GroupNorm instead of BatchNorm.
    Required for Opacus DP-SGD training.
    
    Architecture: Input -> [128, 64, 32] -> Output (2 classes)
    """
    def __init__(self, input_size: int, hidden_sizes: list = None, output_size: int = 2, dropout_rate: float = 0.3):
        super(FeedforwardNN_DP, self).__init__()
        
        if hidden_sizes is None:
            hidden_sizes = [128, 64, 32]
        
        layers = []
        prev_size = input_size
        
        # Create hidden layers with GroupNorm (Opacus compatible)
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            # Use GroupNorm instead of BatchNorm for DP compatibility
            num_groups = min(32, hidden_size)
            while hidden_size % num_groups != 0:
                num_groups -= 1
            layers.append(nn.GroupNorm(num_groups, hidden_size))
            layers.append(nn.Dropout(dropout_rate))
            prev_size = hidden_size
        
        # Output layer
        layers.append(nn.Linear(prev_size, output_size))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


class LogisticRegression_DP(nn.Module):
    """
    Differential Privacy compatible Logistic Regression model.
    Simple linear classifier - inherently compatible with Opacus.
    """
    def __init__(self, input_size: int, output_size: int = 2):
        super(LogisticRegression_DP, self).__init__()
        self.linear = nn.Linear(input_size, output_size)
    
    def forward(self, x):
        return self.linear(x)


# Model configuration constants
MODEL_CONFIGS = {
    'diabetes': {
        'input_size': 21,
        'hidden_sizes': [128, 64, 32],
        'output_size': 2
    },
    'adult': {
        'input_size': 14,
        'hidden_sizes': [128, 64, 32],
        'output_size': 2
    }
}


def get_model_class(model_type: str):
    """
    Get the appropriate model class based on model type string.
    
    Args:
        model_type: One of 'fnn_baseline', 'fnn_dp', 'lr_dp'
    
    Returns:
        Model class
    """
    if model_type == 'fnn_baseline':
        return FeedforwardNN
    elif model_type.startswith('fnn_dp'):
        return FeedforwardNN_DP
    elif model_type.startswith('lr_dp'):
        return LogisticRegression_DP
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def create_model(dataset: str, model_type: str) -> nn.Module:
    """
    Create a model instance for the given dataset and model type.
    
    Args:
        dataset: 'diabetes' or 'adult'
        model_type: 'fnn_baseline', 'fnn_dp_eps{X}', or 'lr_dp_eps{X}'
    
    Returns:
        Instantiated model (weights not loaded)
    """
    config = MODEL_CONFIGS.get(dataset)
    if not config:
        raise ValueError(f"Unknown dataset: {dataset}")
    
    model_class = get_model_class(model_type)
    
    if model_type.startswith('lr'):
        # Logistic regression only needs input and output size
        return model_class(
            input_size=config['input_size'],
            output_size=config['output_size']
        )
    else:
        # FNN models use hidden layers
        return model_class(
            input_size=config['input_size'],
            hidden_sizes=config['hidden_sizes'],
            output_size=config['output_size']
        )
