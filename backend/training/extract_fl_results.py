import torch
import os
import glob
import pandas as pd
import numpy as np
from scipy import stats

# Paths
models_dir = r'c:\Users\almir\ai-privacy\backend\models'

# Load baseline results
print("="*80)
print("LOADING BASELINE MODELS")
print("="*80)

baseline_files = glob.glob(os.path.join(models_dir, '*_baseline_*.pth'))
baselines = {}

for f in baseline_files:
    checkpoint = torch.load(f, weights_only=False, map_location='cpu')
    dataset = checkpoint['training_config']['dataset']
    model_type = checkpoint['model_type']
    accuracy = checkpoint['results']['final_accuracy']
    f1 = checkpoint['results']['final_f1_score']
    
    key = f"{dataset}_{model_type}"
    baselines[key] = {'accuracy': accuracy, 'f1': f1}
    print(f"{key}: Accuracy={accuracy:.4f}, F1={f1:.4f}")

# Load FL results
print("\n" + "="*80)
print("LOADING FL MODELS")
print("="*80)

fl_files = glob.glob(os.path.join(models_dir, 'fl_*.pth'))
fl_results = []

for f in fl_files:
    try:
        checkpoint = torch.load(f, weights_only=False, map_location='cpu')
        
        dataset = checkpoint['training_config']['dataset']
        model_type = checkpoint['model_type']
        agg_method = checkpoint['training_config']['aggregation_method']
        accuracy = checkpoint['results']['final_accuracy']
        f1_score = checkpoint['results']['final_f1_score']
        
        # Get baseline for comparison
        baseline_key = f"{dataset}_{model_type}"
        if baseline_key in baselines:
            baseline_acc = baselines[baseline_key]['accuracy']
            accuracy_loss = baseline_acc - accuracy
        else:
            baseline_acc = None
            accuracy_loss = None
        
        fl_results.append({
            'Dataset': dataset,
            'Model': model_type,
            'Aggregation': agg_method,
            'Accuracy': accuracy,
            'F1-Score': f1_score,
            'Baseline_Acc': baseline_acc,
            'Accuracy_Loss': accuracy_loss
        })
    except Exception as e:
        print(f"Error loading {os.path.basename(f)}: {e}")

# Create DataFrame
df = pd.DataFrame(fl_results)

# Sort by dataset, model, aggregation
df = df.sort_values(['Dataset', 'Model', 'Aggregation'])

# Calculate statistics per configuration
print("\n" + "="*80)
print("FL RESULTS SUMMARY")
print("="*80)

grouped = df.groupby(['Dataset', 'Model', 'Aggregation']).agg({
    'Accuracy': ['mean', 'std', 'count'],
    'F1-Score': ['mean', 'std'],
    'Accuracy_Loss': ['mean']
}).reset_index()

# Flatten column names
grouped.columns = ['Dataset', 'Model', 'Aggregation', 'Acc_Mean', 'Acc_Std', 'Count', 'F1_Mean', 'F1_Std', 'AccLoss_Mean']

print("\n" + grouped.to_string(index=False))

# Display with baselines
print("\n" + "="*80)
print("DETAILED COMPARISON WITH BASELINES")
print("="*80)

for _, row in grouped.iterrows():
    baseline_key = f"{row['Dataset']}_{row['Model']}"
    if baseline_key in baselines:
        baseline_acc = baselines[baseline_key]['accuracy']
        print(f"\n{row['Dataset'].upper()} - {row['Model']} - {row['Aggregation']}")
        print(f"  FL Accuracy: {row['Acc_Mean']:.4f} ± {row['Acc_Std']:.4f}")
        print(f"  Baseline: {baseline_acc:.4f}")
        print(f"  Loss: {row['AccLoss_Mean']:.4f}")

print("\n" + "="*80)
print(f"Total FL models analyzed: {len(fl_results)}")
print(f"Unique configurations: {len(grouped)}")
print("="*80)
