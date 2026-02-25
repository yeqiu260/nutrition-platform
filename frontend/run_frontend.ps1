# 前端启动脚本
Write-Host "================================" -ForegroundColor Cyan
Write-Host "启动 WysikHealth 前端服务" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Node.js
Write-Host "检查 Node.js..." -ForegroundColor Yellow
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未安装 Node.js" -ForegroundColor Red
    Write-Host "请访问 https://nodejs.org/ 下载安装" -ForegroundColor Red
    exit 1
}

$nodeVersion = node --version
Write-Host "✓ Node.js 版本: $nodeVersion" -ForegroundColor Green

# 检查依赖
if (!(Test-Path "node_modules")) {
    Write-Host ""
    Write-Host "首次运行，正在安装依赖..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败" -ForegroundColor Red
        exit 1
    }
}

# 启动开发服务器
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "启动前端开发服务器..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问地址: http://localhost:3100" -ForegroundColor Green
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host ""

npx next dev -p 3100
