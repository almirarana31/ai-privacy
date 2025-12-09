"""
Privacy Playground Backend - FastAPI Application

Provides REST API endpoints for:
- Running experiments on pre-trained models
- Evaluating models on local test data or uploaded CSV
- Listing available models and configurations
- Hot-reloading models
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Optional, List

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
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
    description="Backend API for testing pre-trained models with differential privacy",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    loader = get_model_loader()
    processor = get_data_processor()
    
    return HealthResponse(
        status="healthy",
        models_loaded=len(loader.loaded_models),
        datasets_ready=list(processor.test_data.keys())
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return await root()


@app.get("/api/models", response_model=List[ModelInfo])
async def list_models():
    """List all available models."""
    loader = get_model_loader()
    models = loader.list_available_models()
    return [ModelInfo(**m) for m in models]


@app.post("/api/models/reload")
async def reload_models():
    """Hot-reload all models from disk."""
    loader = get_model_loader()
    models_info = loader.reload_models()
    return {
        "status": "success",
        "models_loaded": len(models_info),
        "models": models_info
    }


@app.get("/api/datasets/{dataset}", response_model=DatasetInfo)
async def get_dataset_info(dataset: str):
    """Get information about a dataset."""
    if dataset not in MODEL_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not found")
    
    processor = get_data_processor()
    info = processor.get_dataset_info(dataset)
    return DatasetInfo(**info)


@app.get("/api/datasets/{dataset}/epsilons")
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


@app.post("/api/experiment", response_model=ExperimentResult)
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
    
    # Get baseline model
    baseline_type = 'fnn_baseline' if config.model_type == 'fnn' else 'lr_dp'
    baseline_epsilon = None if config.model_type == 'fnn' else 0.5  # Use lowest epsilon for LR baseline
    
    baseline_model = loader.get_model(config.dataset, baseline_type, baseline_epsilon)
    if baseline_model is None:
        # Try to find any baseline
        if config.model_type == 'fnn':
            raise HTTPException(status_code=500, detail="Baseline FNN model not found")
        else:
            # For LR, use lowest available epsilon as "baseline"
            epsilons = loader.get_available_epsilons(config.dataset, 'lr_dp')
            if epsilons:
                baseline_model = loader.get_model(config.dataset, 'lr_dp', epsilons[0])
    
    if baseline_model is None:
        raise HTTPException(status_code=500, detail=f"No baseline model found for {config.model_type}")
    
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


@app.post("/api/experiment/upload", response_model=ExperimentResult)
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


# ============================================================================
# Run with: uvicorn main:app --reload --port 8000
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
