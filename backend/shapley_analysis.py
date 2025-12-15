"""
Shapley Value Analysis for Baseline Models

This script performs SHAP (SHapley Additive exPlanations) analysis on the baseline
models to understand feature importance and model interpretability.

Usage:
    python shapley_analysis.py --dataset diabetes --model_type fnn
    python shapley_analysis.py --dataset adult --model_type lr
    python shapley_analysis.py --all  # Analyze all baseline models
"""

import os
import sys
import argparse
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
import shap

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.architectures import MODEL_CONFIGS, FeedforwardNN, FeedforwardNN_Simple, LogisticRegressionModel
from services.data_processor import DataProcessor

warnings.filterwarnings('ignore')


class ShapleyAnalyzer:
    """
    Performs SHAP analysis on trained PyTorch models.
    """
    
    def __init__(self, data_dir: str = None, models_dir: str = None, output_dir: str = None):
        """
        Initialize the Shapley Analyzer.
        
        Args:
            data_dir: Directory containing test data and preprocessors
            models_dir: Directory containing trained model files
            output_dir: Directory to save analysis results and plots
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if models_dir is None:
            models_dir = os.path.join(os.path.dirname(__file__), 'models')
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), 'shapley_results')
        
        self.data_dir = data_dir
        self.models_dir = models_dir
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize data processor
        self.data_processor = DataProcessor(data_dir)
        self.data_processor.load_test_data()
        
        print(f"[OK] Initialized Shapley Analyzer")
        print(f"  Data dir: {data_dir}")
        print(f"  Models dir: {models_dir}")
        print(f"  Output dir: {output_dir}")
    
    def load_model(self, dataset: str, model_type: str, baseline: bool = True):
        """
        Load a trained model from disk.
        
        Args:
            dataset: 'diabetes' or 'adult'
            model_type: 'fnn' or 'lr'
            baseline: If True, load baseline model; otherwise load DP model
        
        Returns:
            Loaded PyTorch model
        """
        # Get model config
        config = MODEL_CONFIGS.get(dataset)
        if config is None:
            raise ValueError(f"Unknown dataset: {dataset}")
        
        input_size = config['input_size']
        
        # Create model architecture
        if model_type == 'fnn':
            model = FeedforwardNN_Simple(input_size=input_size, hidden_sizes=[128, 64], output_size=2)
        elif model_type == 'lr':
            model = LogisticRegressionModel(input_size=input_size, output_size=2)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Find baseline model file
        if baseline:
            pattern = f"{dataset}_{model_type}_baseline_*.pth"
        else:
            pattern = f"{dataset}_{model_type}_dp_*.pth"
        
        # Search for model file
        model_files = list(Path(self.models_dir).glob(pattern))
        if not model_files:
            raise FileNotFoundError(f"No model found matching pattern: {pattern}")
        
        # Use the most recent model
        model_file = sorted(model_files)[-1]
        
        # Load model weights
        checkpoint = torch.load(model_file, map_location='cpu')
        
        # Handle different checkpoint formats
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            # Checkpoint contains metadata and state dict
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            # Direct state dict
            model.load_state_dict(checkpoint)
        
        model.eval()
        
        print(f"[OK] Loaded model: {model_file.name}")
        return model, model_file.name
    
    def create_prediction_function(self, model):
        """
        Create a prediction function compatible with SHAP.
        
        Args:
            model: PyTorch model
        
        Returns:
            Function that takes numpy array and returns predictions
        """
        def predict(X):
            """Predict probabilities for input data (class 1 only for binary classification)."""
            if not isinstance(X, torch.Tensor):
                X = torch.FloatTensor(X)
            
            with torch.no_grad():
                logits = model(X)
                probs = torch.softmax(logits, dim=1)
            
            # For binary classification, return only class 1 probability
            # This prevents SHAP from computing values for both classes
            return probs[:, 1].numpy()
        
        return predict
    
    def analyze_model(self, dataset: str, model_type: str, num_samples: int = 100):
        """
        Perform SHAP analysis on a specific model.
        
        Args:
            dataset: 'diabetes' or 'adult'
            model_type: 'fnn' or 'lr'
            num_samples: Number of background samples for SHAP explainer
        
        Returns:
            Dictionary containing SHAP values and analysis results
        """
        print(f"\n{'='*80}")
        print(f"Analyzing {dataset.upper()} - {model_type.upper()} (Baseline)")
        print(f"{'='*80}")
        
        # Load model
        model, model_name = self.load_model(dataset, model_type, baseline=True)
        
        # Get test data
        test_data = self.data_processor.get_test_data(dataset)
        if test_data is None:
            raise ValueError(f"No test data available for {dataset}")
        
        X_test, y_test = test_data
        
        # Get feature names
        feature_names = self.data_processor.feature_names.get(dataset)
        if feature_names is None:
            feature_names = [f"Feature_{i}" for i in range(X_test.shape[1])]
        
        print(f"[OK] Test data shape: {X_test.shape}")
        print(f"[OK] Number of features: {len(feature_names)}")
        
        # Create prediction function
        predict_fn = self.create_prediction_function(model)
        
        # Sample background data for SHAP
        background_indices = np.random.choice(len(X_test), size=min(num_samples, len(X_test)), replace=False)
        background_data = X_test[background_indices]
        
        print(f"[OK] Creating SHAP explainer with {len(background_data)} background samples...")
        
        # Create SHAP explainer (using KernelExplainer for model-agnostic approach)
        explainer = shap.KernelExplainer(predict_fn, background_data)
        
        # Select samples to explain (use a subset for efficiency)
        explain_indices = np.random.choice(len(X_test), size=min(100, len(X_test)), replace=False)
        X_explain = X_test[explain_indices]
        
        print(f"[OK] Computing SHAP values for {len(X_explain)} samples...")
        print("  (This may take a few minutes...)")
        
        # Compute SHAP values
        shap_values = explainer.shap_values(X_explain)
        
        # Since we're predicting only class 1 probability, shap_values is already 1D per sample
        print(f"[OK] SHAP values computed successfully")
        
        # Create output directory for this model
        model_output_dir = os.path.join(self.output_dir, f"{dataset}_{model_type}")
        os.makedirs(model_output_dir, exist_ok=True)
        
        # Generate visualizations
        self._create_visualizations(
            shap_values, 
            X_explain, 
            feature_names, 
            model_output_dir,
            f"{dataset}_{model_type}"
        )
        
        # Calculate feature importance
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': mean_abs_shap
        }).sort_values('importance', ascending=False)
        
        # Save feature importance
        importance_file = os.path.join(model_output_dir, 'feature_importance.csv')
        feature_importance.to_csv(importance_file, index=False)
        print(f"[OK] Saved feature importance to: {importance_file}")
        
        # Display top features
        print(f"\nTop 10 Most Important Features:")
        print(feature_importance.head(10).to_string(index=False))
        
        # Save SHAP values
        shap_file = os.path.join(model_output_dir, 'shap_values.npz')
        np.savez(
            shap_file,
            shap_values=shap_values,
            X_explain=X_explain,
            feature_names=feature_names
        )
        print(f"[OK] Saved SHAP values to: {shap_file}")
        
        return {
            'shap_values': shap_values,
            'X_explain': X_explain,
            'feature_names': feature_names,
            'feature_importance': feature_importance,
            'model_name': model_name,
            'output_dir': model_output_dir
        }
    
    def _create_visualizations(self, shap_values, X_explain, feature_names, output_dir, model_id):
        """
        Create and save SHAP visualizations.
        
        Args:
            shap_values: SHAP values array
            X_explain: Input data for explained samples
            feature_names: List of feature names
            output_dir: Directory to save plots
            model_id: Model identifier for plot titles
        """
        print(f"\n[OK] Creating visualizations...")
        
        # 1. Summary Plot (Feature Importance)
        plt.figure(figsize=(10, 8))
        shap.summary_plot(shap_values, X_explain, feature_names=feature_names, show=False)
        plt.title(f'SHAP Summary Plot - {model_id}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        summary_file = os.path.join(output_dir, 'shap_summary.png')
        plt.savefig(summary_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  -> Saved summary plot: {summary_file}")
        
        # 2. Bar Plot (Mean Absolute SHAP Values)
        plt.figure(figsize=(10, 8))
        shap.summary_plot(shap_values, X_explain, feature_names=feature_names, plot_type='bar', show=False)
        plt.title(f'Feature Importance (Mean |SHAP|) - {model_id}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        bar_file = os.path.join(output_dir, 'shap_bar.png')
        plt.savefig(bar_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  -> Saved bar plot: {bar_file}")
        
        # 3. Waterfall plot for first sample
        plt.figure(figsize=(10, 8))
        # Get the expected value (base value) - use mean of SHAP values across samples
        expected_value = np.mean(np.sum(shap_values, axis=1))
        
        shap.plots.waterfall(
            shap.Explanation(
                values=shap_values[0],
                base_values=expected_value,
                data=X_explain[0],
                feature_names=feature_names
            ),
            show=False
        )
        plt.title(f'SHAP Waterfall Plot (Sample 1) - {model_id}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        waterfall_file = os.path.join(output_dir, 'shap_waterfall_sample1.png')
        plt.savefig(waterfall_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  -> Saved waterfall plot: {waterfall_file}")
        
        # 4. Force plot for first sample (save as image)
        try:
            force_plot = shap.force_plot(
                expected_value,
                shap_values[0],
                X_explain[0],
                feature_names=feature_names,
                show=False,
                matplotlib=True
            )
            force_file = os.path.join(output_dir, 'shap_force_sample1.png')
            plt.savefig(force_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"  -> Saved force plot: {force_file}")
        except Exception as e:
            print(f"  [WARN] Could not create force plot: {e}")
        
        print(f"[OK] All visualizations saved to: {output_dir}")
    
    def analyze_all_baseline_models(self):
        """
        Analyze all baseline models (diabetes and adult, FNN and LR).
        """
        datasets = ['diabetes', 'adult']
        model_types = ['fnn', 'lr']
        
        results = {}
        
        for dataset in datasets:
            for model_type in model_types:
                try:
                    result = self.analyze_model(dataset, model_type)
                    results[f"{dataset}_{model_type}"] = result
                except Exception as e:
                    print(f"\n[ERROR] Error analyzing {dataset} {model_type}: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Create summary report
        self._create_summary_report(results)
        
        return results
    
    def _create_summary_report(self, results):
        """
        Create a summary report comparing all models.
        
        Args:
            results: Dictionary of analysis results for each model
        """
        print(f"\n{'='*80}")
        print("SUMMARY REPORT - Feature Importance Across Models")
        print(f"{'='*80}")
        
        summary_file = os.path.join(self.output_dir, 'summary_report.txt')
        
        with open(summary_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("SHAPLEY ANALYSIS SUMMARY REPORT\n")
            f.write("="*80 + "\n\n")
            
            for model_id, result in results.items():
                f.write(f"\n{model_id.upper()}\n")
                f.write("-" * 40 + "\n")
                f.write(f"Model: {result['model_name']}\n")
                f.write(f"Top 5 Features:\n")
                f.write(result['feature_importance'].head(5).to_string(index=False))
                f.write("\n\n")
                
                # Also print to console
                print(f"\n{model_id.upper()}")
                print("-" * 40)
                print(f"Top 5 Features:")
                print(result['feature_importance'].head(5).to_string(index=False))
        
        print(f"\n[OK] Summary report saved to: {summary_file}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Perform SHAP analysis on baseline models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze specific model
  python shapley_analysis.py --dataset diabetes --model_type fnn
  
  # Analyze all baseline models
  python shapley_analysis.py --all
  
  # Specify custom output directory
  python shapley_analysis.py --all --output_dir ./my_shap_results
        """
    )
    
    parser.add_argument('--dataset', type=str, choices=['diabetes', 'adult'],
                        help='Dataset to analyze (diabetes or adult)')
    parser.add_argument('--model_type', type=str, choices=['fnn', 'lr'],
                        help='Model type to analyze (fnn or lr)')
    parser.add_argument('--all', action='store_true',
                        help='Analyze all baseline models')
    parser.add_argument('--num_samples', type=int, default=100,
                        help='Number of background samples for SHAP (default: 100)')
    parser.add_argument('--output_dir', type=str, default=None,
                        help='Output directory for results (default: ./shapley_results)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.all and (not args.dataset or not args.model_type):
        parser.error("Either --all or both --dataset and --model_type must be specified")
    
    # Initialize analyzer
    analyzer = ShapleyAnalyzer(output_dir=args.output_dir)
    
    # Run analysis
    if args.all:
        print("\nAnalyzing all baseline models...")
        results = analyzer.analyze_all_baseline_models()
    else:
        print(f"\nAnalyzing {args.dataset} - {args.model_type}...")
        result = analyzer.analyze_model(args.dataset, args.model_type, num_samples=args.num_samples)
        results = {f"{args.dataset}_{args.model_type}": result}
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE!")
    print(f"{'='*80}")
    print(f"Results saved to: {analyzer.output_dir}")
    print("\nGenerated files:")
    print("  - Feature importance CSV files")
    print("  - SHAP summary plots")
    print("  - SHAP bar plots")
    print("  - Waterfall plots")
    print("  - Force plots")
    print("  - Summary report")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
