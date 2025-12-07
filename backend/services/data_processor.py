"""
Data processing service for Privacy Playground.
Handles CSV preprocessing with flexible column mapping for uploaded data.
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from io import StringIO

from models.architectures import MODEL_CONFIGS


class DataProcessor:
    """
    Processes data for model inference.
    Supports both local test data and user-uploaded CSV files.
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the data processor.
        
        Args:
            data_dir: Directory containing preprocessed test data files
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        
        self.data_dir = data_dir
        self.test_data: Dict[str, dict] = {}
        self.scalers: Dict[str, object] = {}
        self.feature_names: Dict[str, List[str]] = {}
        
    def load_test_data(self) -> Dict[str, dict]:
        """
        Load preprocessed test data from .npy files.
        
        Expected files in data_dir:
            - diabetes_X_test.npy
            - diabetes_y_test.npy
            - diabetes_scaler.pkl
            - diabetes_features.pkl
            - adult_X_test.npy
            - adult_y_test.npy
            - adult_scaler.pkl
            - adult_features.pkl
        
        Returns:
            Dictionary with loaded test data info
        """
        loaded = {}
        
        for dataset in ['diabetes', 'adult']:
            try:
                X_path = os.path.join(self.data_dir, f'{dataset}_X_test.npy')
                y_path = os.path.join(self.data_dir, f'{dataset}_y_test.npy')
                scaler_path = os.path.join(self.data_dir, f'{dataset}_scaler.pkl')
                features_path = os.path.join(self.data_dir, f'{dataset}_features.pkl')
                
                if os.path.exists(X_path) and os.path.exists(y_path):
                    X_test = np.load(X_path)
                    y_test = np.load(y_path)
                    
                    self.test_data[dataset] = {
                        'X': X_test,
                        'y': y_test
                    }
                    
                    loaded[dataset] = {
                        'samples': len(y_test),
                        'features': X_test.shape[1]
                    }
                    
                    print(f"✓ Loaded test data for {dataset}: {X_test.shape}")
                else:
                    print(f"⚠ Test data not found for {dataset}")
                
                # Load scaler if available
                if os.path.exists(scaler_path):
                    with open(scaler_path, 'rb') as f:
                        self.scalers[dataset] = pickle.load(f)
                    print(f"✓ Loaded scaler for {dataset}")
                
                # Load feature names if available
                if os.path.exists(features_path):
                    with open(features_path, 'rb') as f:
                        self.feature_names[dataset] = pickle.load(f)
                    print(f"✓ Loaded feature names for {dataset}")
                    
            except Exception as e:
                print(f"✗ Error loading {dataset} data: {e}")
        
        return loaded
    
    def get_test_data(self, dataset: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Get preprocessed test data for a dataset.
        
        Args:
            dataset: 'diabetes' or 'adult'
        
        Returns:
            Tuple of (X_test, y_test) or None if not loaded
        """
        if dataset not in self.test_data:
            return None
        
        data = self.test_data[dataset]
        return data['X'], data['y']
    
    def get_dataset_info(self, dataset: str) -> dict:
        """
        Get information about a dataset.
        
        Args:
            dataset: 'diabetes' or 'adult'
        
        Returns:
            Dict with dataset info
        """
        config = MODEL_CONFIGS.get(dataset, {})
        
        info = {
            'name': dataset,
            'input_size': config.get('input_size', 0),
            'feature_names': self.feature_names.get(dataset, []),
            'has_test_data': dataset in self.test_data,
            'has_scaler': dataset in self.scalers
        }
        
        if dataset in self.test_data:
            info['test_samples'] = len(self.test_data[dataset]['y'])
        
        return info
    
    def process_uploaded_csv(
        self,
        csv_content: str,
        dataset: str,
        target_column: str = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray], dict]:
        """
        Process an uploaded CSV file for model inference.
        
        Supports flexible column mapping:
        - If CSV has same number of numeric columns as expected, use as-is
        - If target_column specified, separate features and target
        - Applies scaler if available
        
        Args:
            csv_content: CSV file content as string
            dataset: 'diabetes' or 'adult' (determines expected features)
            target_column: Optional name of target column to separate
        
        Returns:
            Tuple of (X, y or None, info_dict)
        """
        expected_features = MODEL_CONFIGS.get(dataset, {}).get('input_size', 0)
        
        # Parse CSV
        try:
            df = pd.read_csv(StringIO(csv_content))
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {e}")
        
        info = {
            'original_shape': df.shape,
            'columns': list(df.columns),
            'numeric_columns': [],
            'target_column': target_column,
            'features_used': expected_features
        }
        
        # Separate target if specified
        y = None
        if target_column and target_column in df.columns:
            y = df[target_column].values
            df = df.drop(columns=[target_column])
            
            # Encode target if it's categorical
            if y.dtype == 'object':
                unique_vals = np.unique(y)
                # Try to map to binary
                if len(unique_vals) == 2:
                    y = (y == unique_vals[1]).astype(np.int64)
                else:
                    # Simple label encoding
                    mapping = {val: i for i, val in enumerate(unique_vals)}
                    y = np.array([mapping[v] for v in y], dtype=np.int64)
        
        # Get numeric columns only
        numeric_df = df.select_dtypes(include=[np.number])
        info['numeric_columns'] = list(numeric_df.columns)
        
        # Encode any remaining categorical columns
        for col in df.columns:
            if col not in numeric_df.columns:
                df[col] = pd.factorize(df[col])[0]
        
        numeric_df = df.select_dtypes(include=[np.number])
        
        # Validate feature count
        if len(numeric_df.columns) < expected_features:
            raise ValueError(
                f"Not enough numeric features. Expected {expected_features}, "
                f"got {len(numeric_df.columns)}. "
                f"Columns found: {list(numeric_df.columns)}"
            )
        
        # Use first N columns if more than expected
        if len(numeric_df.columns) > expected_features:
            numeric_df = numeric_df.iloc[:, :expected_features]
            info['warning'] = f"Using first {expected_features} columns"
        
        X = numeric_df.values.astype(np.float32)
        
        # Apply scaler if available
        if dataset in self.scalers:
            try:
                X = self.scalers[dataset].transform(X)
                info['scaled'] = True
            except Exception as e:
                info['scaling_error'] = str(e)
                info['scaled'] = False
        else:
            info['scaled'] = False
        
        return X, y, info
    
    def validate_data_shape(self, X: np.ndarray, dataset: str) -> bool:
        """
        Validate that data has correct shape for the dataset.
        
        Args:
            X: Feature array
            dataset: 'diabetes' or 'adult'
        
        Returns:
            True if shape is valid
        """
        expected_features = MODEL_CONFIGS.get(dataset, {}).get('input_size', 0)
        return X.shape[1] == expected_features


# Global data processor instance
_data_processor: Optional[DataProcessor] = None


def get_data_processor() -> DataProcessor:
    """Get the global data processor instance."""
    global _data_processor
    if _data_processor is None:
        _data_processor = DataProcessor()
    return _data_processor


def initialize_data() -> Dict[str, dict]:
    """Initialize and load all test data on startup."""
    processor = get_data_processor()
    return processor.load_test_data()
