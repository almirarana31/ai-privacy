# Test Docker Setup for Privacy Playground (Windows)

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Privacy Playground - Docker Test" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

Write-Host "`n1. Building Docker images..." -ForegroundColor Yellow
docker-compose build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Build successful" -ForegroundColor Green

Write-Host "`n2. Starting services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "`n3. Waiting for services to be healthy (30s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`n4. Checking backend health..." -ForegroundColor Yellow
try {
    $backendResponse = Invoke-WebRequest -Uri "http://43.218.226.78:8000/health" -UseBasicParsing
    if ($backendResponse.StatusCode -eq 200) {
        Write-Host "✅ Backend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Backend health check failed" -ForegroundColor Red
    docker-compose logs backend
    exit 1
}

Write-Host "`n5. Checking frontend health..." -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://43.218.226.78/health" -UseBasicParsing
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "✅ Frontend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Frontend health check failed" -ForegroundColor Red
    docker-compose logs frontend
    exit 1
}

Write-Host "`n6. Testing API endpoint..." -ForegroundColor Yellow
try {
    $apiResponse = Invoke-WebRequest -Uri "http://43.218.226.78/api/health" -UseBasicParsing
    if ($apiResponse.StatusCode -eq 200) {
        Write-Host "✅ API proxy working" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ API proxy failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "All tests passed! ✅" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host "`nServices running:" -ForegroundColor Yellow
Write-Host "  Frontend: http://43.218.226.78" -ForegroundColor White
Write-Host "  Backend:  http://108.136.50.96:8000" -ForegroundColor White
Write-Host "  API Docs: http://108.136.50.96:8000/docs" -ForegroundColor White
Write-Host "`nTo view logs: docker-compose logs -f" -ForegroundColor Cyan
Write-Host "To stop:      docker-compose down" -ForegroundColor Cyan
