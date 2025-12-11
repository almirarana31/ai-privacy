"""
Model loader service for Privacy Playground.
Handles loading pre-trained PyTorch models with pattern-based file discovery.
"""

import os
import glob
import torch
from typing import Dict, Optional, List, Tuple
from pathlib import Path

from models.architectures import create_model, MODEL_CONFIGS


class ModelLoader:
    """
    Loads and manages pre-trained models for the Privacy Playground backend.
    Supports hot-reloading of models without server restart.
    """
    
    def __init__(self, models_dir: str = None):
        """
        Initialize the model loader.
        
        Args:
            models_dir: Directory containing .pth model files
        """
        if models_dir is None:
            # Default to backend/models directory
            models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
        
        self.models_dir = models_dir
        self.loaded_models: Dict[str, torch.nn.Module] = {}
        self.model_metadata: Dict[str, dict] = {}
        self.device = torch.device('cpu')  # Use CPU for inference
        
    def discover_models(self) -> List[str]:
        """
        Discover all .pth model files in the models directory.
        
        Returns:
            List of model file paths
        """
        pattern = os.path.join(self.models_dir, '*.pth')
        return glob.glob(pattern)
    
    def parse_model_filename(self, filepath: str) -> Optional[dict]:
        """
        Parse model filename to extract dataset, model type, and metadata.
        
        Expected formats:
            - {dataset}_{model_type}_{timestamp}.pth (baseline)
            - {dataset}_{model_type}_dp_eps{X}_{timestamp}.pth (DP)
            - fl_{MODEL}_{dataset}_{aggregation}_{timestamp}.pth (FL)
        
        Examples:
            - diabetes_fnn_baseline_20251205_014119.pth
            - diabetes_fnn_dp_eps1.0_20251205_014119.pth
            - fl_FNN_diabetes_FedAvg_20251210_003232.pth
            - fl_LR_adult_FedAdam_20251210_002519.pth
        
        Args:
            filepath: Path to model file
        
        Returns:
            Dict with 'dataset', 'model_type', 'epsilon', 'aggregation' (if applicable)
        """
        filename = os.path.basename(filepath)
        name_without_ext = filename.replace('.pth', '')
        
        parts = name_without_ext.split('_')
        if len(parts) < 3:
            return None
        
        # Check if it's a Federated Learning model
        if parts[0] == 'fl':
            # Format: fl_{MODEL}_{dataset}_{aggregation}_{timestamp}
            if len(parts) < 4:
                return None
            
            fl_model_type = parts[1].lower()  # 'FNN' or 'LR'
            dataset = parts[2]  # 'diabetes' or 'adult'
            aggregation = parts[3]  # 'FedAvg', 'FedAdam', etc.
            
            model_type = f"fl_{fl_model_type}"
            
            return {
                'dataset': dataset,
                'model_type': model_type,
                'epsilon': None,
                'aggregation': aggregation,
                'filepath': filepath,
                'is_federated': True
            }
        
        # Standard DP/baseline models
        dataset = parts[0]  # 'diabetes' or 'adult'
        model_arch = parts[1].lower()  # Convert to lowercase (FNN -> fnn, LR -> lr)
        
        # Check if it's a baseline or DP model
        if 'baseline' in name_without_ext:
            model_type = f"{model_arch}_baseline"  # e.g., 'fnn_baseline'
            epsilon = None
            aggregation = None
        elif 'dp_eps' in name_without_ext:
            # Find epsilon value
            epsilon = None
            for part in parts:
                if part.startswith('eps'):
                    epsilon = float(part.replace('eps', ''))
                    break
            model_type = f"{model_arch}_dp"  # e.g., 'fnn_dp' or 'lr_dp'
            aggregation = None
        else:
            return None
        
        return {
            'dataset': dataset,
            'model_type': model_type,
            'epsilon': epsilon,
            'aggregation': aggregation,
            'filepath': filepath,
            'is_federated': False
        }
    
    def get_model_key(self, dataset: str, model_type: str, epsilon: float = None, aggregation: str = None) -> str:
        """
        Generate a unique key for a model based on its parameters.
        
        Args:
            dataset: 'diabetes' or 'adult'
            model_type: 'fnn_baseline', 'fnn_dp', 'lr_dp', 'fl_fnn', 'fl_lr'
            epsilon: Privacy budget (for DP models)
            aggregation: Aggregation method (for FL models)
        
        Returns:
            Unique string key
        """
        if aggregation is not None:
            return f"{dataset}_{model_type}_{aggregation}"
        if epsilon is not None:
            return f"{dataset}_{model_type}_eps{epsilon}"
        return f"{dataset}_{model_type}"
    
    def load_model(self, filepath: str) -> Tuple[torch.nn.Module, dict]:
        """
        Load a single model from a .pth file.
        
        Args:
            filepath: Path to the model file
        
        Returns:
            Tuple of (model, metadata)
        """
        info = self.parse_model_filename(filepath)
        if info is None:
            raise ValueError(f"Could not parse model filename: {filepath}")
        
        # Load checkpoint first to get architecture info
        checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)
        
        # Extract model state dict and metadata based on checkpoint format
        if 'model_state_dict' in checkpoint:
            # New format with metadata
            state_dict = checkpoint['model_state_dict']
            model_architecture = checkpoint.get('model_architecture', {})
            training_config = checkpoint.get('training_config', {})
            metadata = {
                'preprocessing': checkpoint.get('preprocessing', {}),
                'model_architecture': model_architecture,
                'metadata': checkpoint.get('metadata', {}),
                'training_config': training_config,
                'results': checkpoint.get('results', {}),
                'aggregation': info.get('aggregation'),
                'is_federated': info.get('is_federated', False)
            }
        else:
            # Simple format - just state dict
            state_dict = checkpoint
            model_architecture = {}
            metadata = {
                'aggregation': info.get('aggregation'),
                'is_federated': info.get('is_federated', False)
            }
        
        # Handle Opacus wrapped model state dict
        # Opacus adds '_module.' prefix to all keys
        cleaned_state_dict = {}
        for key, value in state_dict.items():
            if key.startswith('_module.'):
                cleaned_state_dict[key.replace('_module.', '')] = value
            else:
                cleaned_state_dict[key] = value
        
        # Create model with the correct architecture from checkpoint
        # Use the saved architecture info to reconstruct the exact model
        model_type_key = info['model_type']
        dataset = info['dataset']
        
        # If we have architecture info from the checkpoint, use it to construct the model
        # Otherwise, fall back to the legacy create_model function
        if model_architecture and 'input_size' in model_architecture:
            # Reconstruct model using saved architecture
            from models.architectures import FeedforwardNN_Simple, LogisticRegressionModel
            
            input_size = model_architecture.get('input_size')
            output_size = model_architecture.get('output_size', 2)
            hidden_sizes = model_architecture.get('hidden_sizes')
            dropout_rate = model_architecture.get('dropout_rate', 0.3)
            
            # Determine which class to use based on model type
            if 'lr' in model_type_key.lower():
                model = LogisticRegressionModel(input_size=input_size, output_size=output_size)
            else:  # FNN variant
                # Use FeedforwardNN_Simple for newly trained DP models
                # (matches the notebook architecture)
                model = FeedforwardNN_Simple(
                    input_size=input_size,
                    hidden_sizes=hidden_sizes,
                    output_size=output_size,
                    dropout_rate=dropout_rate
                )
        else:
            # Fallback to legacy approach
            model_type_full = info['model_type']
            if info.get('epsilon') is not None:
                model_type_full = f"{info['model_type']}_eps{info['epsilon']}"
            model = create_model(dataset, model_type_full)
        
        model.load_state_dict(cleaned_state_dict)
        model.eval()
        model.to(self.device)
        
        return model, metadata
    
    def load_all_models(self) -> Dict[str, dict]:
        """
        Load all discovered models into memory.
        For duplicate model keys (e.g., multiple baseline models for same dataset),
        only the newest file (by modification time) is loaded.
        
        Returns:
            Dictionary of model info with keys and metadata
        """
        model_files = self.discover_models()
        loaded_info = {}
        
        # Group files by their model key and keep only the newest
        file_groups = {}
        for filepath in model_files:
            info = self.parse_model_filename(filepath)
            if info is None:
                print(f"Skipping unparseable file: {filepath}")
                continue
            
            key = self.get_model_key(
                info['dataset'], 
                info['model_type'], 
                info.get('epsilon'),
                info.get('aggregation')
            )
            
            # Get file modification time
            mtime = os.path.getmtime(filepath)
            
            # Keep only the newest file for each key
            if key not in file_groups or mtime > file_groups[key]['mtime']:
                file_groups[key] = {
                    'filepath': filepath,
                    'mtime': mtime,
                    'info': info
                }
        
        # Now load the selected files
        for key, file_data in file_groups.items():
            filepath = file_data['filepath']
            info = file_data['info']
            
            try:
                model, metadata = self.load_model(filepath)
                
                self.loaded_models[key] = model
                self.model_metadata[key] = {
                    **info,
                    **metadata
                }
                
                loaded_info[key] = {
                    'dataset': info['dataset'],
                    'model_type': info['model_type'],
                    'epsilon': info.get('epsilon'),
                    'aggregation': info.get('aggregation'),
                    'is_federated': info.get('is_federated', False),
                    'loaded': True
                }
                
                print(f"✓ Loaded: {key} from {os.path.basename(filepath)}")
                
            except Exception as e:
                print(f"✗ Failed to load {filepath}: {e}")
        
        return loaded_info
    
    def reload_models(self) -> Dict[str, dict]:
        """
        Hot-reload all models from disk.
        
        Returns:
            Dictionary of newly loaded model info
        """
        self.loaded_models.clear()
        self.model_metadata.clear()
        return self.load_all_models()
    
    def get_model(self, dataset: str, model_type: str, epsilon: float = None, aggregation: str = None) -> Optional[torch.nn.Module]:
        """
        Get a loaded model by its parameters.
        
        Args:
            dataset: 'diabetes' or 'adult'
            model_type: Model type string
            epsilon: Privacy budget (for DP models)
            aggregation: Aggregation method (for FL models)
        
        Returns:
            Model instance or None if not found
        """
        key = self.get_model_key(dataset, model_type, epsilon, aggregation)
        return self.loaded_models.get(key)
    
    def get_model_metadata(self, dataset: str, model_type: str, epsilon: float = None, aggregation: str = None) -> Optional[dict]:
        """
        Get metadata for a loaded model.
        
        Args:
            dataset: 'diabetes' or 'adult'
            model_type: Model type string
            epsilon: Privacy budget (for DP models)
            aggregation: Aggregation method (for FL models)
        
        Returns:
            Metadata dict or None if not found
        """
        key = self.get_model_key(dataset, model_type, epsilon, aggregation)
        return self.model_metadata.get(key)
    
    def list_available_models(self) -> List[dict]:
        """
        List all loaded models with their parameters.
        
        Returns:
            List of model info dictionaries
        """
        models = []
        for key, metadata in self.model_metadata.items():
            models.append({
                'key': key,
                'dataset': metadata.get('dataset'),
                'model_type': metadata.get('model_type'),
                'epsilon': metadata.get('epsilon'),
                'aggregation': metadata.get('aggregation'),
                'is_federated': metadata.get('is_federated', False)
            })
        return models
    
    def get_available_epsilons(self, dataset: str, model_type: str) -> List[float]:
        """
        Get list of available epsilon values for a dataset and model type.
        
        Args:
            dataset: 'diabetes' or 'adult'
            model_type: 'fnn_dp' or 'lr_dp'
        
        Returns:
            Sorted list of epsilon values
        """
        epsilons = []
        for key, metadata in self.model_metadata.items():
            if metadata.get('dataset') == dataset and metadata.get('model_type') == model_type:
                if metadata.get('epsilon') is not None:
                    epsilons.append(metadata['epsilon'])
        return sorted(epsilons)


# Global model loader instance
_model_loader: Optional[ModelLoader] = None


def get_model_loader() -> ModelLoader:
    """Get the global model loader instance."""
    global _model_loader
    if _model_loader is None:
        _model_loader = ModelLoader()
    return _model_loader


def initialize_models() -> Dict[str, dict]:
    """Initialize and load all models on startup."""
    loader = get_model_loader()
    return loader.load_all_models()
