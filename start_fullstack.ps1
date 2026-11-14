# UniGuru Full-Stack Launcher (Model Server + FastAPI Backend + React Frontend)
$ErrorActionPreference = "Stop"
$RootDir = $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting UniGuru Marathi RAG & Local LLM Full Stack     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Local LLM Microservice (Port 8001)
Write-Host "[1/3] Starting Local LLM Microservice on port 8001..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c run_llm_service.bat" -WorkingDirectory $RootDir

Start-Sleep -Seconds 3

# 2. Start FastAPI Backend (Port 8000)
Write-Host "[2/3] Starting FastAPI Backend on port 8000..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c run_backend.bat" -WorkingDirectory $RootDir

Start-Sleep -Seconds 2

# 3. Start React Frontend (Port 5173)
Write-Host "[3/3] Starting React Frontend on port 5173..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c run_frontend.bat" -WorkingDirectory $RootDir

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "All 3 services have been launched in separate terminal windows!" -ForegroundColor Cyan
Write-Host "Opening http://localhost:5173 in browser..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"
