# ---------- Frontend build ----------
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend .
RUN npm run build

# ---------- Backend ----------
FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# Backend setup
WORKDIR /backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend .

# Copy frontend build to Nginx
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose App Runner port
EXPOSE 80

# Start both services
CMD service nginx start && uvicorn main:app --host 0.0.0.0 --port 8000
