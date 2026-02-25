# 启动后端服务
Write-Host "Starting backend server..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
