# AI Privacy - Privacy-Preserving Machine Learning Platform

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

- **Federation setup:**
  - 5 clients (IID data distribution)
  - 20 global rounds
  - 5 local epochs per round
  - Batch size: 64, learning rate: 0.001

- **Total configurations:** 2 datasets × 2 models × 5 aggregations = **20 configs**

### **Cross-Validation**

**Rigorous 5×5 evaluation design:**
- **5 random seeds:** [42, 123, 456, 789, 1011]
- **5-fold stratified cross-validation** (maintains class balance)
- **25 evaluations per configuration**

**Total experimental evaluations:**
- Baseline: 4 configs × 25 = 100 evaluations
- Differential Privacy: 20 configs × 25 = 500 evaluations
- Federated Learning: 20 configs × 25 = 500 evaluations
- **Grand total: 1,100 evaluations**

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
User → localhost:3000 → Nginx
                         ↓
                    /api/* requests
                         ↓
              backend:8000 (Docker network)
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
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

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

### **Available Notebooks**

| Notebook | Purpose | Configs | Evaluations |
|----------|---------|---------|-------------|
| `dp_continue_crossvalidation.ipynb` | DP Diabetes (LR, FNN) | 10 | 250 |
| `dp_adult_complete.ipynb` | DP Adult (LR, FNN) | 10 | 250 |
| `fl_diabetes_fnn_continue.ipynb` | FL Diabetes FNN completion | 3 | 75 |
| `comprehensive_analysis.ipynb` | Statistical analysis + viz | - | - |
| `merge_all_results.ipynb` | Aggregate all results | - | - |

## 📊 Metrics & Analysis

### **Performance Metrics**
- **Accuracy** - Primary metric (mean ± std, min-max range)
- **F1-Score** - Weighted average (handles class imbalance)
- **Actual ε** - Measured privacy consumption (DP only)

### **Statistical Tests**
- Independent t-tests comparing each method vs baseline
- p-values for significance (α=0.05)
- Accuracy loss quantification
- Privacy-utility tradeoff visualization

### **Visualizations**
- Privacy-accuracy tradeoff curves (DP)
- Aggregation method comparison (FL)
- Accuracy loss heatmaps
- Overall method comparison

## 📈 Current Progress

### ✅ Completed
- Baseline: All 4 configurations (diabetes + adult, LR + FNN)
- FL Adult: All 10 configurations (2 models × 5 aggregations)
- FL Diabetes: 7/10 configurations (missing FNN: q-FedAvg, SCAFFOLD, FedAdam)
- DP Diabetes: 3/10 configurations (LR: ε=5.0, 10.0 | FNN: ε=0.5)
- Docker containerization setup
- Analysis notebooks

### ⚠️ In Progress
- DP Diabetes: 7 missing configs
- DP Adult: All 10 configs (notebook created)
- FL Diabetes FNN: 3 missing aggregations

### 📝 Total
- **Completed:** ~570/1,100 evaluations (~52%)
- **Remaining:** ~530 evaluations

## 🔐 Privacy Guarantees

### **Differential Privacy (DP)**
- **Formal guarantee:** (ε, δ)-differential privacy
- Lower ε = stronger privacy, higher accuracy loss
- Opacus library provides certified privacy accounting
- **Note:** Current notebooks use warnings suppression for clean output. For production deployment, enable `secure_mode=True`

### **Federated Learning (FL)**
- **Privacy benefit:** Raw data never leaves clients
- **Limitation:** No formal privacy guarantee (vulnerable to inference attacks)
- **Enhancement:** Can combine with DP for formal guarantees (future work)

## 🛠️ Technology Stack

### **Backend**
- Python 3.11
- FastAPI (async web framework)
- PyTorch (deep learning)
- Opacus (differential privacy)
- scikit-learn (preprocessing & metrics)
- pandas, numpy (data manipulation)

### **Frontend**
- React 18
- Vite (build tool)
- Tailwind CSS (styling)
- Recharts (data visualization)
- Axios (HTTP client)

### **Infrastructure**
- Docker & Docker Compose
- Nginx (reverse proxy)
- Uvicorn (ASGI server)

### **Development**
- VS Code (IDE)
- Jupyter/IPython (notebooks)
- Kaggle (GPU training)

## 🚢 Kubernetes Deployment (Planned)

### **Architecture**
```
Internet → Ingress (HTTPS/TLS)
            ↓
    LoadBalancer Service
            ↓
    ┌──────┴──────┐
    ↓             ↓
Frontend Pods  Backend Pods
(replicas)     (replicas)
    ↓             ↓
PersistentVolumeClaims
(results storage)
```

### **Components**
- Deployments (frontend, backend with replicas)
- Services (ClusterIP, LoadBalancer)
- Ingress (domain routing + TLS)
- PersistentVolume/PVC (shared storage)
- ConfigMaps (configuration)
- HorizontalPodAutoscaler (auto-scaling)

### **Cloud Platforms**
- Azure Kubernetes Service (AKS)
- Amazon Elastic Kubernetes Service (EKS)
- Google Kubernetes Engine (GKE)

## 📚 References

### **Papers**
- Abadi et al. (2016) - Deep Learning with Differential Privacy
- McMahan et al. (2017) - Communication-Efficient Learning of Deep Networks from Decentralized Data
- Li et al. (2020) - Federated Optimization in Heterogeneous Networks (FedProx)
- Reddi et al. (2021) - Adaptive Federated Optimization (FedAdam)

### **Libraries**
- [Opacus](https://opacus.ai/) - PyTorch Differential Privacy
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library

## 📄 License

This project is for academic research purposes.

## 👥 Contributors

Research project by Almir

## 🤝 Contributing

This is a research project. For collaboration inquiries, please open an issue.

## 📧 Contact

For questions about the research methodology or implementation, please open a GitHub issue.

---

**Status:** Active Development | **Last Updated:** December 2025
