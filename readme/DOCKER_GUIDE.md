# Privacy Playground - Docker Setup

## Quick Start

### Build and run everything:
```bash
docker-compose up --build
```

### Run in detached mode:
```bash
docker-compose up -d
```

### View logs:
```bash
docker-compose logs -f
```

### Stop everything:
```bash
docker-compose down
```

## Services

- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Individual Commands

### Build backend only:
```bash
docker build -t privacy-backend ./backend
```

### Build frontend only:
```bash
docker build -t privacy-frontend ./frontend
```

### Run backend standalone:
```bash
docker run -p 8000:8000 -v $(pwd)/backend/models_research:/app/models_research privacy-backend
```

### Run frontend standalone:
```bash
docker run -p 80:80 privacy-frontend
```

## Development

### Rebuild after code changes:
```bash
docker-compose up --build
```

### View container status:
```bash
docker-compose ps
```

### Access backend container shell:
```bash
docker exec -it privacy-playground-backend bash
```

### Access frontend container shell:
```bash
docker exec -it privacy-playground-frontend sh
```

## Volume Management

The following directories are mounted as volumes:
- `backend/models_research` - Pre-trained models
- `backend/models_research_fl_dp` - FL+DP results
- `backend/data` - Dataset cache
- `backend/datasets` - Raw datasets

To reset volumes:
```bash
docker-compose down -v
```

## Production Deployment

### Using docker-compose:
```bash
docker-compose -f docker-compose.yml up -d
```

### Push to registry:
```bash
docker tag privacy-backend:latest your-registry/privacy-backend:latest
docker tag privacy-frontend:latest your-registry/privacy-frontend:latest
docker push your-registry/privacy-backend:latest
docker push your-registry/privacy-frontend:latest
```

## Troubleshooting

### Check backend health:
```bash
curl http://localhost:8000/health
```

### Check frontend health:
```bash
curl http://localhost/health
```

### View backend logs:
```bash
docker-compose logs backend
```

### View frontend logs:
```bash
docker-compose logs frontend
```

### Rebuild from scratch:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```
