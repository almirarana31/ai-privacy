# 🐳 Privacy Playground - Docker Deployment Guide

Complete Docker containerization with Kubernetes-ready architecture.

## 📦 What's Included

- **Backend**: FastAPI + PyTorch (Python 3.11)
- **Frontend**: React + Vite (Node 20 + Nginx)
- **Docker Compose**: Full orchestration
- **Health Checks**: Automated monitoring
- **Volume Mounts**: Persistent data/models

## 🚀 Quick Start

### 1. Build and Run
```powershell
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 2. Access Services
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost/api/health

### 3. View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 4. Stop Services
```powershell
docker-compose down

# Remove volumes too
docker-compose down -v
```

## 🧪 Testing

Run the automated test script:

```powershell
# Windows PowerShell
.\test-docker.ps1

# Linux/Mac
chmod +x test-docker.sh
./test-docker.sh
```

This will:
1. Build Docker images
2. Start services
3. Wait for health checks
4. Test backend API
5. Test frontend
6. Test API proxy

## 📂 Directory Structure

```
ai-privacy/
├── backend/
│   ├── Dockerfile              # Backend container config
│   ├── .dockerignore           # Excluded files
│   ├── main.py                 # FastAPI app
│   ├── requirements.txt        # Python dependencies
│   └── models_research/        # Mounted volume (results)
│
├── frontend/
│   ├── Dockerfile              # Multi-stage frontend build
│   ├── .dockerignore           # Excluded files
│   ├── nginx.conf              # Nginx reverse proxy config
│   └── src/                    # React app
│
├── docker-compose.yml          # Orchestration config
├── test-docker.ps1             # Windows test script
└── test-docker.sh              # Linux/Mac test script
```

## 🔧 Configuration

### Backend Environment Variables

Edit `docker-compose.yml` to add:
```yaml
environment:
  - PYTHONUNBUFFERED=1
  - ENV=production
  - LOG_LEVEL=info
```

### Frontend API URL

The frontend uses `/api` prefix which Nginx proxies to backend.

To change backend URL, update `frontend/nginx.conf`:
```nginx
location /api/ {
    proxy_pass http://backend:8000/;
}
```

### Volume Mounts

Results and models are persisted via volumes:
```yaml
volumes:
  - ./backend/models_research:/app/models_research
  - ./backend/models_research_fl_dp:/app/models_research_fl_dp
  - ./backend/data:/app/data
```

Add your completed results here and restart:
```powershell
docker-compose restart backend
```

## 🏗️ Building Individual Services

### Backend Only
```powershell
cd backend
docker build -t privacy-backend .
docker run -p 8000:8000 -v ${PWD}/models_research:/app/models_research privacy-backend
```

### Frontend Only
```powershell
cd frontend
docker build -t privacy-frontend .
docker run -p 80:80 privacy-frontend
```

## 🔍 Troubleshooting

### Backend won't start
```powershell
# Check logs
docker-compose logs backend

# Check if models directory exists
ls backend/models_research

# Rebuild without cache
docker-compose build --no-cache backend
```

### Frontend 502 Bad Gateway
```powershell
# Backend might not be healthy yet
docker-compose ps

# Check backend health
curl http://localhost:8000/health

# Restart frontend
docker-compose restart frontend
```

### Models not loading
```powershell
# Ensure models are in correct location
ls backend/models_research/research_results.json

# Check backend logs
docker-compose logs backend | grep "models"

# Verify volume mounts
docker inspect privacy-playground-backend
```

### Port already in use
```powershell
# Find what's using port 80
netstat -ano | findstr :80

# Change ports in docker-compose.yml
ports:
  - "8080:80"  # Use 8080 instead
```

## 📊 Resource Requirements

### Minimum
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 10GB

### Recommended
- **CPU**: 4 cores
- **RAM**: 8GB
- **Disk**: 20GB

### With GPU (for training)
Add to `docker-compose.yml`:
```yaml
backend:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

## 🚢 Production Deployment

### 1. Build for production
```powershell
docker-compose -f docker-compose.yml build
```

### 2. Tag images
```powershell
docker tag privacy-playground-backend:latest yourusername/privacy-backend:v1.0
docker tag privacy-playground-frontend:latest yourusername/privacy-frontend:v1.0
```

### 3. Push to registry
```powershell
docker login
docker push yourusername/privacy-backend:v1.0
docker push yourusername/privacy-frontend:v1.0
```

### 4. Deploy with docker-compose
```powershell
# On production server
docker-compose pull
docker-compose up -d
```

## ☸️ Kubernetes Migration (Next Step)

Files created for K8s deployment:
- `k8s/backend-deployment.yaml` - Backend pods
- `k8s/frontend-deployment.yaml` - Frontend pods
- `k8s/backend-service.yaml` - Backend service
- `k8s/frontend-service.yaml` - Frontend service
- `k8s/ingress.yaml` - Routing

Ready to create Kubernetes manifests? Ask and I'll generate them!

## 🔐 Security Considerations

### Production Checklist
- [ ] Change default ports
- [ ] Enable HTTPS/TLS
- [ ] Add authentication
- [ ] Limit CORS origins
- [ ] Use secrets for sensitive data
- [ ] Enable rate limiting
- [ ] Set resource limits
- [ ] Regular security scans

### Update nginx.conf for HTTPS:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    # ... rest of config
}
```

## 📈 Monitoring

### View container stats
```powershell
docker stats
```

### Check health
```powershell
# Backend
curl http://localhost:8000/health

# Frontend
curl http://localhost/health
```

### Export logs
```powershell
docker-compose logs > deployment.log
```

## 🎯 Next Steps

1. ✅ Docker setup complete
2. ⏳ Test locally
3. ⏳ Add research results
4. ⏳ Create Kubernetes manifests
5. ⏳ Deploy to cloud (Azure/AWS/GCP)
6. ⏳ Set up CI/CD pipeline

---

**Ready to deploy!** 🚀

Run `.\test-docker.ps1` to validate your setup.
