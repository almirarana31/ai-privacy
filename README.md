# AI Privacy - Privacy-Preserving Machine Learning Platform
![Status](https://img.shields.io/badge/status-active-success)
![Research](https://img.shields.io/badge/type-academic%20research-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Docker](https://img.shields.io/badge/docker-ready-2496ED)
![License](https://img.shields.io/badge/license-academic-lightgrey)
![Privacy](https://img.shields.io/badge/focus-privacy%20%26%20ethics-purple)

A comprehensive research platform for evaluating privacy-preserving machine learning techniques including **Differential Privacy** and **Federated Learning** across multiple datasets and models.

## 📊 Overview

This project implements and compares three approaches to machine learning:
1. **Baseline** - Standard centralized training (no privacy)
2. **Differential Privacy (DP)** - Privacy-preserving training with formal privacy guarantees
3. **Federated Learning (FL)** - Distributed training across multiple clients

## 🎯 Research Objectives

- Compare privacy-utility tradeoffs across different privacy budgets (ε)
- Evaluate multiple federated learning aggregation strategies
- Test across different model architectures (LR vs FNN)
- Validate across diverse datasets (healthcare and demographic)
- Provide rigorous statistical analysis with 5-fold CV × 5 random seeds

## 📁 Project Structure

```
ai-privacy/
├── frontend/                    # React web application
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── pages/              # Page views
│   │   └── services/           # API client
│   ├── nginx.conf              # Production web server config
│   └── Dockerfile              # Multi-stage build
│
├── backend/                     # FastAPI Python server
│   ├── main.py                 # API endpoints
│   ├── models_research/        # Baseline results
│   ├── models_fl_adult/        # FL Adult results
│   ├── models_fl_diabetes/     # FL Diabetes results
│   ├── models_dp_adult/        # DP Adult results (new)
│   ├── models_research_dp_continue/  # DP Diabetes results
│   │
│   ├── Notebooks:
│   ├── dp_continue_crossvalidation.ipynb  # DP Diabetes experiments
│   ├── dp_adult_complete.ipynb            # DP Adult experiments
│   ├── fl_diabetes_fnn_continue.ipynb     # FL Diabetes continuation
│   ├── comprehensive_analysis.ipynb       # Statistical analysis
│   ├── merge_all_results.ipynb            # Results aggregation
│   └── Dockerfile
│
├── docker-compose.yml          # Multi-container orchestration
└── test-docker.ps1             # Automated testing
```

## 🔬 Experimental Setup

### **Datasets**

#### 1. Diabetes Health Indicators (BRFSS 2015)
- **Source:** CDC Behavioral Risk Factor Surveillance System
- **Size:** ~70,000 samples
- **Features:** 21 health indicators (BMI, age, blood pressure, etc.)
- **Target:** Binary diabetes diagnosis
- **Source:** [Kaggle Dataset](https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset)

#### 2. Adult Census Income
- **Source:** UCI Machine Learning Repository
- **Size:** ~48,000 samples
- **Features:** 14 demographic/employment attributes
- **Target:** Binary income classification (≤50K or >50K)
- **Source:** [Kaggle Dataset](https://www.kaggle.com/datasets/uciml/adult-census-income)

### **Models**

#### Logistic Regression (LR)
- Single linear layer
- Simple baseline for privacy comparison

#### Feedforward Neural Network (FNN)
- Architecture: `[128, 64]` hidden layers
- Activation: ReLU
- Regularization: 30% dropout
- Tests privacy impact on complex models

### **Privacy-Preserving Methods**

#### 1. Differential Privacy (Opacus)
- **Privacy budgets (ε):** [0.5, 1.0, 3.0, 5.0, 10.0]
- **Mechanism:** Per-sample gradient clipping + Gaussian noise
- **Parameters:**
  - Noise multiplier: 1.0
  - Max gradient norm: 1.0
  - Delta (δ): 1e-5
- **Training:** 50 epochs (stops when target ε reached)
- **Total configurations:** 2 datasets × 2 models × 5 ε = **20 configs**

#### 2. Federated Learning
- **Aggregation strategies:**
  1. **FedAvg** - Weighted average by client data size
  2. **FedProx** - FedAvg + proximal term (μ=0.01)
  3. **q-FedAvg** - Fairness-weighted aggregation (q=0.2)
  4. **SCAFFOLD** - Variance reduction
  5. **FedAdam** - Adaptive optimization (β₁=0.9, β₂=0.999)

## 🏗️ Architecture

### **Frontend (React + Nginx)**
- **Development:** Vite dev server
- **Production:** Multi-stage Docker build
  - Stage 1: Node 20 Alpine builds React app
  - Stage 2: Nginx Alpine serves static files
- **Features:**
  - Reverse proxy: `/api/*` → backend
  - Gzip compression
  - Cache control
  - Health checks

### **Backend (FastAPI + PyTorch)**
- **Runtime:** Python 3.11-slim
- **Dependencies:**
  - FastAPI + Uvicorn
  - PyTorch (CPU mode for inference)
  - Opacus (differential privacy)
  - scikit-learn, pandas, numpy

### **API Endpoints**
```
GET /api/baseline         # Baseline results
GET /api/federated        # Federated learning results
GET /api/differential     # Differential privacy results
GET /api/compare          # Cross-method comparison
GET /health               # Health check
```

### **Docker Architecture**
- **2 services:** frontend (port 3000) + backend (port 8000)
- **8 volume mounts:** Results directories for hot-reload
- **Network:** Bridge mode (privacy-network)
- **Health checks:** 30s interval with dependencies
- **Restart policy:** unless-stopped

### **Request Flow**
```
User → https://ai-privacy-frontend.vercel.app → Nginx
          ↓
        /api/* requests
          ↓
        https://y6mhhtvkvp.ap-southeast-1.awsapprunner.com (Docker network)
          ↓
        FastAPI reads JSON from volumes
          ↓
        Response → Nginx → User
```

## 🚀 Getting Started

### **Prerequisites**
- Python 3.11+
- Node.js 20+
- Docker Desktop (for containerized deployment)
- CUDA-compatible GPU (optional, for faster training)

### **Local Development**

#### Backend Setup
```bash
# Navigate to project root
cd c:\Users\almir\ai-privacy

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### **Docker Deployment**

#### Build and run containers
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### Test deployment
```powershell
# Run automated tests
.\test-docker.ps1
```

Access the application:
- **Frontend:** https://ai-privacy-frontend.vercel.app
- **Backend API:** https://y6mhhtvkvp.ap-southeast-1.awsapprunner.com
- **API Docs:** https://y6mhhtvkvp.ap-southeast-1.awsapprunner.com/docs

## 📓 Running Experiments

### **On Kaggle (GPU)**

1. Create new Kaggle notebook
2. Add datasets as inputs:
   - Diabetes Health Indicators
   - Adult Census Income
   - Baseline results (for comparison)
3. Upload experiment notebook (DP or FL)
4. Enable GPU accelerator
5. Run all cells
6. Download results JSON from output

### **Locally (CPU/GPU)**

1. Open notebook in VS Code
2. Select Python environment (`.venv`)
3. Run all cells
4. Results save to `backend/models_*/`

## WebApp Design
<img width="1863" height="907" alt="Screenshot 2025-12-16 231839" src="https://github.com/user-attachments/assets/9dbbb969-d628-4de9-8d35-cc97930172ee" />
<img width="1848" height="914" alt="Screenshot 2025-12-16 231818" src="https://github.com/user-attachments/assets/e2e3d333-3bdf-4de3-a3e5-f566b2b190e5" />
<img width="1844" height="917" alt="Screenshot 2025-12-16 231825" src="https://github.com/user-attachments/assets/2f35a514-98e2-4f5d-b9c6-3493cea97168" />
<img width="1845" height="913" alt="Screenshot 2025-12-16 231832" src="https://github.com/user-attachments/assets/cfb3e38e-46a2-4bde-a3a7-abd2d7bea761" />


### **Libraries**
- [Opacus](https://opacus.ai/) - PyTorch Differential Privacy
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library

## 📄 License

This project is for academic research purposes.

**Status:** Active Development | **Last Updated:** December 2025
