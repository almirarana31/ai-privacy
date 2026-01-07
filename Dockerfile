# =========================
# Frontend build stage
# =========================
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Install frontend dependencies
COPY frontend/package*.json ./
RUN npm install

# Build frontend
COPY frontend .
RUN npm run build


# =========================
# Backend + Nginx runtime
# =========================
FROM python:3.11-slim

# Install system dependencies (nginx)
RUN apt-get update \
    && apt-get install -y nginx \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# Backend setup
# -------------------------
WORKDIR /backend

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend .

# -------------------------
# Frontend -> Nginx
# -------------------------
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# -------------------------
# Expose port for App Runner
# -------------------------
EXPOSE 80

# -------------------------
# Start Nginx + FastAPI
# -------------------------
CMD service nginx start && uvicorn main:app --host 0.0.0.0 --port 8000
