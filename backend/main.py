import os
import sys
import json
from contextlib import asynccontextmanager
from typing import Optional, List

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.model_loader import get_model_loader, initialize_models
from services.data_processor import get_data_processor, initialize_data
from models.architectures import MODEL_CONFIGS


# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================

class ExperimentConfig(BaseModel):
    """Configuration for running an experiment."""
    dataset: str  # 'diabetes' or 'adult'
    model_type: str  # 'fnn' or 'lr'
    dp_enabled: bool = False
    epsilon: Optional[float] = None  # Required if dp_enabled is True


class FederatedExperimentConfig(BaseModel):
    """Configuration for running a federated learning experiment."""
    dataset: str  # 'diabetes' or 'adult'
    model_type: str  # 'fnn' or 'lr'
    aggregation: str  # 'FedAvg', 'FedProx', 'q-FedAvg', 'SCAFFOLD', 'FedAdam'


class ExperimentResult(BaseModel):
    """Result from running an experiment."""
    baseline_accuracy: float
    private_accuracy: Optional[float] = None
    accuracy_loss: Optional[float] = None
    f1_score: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    epsilon: Optional[float] = None
    samples_evaluated: int
    model_used: str


class FederatedExperimentResult(BaseModel):
    """Result from running a federated learning experiment."""
    accuracy: float
    baseline_accuracy: Optional[float] = None
    accuracy_loss: Optional[float] = None
    f1_score: float
    precision: float
    recall: float
    samples_evaluated: int
    model_used: str
    aggregation: str
    model_type: str
    dataset: str


class ModelInfo(BaseModel):
    """Information about an available model."""
    key: str
    dataset: str
    model_type: str
    epsilon: Optional[float] = None


class DatasetInfo(BaseModel):
    """Information about a dataset."""
    name: str
    input_size: int
    feature_names: List[str]
    has_test_data: bool
    test_samples: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    models_loaded: int
    datasets_ready: List[str]


# ============================================================================
# Application Lifecycle
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print("\n" + "="*60)
    print("🚀 Privacy Playground Backend Starting...")
    print("="*60)
    
    # Initialize models
    print("\n📦 Loading pre-trained models...")
    models_info = initialize_models()
    print(f"✓ Loaded {len(models_info)} models")
    
    # Initialize test data
    print("\n📊 Loading test data...")
    data_info = initialize_data()
    print(f"✓ Loaded test data for {len(data_info)} datasets")
    
    print("\n" + "="*60)
    print("✅ Backend ready!")
    print("="*60 + "\n")
    
    yield
    
    # Shutdown
    print("\n👋 Privacy Playground Backend shutting down...")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Privacy Playground API",
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "Privacy Playground",
        "email": "almir@example.com"
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Service health and status endpoints"
        },
        {
            "name": "Baseline",
            "description": "Standard models without privacy preservation"
        },
        {
            "name": "Differential Privacy",
            "description": "ε-differential privacy experiments with Opacus"
        },
        {
            "name": "Federated Learning",
            "description": "Decentralized training with various aggregation strategies"
        },
        {
            "name": "Comparison",
            "description": "Compare privacy methods across datasets and models"
        },
        {
            "name": "Visualizations",
            "description": "Experimental results data for interactive dashboards"
        }
    ]
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")


# ============================================================================
# Helper Functions
# ============================================================================

def evaluate_model(model: torch.nn.Module, X: np.ndarray, y: np.ndarray) -> dict:
    """
    Evaluate a model on given data.
    
    Args:
        model: PyTorch model
        X: Features (numpy array)
        y: Labels (numpy array)
    
    Returns:
        Dictionary with metrics
    """
    model.eval()
    
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X)
        outputs = model(X_tensor)
        
        # For binary classification, check output shape
        if outputs.shape[1] == 2:
            # Use softmax for 2-class output
            _, predictions = torch.max(outputs, 1)
        else:
            # Single output - use sigmoid threshold
            predictions = (torch.sigmoid(outputs) > 0.5).long().squeeze()
        
        predictions = predictions.numpy()
    
    # Debug: Check prediction distribution
    unique, counts = np.unique(predictions, return_counts=True)
    pred_dist = dict(zip(unique, counts))
    print(f"  Prediction distribution: {pred_dist}")
    
    return {
        'accuracy': accuracy_score(y, predictions) * 100,
        'f1_score': f1_score(y, predictions, average='binary', zero_division=0) * 100,
        'precision': precision_score(y, predictions, average='binary', zero_division=0) * 100,
        'recall': recall_score(y, predictions, average='binary', zero_division=0) * 100,
        'samples': len(y)
    }


def get_model_type_key(model_type: str, dp_enabled: bool) -> str:
    """Convert frontend model_type to internal key."""
    if model_type == 'fnn':
        return 'fnn_dp' if dp_enabled else 'fnn_baseline'
    elif model_type == 'lr':
        return 'lr_dp'
    else:
        raise ValueError(f"Unknown model type: {model_type}")


# ============================================================================
# API Endpoints
# ============================================================================
@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

@app.get(
    "/", 
    response_model=HealthResponse,
    tags=["Health"],
    summary="Root health check",
    description="Returns service status, number of loaded models, and ready datasets"
)
async def root():
    """Health check endpoint."""
    loader = get_model_loader()
    processor = get_data_processor()
    
    return HealthResponse(
        status="healthy",
        models_loaded=len(loader.loaded_models),
        datasets_ready=list(processor.test_data.keys())
    )


@app.get(
    "/api/health", 
    response_model=HealthResponse,
    tags=["Health"],
    summary="API health check",
    description="Returns service status including loaded models and available datasets"
)
async def health_check():
    """Health check endpoint."""
    return await root()


@app.get(
    "/api/models", 
    response_model=List[ModelInfo],
    tags=["Health"],
    summary="List available models",
    description="Returns all pre-trained models with dataset, model type, and privacy method information"
)
async def list_models():
    """List all available models."""
    loader = get_model_loader()
    models = loader.list_available_models()
    return [ModelInfo(**m) for m in models]


@app.post(
    "/api/models/reload",
    tags=["Health"],
    summary="Reload models",
    description="Hot-reload all models from disk without restarting the server. Useful for loading newly trained models."
)
async def reload_models():
    """Hot-reload all models from disk."""
    loader = get_model_loader()
    models_info = loader.reload_models()
    return {
        "status": "success",
        "models_loaded": len(models_info),
        "models": models_info
    }


@app.get(
    "/api/datasets/{dataset}", 
    response_model=DatasetInfo,
    tags=["Health"],
    summary="Get dataset information",
    description="Returns dataset details including shape, feature names, and statistics. Valid datasets: 'diabetes', 'adult'"
)
async def get_dataset_info(dataset: str):
    """Get information about a dataset."""
    if dataset not in MODEL_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not found")
    
    processor = get_data_processor()
    info = processor.get_dataset_info(dataset)
    return DatasetInfo(**info)


@app.get(
    "/api/datasets/{dataset}/epsilons",
    tags=["Differential Privacy"],
    summary="Get available epsilon values",
    description="Returns all available ε (epsilon) privacy budgets for DP models of a specific dataset. Typical values: 0.5 (strong privacy), 1.0, 3.0, 5.0, 10.0 (weak privacy)"
)
async def get_available_epsilons(dataset: str, model_type: str = "fnn"):
    """Get available epsilon values for a dataset and model type."""
    if dataset not in MODEL_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not found")
    
    loader = get_model_loader()
    model_type_key = f"{model_type}_dp"
    epsilons = loader.get_available_epsilons(dataset, model_type_key)
    
    return {
        "dataset": dataset,
        "model_type": model_type,
        "epsilons": epsilons
    }


@app.post(
    "/api/experiment", 
    response_model=ExperimentResult,
    tags=["Baseline", "Differential Privacy"],
    summary="Run experiment with local test data",
    description="""Run baseline or DP-enabled experiment using pre-loaded test data.
    
    **Supports:**
    - Baseline models (LR/FNN without privacy)
    - Differential Privacy models with ε ∈ {0.5, 1.0, 3.0, 5.0, 10.0}
    
    **Returns:**
    - Baseline metrics (accuracy, F1, precision, recall)
    - DP metrics if enabled (with accuracy loss)
    - Samples evaluated count
    """
)
async def run_experiment(config: ExperimentConfig):
    """
    Run an experiment using local test data.
    
    Compares baseline model performance with DP model (if enabled).
    """
    # Validate dataset
    if config.dataset not in MODEL_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown dataset: {config.dataset}")
    
    # Validate epsilon if DP enabled
    if config.dp_enabled and config.epsilon is None:
        raise HTTPException(status_code=400, detail="Epsilon required when DP is enabled")
    
    loader = get_model_loader()
    processor = get_data_processor()
    
    # Get test data
    test_data = processor.get_test_data(config.dataset)
    if test_data is None:
        raise HTTPException(
            status_code=500,
            detail=f"Test data not loaded for {config.dataset}. Run notebook to save test data."
        )
    
    X_test, y_test = test_data
    
    # Get baseline model - use matching model type baseline
    # FNN uses fnn_baseline, LR uses lr_baseline
    if config.model_type == 'fnn':
        baseline_type = 'fnn_baseline'
    else:  # LR
        baseline_type = 'lr_baseline'
    
    baseline_epsilon = None
    
    baseline_model = loader.get_model(config.dataset, baseline_type, baseline_epsilon)
    if baseline_model is None:
        raise HTTPException(status_code=500, detail=f"Baseline {config.model_type.upper()} model not found for {config.dataset}")
    
    # Evaluate baseline
    baseline_metrics = evaluate_model(baseline_model, X_test, y_test)
    print(f"📊 Baseline metrics: {baseline_metrics}")
    
    result = ExperimentResult(
        baseline_accuracy=baseline_metrics['accuracy'],
        f1_score=baseline_metrics['f1_score'],
        precision=baseline_metrics['precision'],
        recall=baseline_metrics['recall'],
        samples_evaluated=baseline_metrics['samples'],
        model_used=f"{config.dataset}_{baseline_type}"
    )
    
    # If DP enabled, also evaluate DP model
    if config.dp_enabled:
        model_type_key = get_model_type_key(config.model_type, True)
        dp_model = loader.get_model(config.dataset, model_type_key, config.epsilon)
        
        if dp_model is None:
            # Find closest epsilon
            epsilons = loader.get_available_epsilons(config.dataset, model_type_key)
            if not epsilons:
                raise HTTPException(
                    status_code=500,
                    detail=f"No DP models found for {config.dataset} {model_type_key}"
                )
            closest = min(epsilons, key=lambda x: abs(x - config.epsilon))
            dp_model = loader.get_model(config.dataset, model_type_key, closest)
            result.epsilon = closest
        else:
            result.epsilon = config.epsilon
        
        if dp_model:
            dp_metrics = evaluate_model(dp_model, X_test, y_test)
            print(f"🔒 DP metrics (ε={result.epsilon}): {dp_metrics}")
            
            # Check if model collapsed (predicting only one class)
            if dp_metrics['f1_score'] == 0.0 and dp_metrics['precision'] == 0.0:
                print(f"⚠️  WARNING: DP model appears to have collapsed (predicting only one class)")
                # Still return the metrics so users can see the issue
            
            result.private_accuracy = dp_metrics['accuracy']
            result.accuracy_loss = baseline_metrics['accuracy'] - dp_metrics['accuracy']
            # Update metrics to DP model's metrics (for DP run)
            result.f1_score = dp_metrics['f1_score']
            result.precision = dp_metrics['precision']
            result.recall = dp_metrics['recall']
            # Update model name to indicate DP model
            result.model_used = f"{config.dataset}_{model_type_key}_eps{result.epsilon}"
            print(f"📤 Returning DP result: baseline_acc={result.baseline_accuracy:.2f}, private_acc={result.private_accuracy:.2f}, loss={result.accuracy_loss:.2f}")
    
    return result


@app.post(
    "/api/experiment/upload", 
    response_model=ExperimentResult,
    tags=["Baseline", "Differential Privacy"],
    summary="Run experiment with uploaded data",
    description="""Upload CSV data and run baseline or DP-enabled experiment.
    
    **CSV Requirements:**
    - Diabetes: 21 feature columns (standardized)
    - Adult: 14 feature columns (preprocessed, encoded)
    - Last column must be binary target (0/1)
    
    **Supports same models as /api/experiment**
    """
)
async def run_experiment_with_upload(
    file: UploadFile = File(...),
    dataset: str = Form(...),
    model_type: str = Form("fnn"),
    dp_enabled: bool = Form(False),
    epsilon: Optional[float] = Form(None),
    target_column: Optional[str] = Form(None)
):
    """
    Run an experiment using uploaded CSV data.
    
    The CSV will be preprocessed to match the expected model input format.
    """
    # Validate inputs
    if dataset not in MODEL_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown dataset: {dataset}")
    
    if dp_enabled and epsilon is None:
        raise HTTPException(status_code=400, detail="Epsilon required when DP is enabled")
    
    # Read uploaded file
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")
    
    # Process CSV
    processor = get_data_processor()
    try:
        X, y, info = processor.process_uploaded_csv(csv_content, dataset, target_column)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    loader = get_model_loader()
    
    # Get baseline model
    baseline_type = 'fnn_baseline' if model_type == 'fnn' else 'lr_dp'
    baseline_epsilon = None if model_type == 'fnn' else 0.5
    
    baseline_model = loader.get_model(dataset, baseline_type, baseline_epsilon)
    if baseline_model is None and model_type == 'lr':
        epsilons = loader.get_available_epsilons(dataset, 'lr_dp')
        if epsilons:
            baseline_model = loader.get_model(dataset, 'lr_dp', epsilons[0])
    
    if baseline_model is None:
        raise HTTPException(status_code=500, detail=f"No baseline model found for {model_type}")
    
    # Evaluate baseline
    if y is not None:
        baseline_metrics = evaluate_model(baseline_model, X, y)
    else:
        # No target - just run inference
        baseline_model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X)
            outputs = baseline_model(X_tensor)
            _, predictions = torch.max(outputs, 1)
        
        baseline_metrics = {
            'accuracy': 0,  # Can't compute without labels
            'f1_score': 0,
            'precision': 0,
            'recall': 0,
            'samples': len(X)
        }
    
    result = ExperimentResult(
        baseline_accuracy=baseline_metrics['accuracy'],
        f1_score=baseline_metrics.get('f1_score', 0),
        precision=baseline_metrics.get('precision', 0),
        recall=baseline_metrics.get('recall', 0),
        samples_evaluated=baseline_metrics['samples'],
        model_used=f"{dataset}_{baseline_type}"
    )
    
    # If DP enabled, also evaluate DP model
    if dp_enabled and y is not None:
        model_type_key = get_model_type_key(model_type, True)
        dp_model = loader.get_model(dataset, model_type_key, epsilon)
        
        if dp_model is None:
            epsilons = loader.get_available_epsilons(dataset, model_type_key)
            if epsilons:
                closest = min(epsilons, key=lambda x: abs(x - epsilon))
                dp_model = loader.get_model(dataset, model_type_key, closest)
                result.epsilon = closest
        else:
            result.epsilon = epsilon
        
        if dp_model:
            dp_metrics = evaluate_model(dp_model, X, y)
            result.private_accuracy = dp_metrics['accuracy']
            result.accuracy_loss = baseline_metrics['accuracy'] - dp_metrics['accuracy']
            result.f1_score = dp_metrics['f1_score']
            result.precision = dp_metrics['precision']
            result.recall = dp_metrics['recall']
            result.model_used = f"{dataset}_{model_type_key}_eps{result.epsilon}"
    
    return result


@app.get(
    "/api/fl/aggregations",
    tags=["Federated Learning"],
    summary="List FL aggregation methods",
    description="Returns all available federated learning aggregation strategies with descriptions"
)
async def get_available_aggregations():
    """Get list of available FL aggregation methods."""
    return {
        "aggregations": [
            {
                "value": "FedAvg",
                "label": "FedAvg",
                "description": "Federated Averaging - Classic weighted average based on client data sizes"
            },
            {
                "value": "FedProx",
                "label": "FedProx",
                "description": "Federated Proximal - Adds proximal term for heterogeneous client data"
            },
            {
                "value": "q-FedAvg",
                "label": "q-FedAvg",
                "description": "Fairness-weighted aggregation using Lipschitz constants"
            },
            {
                "value": "SCAFFOLD",
                "label": "SCAFFOLD",
                "description": "Control variates approach to handle client drift"
            },
            {
                "value": "FedAdam",
                "label": "FedAdam",
                "description": "Adaptive federated optimization with momentum and adaptive learning rates"
            }
        ]
    }


@app.get(
    "/api/fl/models",
    tags=["Federated Learning"],
    summary="List trained FL models",
    description="Returns all trained federated learning models grouped by dataset, model type, and aggregation method"
)
async def list_fl_models():
    """List all available federated learning models."""
    loader = get_model_loader()
    all_models = loader.list_available_models()
    
    # Filter for FL models only
    fl_models = [
        m for m in all_models 
        if m.get('model_type', '').startswith('fl_')
    ]
    
    # Group by dataset and model type
    grouped = {}
    for model in fl_models:
        dataset = model['dataset']
        model_type = model['model_type'].replace('fl_', '').upper()
        
        if dataset not in grouped:
            grouped[dataset] = {}
        if model_type not in grouped[dataset]:
            grouped[dataset][model_type] = []
        
        grouped[dataset][model_type].append({
            'aggregation': model.get('aggregation', 'Unknown'),
            'key': model['key']
        })
    
    return {
        "models": grouped,
        "total_count": len(fl_models)
    }


@app.post(
    "/api/fl/experiment", 
    response_model=FederatedExperimentResult,
    tags=["Federated Learning"],
    summary="Run federated learning experiment",
    description="""Evaluate trained FL model against centralized baseline.
    
    **Aggregation Methods:**
    - FedAvg: Standard averaging
    - FedProx: Proximal term regularization (μ=0.01)
    - q-FedAvg: q-fair aggregation (q=0.5)
    - SCAFFOLD: Control variates correction
    - FedAdam: Server-side Adam optimization
    
    **Architecture:**
    - 5 clients with IID data split
    - 20 global communication rounds
    - 5 local epochs per round
    """
)
async def run_federated_experiment(config: FederatedExperimentConfig):
    """
    Run a federated learning experiment using a trained FL model.
    Compares FL model performance against centralized baseline.
    """
    # Validate dataset
    if config.dataset not in MODEL_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unknown dataset: {config.dataset}")
    
    # Validate aggregation method
    valid_aggs = ["FedAvg", "FedProx", "q-FedAvg", "SCAFFOLD", "FedAdam"]
    if config.aggregation not in valid_aggs:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown aggregation: {config.aggregation}. Valid: {valid_aggs}"
        )
    
    loader = get_model_loader()
    processor = get_data_processor()
    
    # Get test data
    test_data = processor.get_test_data(config.dataset)
    if test_data is None:
        raise HTTPException(
            status_code=500,
            detail=f"Test data not loaded for {config.dataset}. Run notebook to save test data."
        )
    
    X_test, y_test = test_data
    
    # Get baseline model - use matching model type baseline
    if config.model_type == 'fnn':
        baseline_type = 'fnn_baseline'
    else:  # LR
        baseline_type = 'lr_baseline'
    
    baseline_model = loader.get_model(config.dataset, baseline_type, None)
    if baseline_model is None:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline {config.model_type.upper()} model not found for {config.dataset}"
        )
    
    # Evaluate baseline
    baseline_metrics = evaluate_model(baseline_model, X_test, y_test)
    print(f"📊 Baseline {config.model_type.upper()} metrics: {baseline_metrics}")
    
    # Get FL model
    fl_model_type = f"fl_{config.model_type}"
    fl_model = loader.get_model(config.dataset, fl_model_type, aggregation=config.aggregation)
    
    if fl_model is None:
        raise HTTPException(
            status_code=404,
            detail=f"FL model not found: {config.dataset}/{config.model_type}/{config.aggregation}"
        )
    
    # Evaluate FL model
    print(f"🔗 Evaluating FL model: {config.dataset}/{config.model_type}/{config.aggregation}")
    fl_metrics = evaluate_model(fl_model, X_test, y_test)
    
    # Calculate accuracy loss
    accuracy_loss = baseline_metrics['accuracy'] - fl_metrics['accuracy']
    
    print(f"📤 FL Result: baseline={baseline_metrics['accuracy']:.4f}, fl={fl_metrics['accuracy']:.4f}, loss={accuracy_loss:.4f}")
    
    return FederatedExperimentResult(
        accuracy=fl_metrics['accuracy'],
        baseline_accuracy=baseline_metrics['accuracy'],
        accuracy_loss=accuracy_loss,
        f1_score=fl_metrics['f1_score'],
        precision=fl_metrics['precision'],
        recall=fl_metrics['recall'],
        samples_evaluated=fl_metrics['samples'],
        model_used=f"{config.dataset}_{fl_model_type}_{config.aggregation}",
        aggregation=config.aggregation,
        model_type=config.model_type,
        dataset=config.dataset
    )


# ============================================================================
# Visualization Data Endpoints
# ============================================================================

@app.get(
    "/api/visualizations/dp-results",
    tags=["Visualizations"],
    summary="Get DP experiment results",
    description="""Returns all Differential Privacy experimental results for visualization.
    
    **Data includes:**
    - 10 configs (2 models × 5 ε values)
    - 25 evaluations per config (5 seeds × 5 folds)
    - Accuracy, F1, precision, recall metrics
    - Privacy budget (ε) and noise parameters
    
    **Source files:**
    - models_research_dp_continue/dp_continue_results.json
    - models_dp_adult/adult_dp_results.json
    """
)
async def get_dp_visualization_data():
    """
    Get all DP results formatted for interactive visualization.
    Loads from saved JSON files in models_research_dp_continue/ and models_dp_adult/.
    """
    import glob
    results = []
    
    # Search for DP result files
    dp_dirs = [
        "models_research_dp_continue",
        "models_dp_adult"
    ]
    
    for dp_dir in dp_dirs:
        json_files = glob.glob(f"{dp_dir}/*results.json")
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    
                # Extract DP results
                if 'differential_privacy' in data:
                    for config_key, config_data in data['differential_privacy'].items():
                        if 'accuracy' in config_data and isinstance(config_data['accuracy'], dict):
                            results.append({
                                'dataset': config_data.get('dataset', 'unknown'),
                                'model': config_data.get('model', 'unknown'),
                                'epsilon': config_data.get('target_epsilon', 0),
                                'accuracy': config_data['accuracy']['mean'] * 100,
                                'std': config_data['accuracy']['std'] * 100,
                                'baseline': data.get('baseline_reference', {}).get(
                                    f"{config_data['dataset']}_{config_data['model']}", {}
                                ).get('accuracy', 0) * 100,
                                'accuracyLoss': (
                                    data.get('baseline_reference', {}).get(
                                        f"{config_data['dataset']}_{config_data['model']}", {}
                                    ).get('accuracy', 0) - config_data['accuracy']['mean']
                                ) * 100
                            })
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue
    
    return {"data": results, "count": len(results)}


@app.get(
    "/api/visualizations/fl-results",
    tags=["Visualizations"],
    summary="Get FL experiment results",
    description="""Returns all Federated Learning experimental results for visualization.
    
    **Data includes:**
    - 20 configs (2 datasets × 2 models × 5 aggregations)
    - 25 evaluations per config (5 seeds × 5 folds)
    - Centralized vs. federated accuracy comparison
    - Communication rounds and client performance
    
    **Aggregation methods:**
    FedAvg, FedProx, q-FedAvg, SCAFFOLD, FedAdam
    
    **Source files:**
    - models_fl_adult/fl_adult_results.json
    - models_fl_diabetes/fl_diabetes_results.json
    """
)
async def get_fl_visualization_data():
    """
    Get all FL results formatted for interactive visualization.
    Loads from saved JSON files in models_fl_adult/ and models_fl_diabetes/.
    """
    import glob
    results = []
    
    # Search for FL result files
    fl_dirs = [
        "models_fl_adult",
        "models_fl_diabetes",
        "models_fl_continue"
    ]
    
    for fl_dir in fl_dirs:
        json_files = glob.glob(f"{fl_dir}/*results.json")
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    
                # Extract FL results
                if 'federated_learning' in data:
                    for config_key, config_data in data['federated_learning'].items():
                        if 'accuracy' in config_data and isinstance(config_data['accuracy'], dict):
                            dataset_key = f"{config_data['dataset']}_{config_data['model']}"
                            baseline_acc = 0
                            
                            # Try to get baseline from the same file
                            if 'baseline_reference' in data and dataset_key in data['baseline_reference']:
                                baseline_acc = data['baseline_reference'][dataset_key].get('accuracy', 0) * 100
                            
                            results.append({
                                'dataset': config_data.get('dataset', 'unknown'),
                                'model': config_data.get('model', 'unknown'),
                                'aggregation': config_data.get('aggregation', 'unknown'),
                                'accuracy': config_data['accuracy']['mean'] * 100,
                                'std': config_data['accuracy']['std'] * 100,
                                'baseline': baseline_acc
                            })
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue
    
    return {"data": results, "count": len(results)}


@app.get(
    "/api/visualizations/baseline-results",
    tags=["Visualizations"],
    summary="Get baseline experiment results",
    description="""Returns all baseline (no privacy) experimental results for visualization.
    
    **Data includes:**
    - 4 configs (2 datasets × 2 models)
    - 25 evaluations per config (5 seeds × 5 folds)
    - Standard centralized training metrics
    - Used as comparison baseline for DP/FL methods
    
    **Source file:**
    - models_research/research_results.json
    """
)
async def get_baseline_visualization_data():
    """
    Get baseline results for comparison.
    Loads from models_research/research_results.json.
    """
    import glob
    results = []
    
    try:
        # Corrected path for research_results.json
        baseline_file = os.path.join("models", "models_research", "research_results.json")
        with open(baseline_file, 'r') as f:
            data = json.load(f)
            
            if 'baseline_results' in data:
                for dataset, models in data['baseline_results'].items():
                    for model, metrics in models.items():
                        if 'accuracy' in metrics:
                            results.append({
                                'dataset': dataset,
                                'model': model,
                                'accuracy': metrics['accuracy']['mean'] * 100,
                                'std': metrics['accuracy']['std'] * 100 if 'std' in metrics['accuracy'] else 0,
                                'f1': metrics.get('f1', {}).get('mean', 0) * 100
                            })
    except Exception as e:
        print(f"Error loading baseline results: {e}")
    
    return {"data": results, "count": len(results)}


@app.get(
    "/api/visualizations/all",
    tags=["Visualizations"],
    summary="Get all experiment results",
    description="""Returns combined results from all privacy methods (Baseline, DP, FL) in a single response.
    
    **Total experiments:**
    - ~1,100 cross-validated evaluations
    - 34 unique configurations
    - 2 datasets (Diabetes, Adult)
    - 2 models (LR, FNN)
    - 3 privacy methods (None, DP, FL)
    
    **Perfect for:**
    - Interactive dashboards
    - Comprehensive privacy-accuracy tradeoff analysis
    - Method comparison visualizations
    """
)
async def get_all_visualization_data():
    """
    Get all visualization data (DP, FL, Baseline) in one call.
    """
    dp_data = await get_dp_visualization_data()
    fl_data = await get_fl_visualization_data()
    baseline_data = await get_baseline_visualization_data()
    
    return {
        "dp": dp_data["data"],
        "fl": fl_data["data"],
        "baseline": baseline_data["data"],
        "counts": {
            "dp": dp_data["count"],
            "fl": fl_data["count"],
            "baseline": baseline_data["count"]
        }
    }


# ============================================================================
# Run with: uvicorn main:app --reload --port 8000
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
