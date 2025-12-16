#!/bin/bash

# Test Docker Setup for Privacy Playground

echo "================================"
echo "Privacy Playground - Docker Test"
echo "================================"

echo ""
echo "1. Building Docker images..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "✅ Build successful"

echo ""
echo "2. Starting services..."
docker-compose up -d

echo ""
echo "3. Waiting for services to be healthy (30s)..."
sleep 30

echo ""
echo "4. Checking backend health..."
BACKEND_STATUS=$(curl -s http://108.136.50.96:8000/health | grep -o '"status":"healthy"')
if [ -z "$BACKEND_STATUS" ]; then
    echo "❌ Backend health check failed"
    docker-compose logs backend
    exit 1
fi
echo "✅ Backend is healthy"

echo ""
echo "5. Checking frontend health..."
FRONTEND_STATUS=$(curl -s http://43.218.226.78/health)
if [ -z "$FRONTEND_STATUS" ]; then
    echo "❌ Frontend health check failed"
    docker-compose logs frontend
    exit 1
fi
echo "✅ Frontend is healthy"

echo ""
echo "6. Testing API endpoint..."
API_RESPONSE=$(curl -s http://108.136.50.96/api/health)
if [ -z "$API_RESPONSE" ]; then
    echo "❌ API proxy failed"
    exit 1
fi
echo "✅ API proxy working"

echo ""
echo "================================"
echo "All tests passed! ✅"
echo "================================"
echo ""
echo "Services running:"
echo "  Frontend: http://43.218.226.78"
echo "  Backend:  http://108.136.50.96:8000"
echo "  API Docs: http://108.136.50.96:8000/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop:      docker-compose down"
