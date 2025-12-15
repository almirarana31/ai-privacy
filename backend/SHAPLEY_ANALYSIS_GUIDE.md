# Shapley Value Analysis Guide

This guide explains how to conduct SHAP (SHapley Additive exPlanations) analysis on your baseline models to understand feature importance and model interpretability.

## Overview

The `shapley_analysis.py` script performs comprehensive SHAP analysis on your trained baseline models (both diabetes and adult datasets, FNN and LR models).

## What is SHAP?

SHAP (SHapley Additive exPlanations) is a unified approach to explain the output of machine learning models. It uses game theory (Shapley values) to compute the contribution of each feature to the model's predictions.

### Why Use SHAP?

- **Feature Importance**: Understand which features matter most
- **Model Interpretability**: Explain individual predictions
- **Trust & Transparency**: Make your AI models more explainable
- **Debugging**: Identify potential biases or unexpected feature dependencies

## Installation

First, install the required dependencies:

```bash
pip install -r requirements.txt
```

This will install:
- `shap>=0.43.0` - For Shapley value computation
- `matplotlib>=3.7.0` - For visualizations

## Usage

### Analyze a Specific Model

To analyze a single baseline model:

```bash
# Analyze diabetes FNN baseline model
python shapley_analysis.py --dataset diabetes --model_type fnn

# Analyze adult LR baseline model
python shapley_analysis.py --dataset adult --model_type lr
```

### Analyze All Baseline Models

To analyze all baseline models at once (recommended):

```bash
python shapley_analysis.py --all
```

### Advanced Options

```bash
# Specify custom output directory
python shapley_analysis.py --all --output_dir ./my_shap_results

# Use more background samples (slower but more accurate)
python shapley_analysis.py --dataset diabetes --model_type fnn --num_samples 200
```

## Output Files

The analysis creates the following files in the `shapley_results/` directory:

### For Each Model (e.g., `shapley_results/diabetes_fnn/`):

1. **`feature_importance.csv`**
   - CSV file with features ranked by importance
   - Contains mean absolute SHAP values for each feature

2. **`shap_summary.png`**
   - Beeswarm plot showing feature importance and impact direction
   - Each dot represents a sample
   - Color indicates feature value (red = high, blue = low)

3. **`shap_bar.png`**
   - Bar chart showing mean absolute SHAP values
   - Quick overview of feature importance

4. **`shap_waterfall_sample1.png`**
   - Waterfall plot for first test sample
   - Shows how each feature contributes to the prediction

5. **`shap_force_sample1.png`**
   - Force plot for first test sample
   - Visual representation of feature contributions

6. **`shap_values.npz`**
   - NumPy archive containing raw SHAP values
   - Can be loaded for further custom analysis

### Summary Report

- **`summary_report.txt`**
  - Text file comparing top features across all models
  - Quick reference for cross-model comparison

## Interpreting the Results

### Summary Plot (Beeswarm)

- **Y-axis**: Features ranked by importance (top to bottom)
- **X-axis**: SHAP value (impact on model output)
- **Color**: Feature value
  - Red = High feature value
  - Blue = Low feature value
- **Interpretation**: 
  - Features at the top are most important
  - Red dots on the right mean high values increase the prediction
  - Blue dots on the left mean low values decrease the prediction

### Bar Plot

- Simple ranking of features by mean absolute SHAP value
- Higher bars = more important features

### Waterfall Plot

- Shows a single prediction broken down by feature contributions
- Base value (expected model output) + feature contributions = final prediction
- Features pushing prediction up are shown in red
- Features pushing prediction down are shown in blue

### Force Plot

- Similar to waterfall but horizontal layout
- Shows which features push prediction higher (red) or lower (blue)

## Example Workflow

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run analysis on all models**:
   ```bash
   python shapley_analysis.py --all
   ```

3. **Review results**:
   - Check `shapley_results/summary_report.txt` for quick overview
   - Examine individual plots for each model
   - Load `feature_importance.csv` files for detailed rankings

4. **Interpret findings**:
   - Compare feature importance across models
   - Identify consistent important features
   - Look for unexpected feature dependencies

## Technical Details

### SHAP Explainer Used

The script uses **KernelExplainer**, which is:
- **Model-agnostic**: Works with any model (PyTorch, scikit-learn, etc.)
- **Theoretically grounded**: Based on Shapley values from game theory
- **Accurate**: Provides exact explanations (with enough samples)

### Computational Considerations

- **Background samples**: Default is 100 (can be increased for accuracy)
- **Explain samples**: Default is 100 random test samples
- **Runtime**: 
  - Single model: ~2-5 minutes
  - All models: ~10-20 minutes
- **Memory**: Moderate (should work on 8GB RAM)

### Customization

You can modify the script to:
- Change the number of samples explained
- Use different SHAP explainers (e.g., DeepExplainer for neural networks)
- Create additional visualizations
- Perform SHAP analysis on DP models (not just baseline)

## Troubleshooting

### "No module named 'shap'"
Run: `pip install -r requirements.txt`

### "No model found matching pattern"
Ensure you have trained baseline models in the `models/` directory with the expected naming pattern (e.g., `diabetes_fnn_baseline_*.pth`)

### "No test data available"
Ensure test data files exist in `data/` directory:
- `diabetes_X_test.npy`, `diabetes_y_test.npy`
- `adult_X_test.npy`, `adult_y_test.npy`

### Analysis is very slow
- Reduce `--num_samples` (e.g., `--num_samples 50`)
- Analyze one model at a time instead of using `--all`

## Next Steps

After analyzing your baseline models, you can:

1. **Compare with DP models**: Modify the script to analyze DP models and compare feature importance
2. **Identify biases**: Look for features that shouldn't be important
3. **Feature engineering**: Use insights to create better features
4. **Model debugging**: Understand why certain predictions are made
5. **Documentation**: Use SHAP plots in reports and presentations

## References

- [SHAP Documentation](https://shap.readthedocs.io/)
- [SHAP Paper (NeurIPS 2017)](https://papers.nips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html)
- [Interpretable ML Book](https://christophm.github.io/interpretable-ml-book/)

## Support

For issues or questions about the Shapley analysis, please check:
1. This README
2. The script's help: `python shapley_analysis.py --help`
3. SHAP documentation: https://shap.readthedocs.io/
