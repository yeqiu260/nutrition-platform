#!/bin/bash
# ================================================================
# wysik.com - Nginx + SSL 自動安裝腳本
# 在 EC2 (Amazon Linux 2023) 上運行
# ================================================================

set -e

echo "=========================================="
echo "  wysik.com Nginx + SSL 設置"
echo "=========================================="

# 1. 安裝 Nginx
echo ""
echo "[1/5] 安裝 Nginx..."
sudo dnf install -y nginx || sudo yum install -y nginx || sudo amazon-linux-extras install -y nginx1

# 2. 安裝 Certbot (Let's Encrypt)
echo ""
echo "[2/5] 安裝 Certbot..."
sudo dnf install -y certbot python3-certbot-nginx || sudo pip3 install certbot certbot-nginx

# 3. 創建 certbot 驗證目錄
echo ""
echo "[3/5] 創建目錄..."
sudo mkdir -p /var/www/certbot

# 4. 先用 HTTP-only 配置啟動 Nginx（申請證書前需要）
echo ""
echo "[4/5] 配置 Nginx（HTTP 模式）..."

# 寫入臨時 HTTP 配置（用於 certbot 驗證）
sudo tee /etc/nginx/conf.d/wysik.conf > /dev/null << 'NGINX_HTTP'
server {
    listen 80;
    server_name wysik.com www.wysik.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        client_max_body_size 10M;
    }
}
NGINX_HTTP

# 刪除默認配置避免衝突
sudo rm -f /etc/nginx/conf.d/default.conf

# 測試並啟動 Nginx
sudo nginx -t
sudo systemctl start nginx 2>/dev/null || sudo systemctl restart nginx
sudo systemctl enable nginx

echo ""
echo "  ✓ Nginx HTTP 模式已啟動"
echo "  ✓ http://wysik.com 現在應該可以訪問了"

# 5. 申請 SSL 證書
echo ""
echo "[5/5] 申請 Let's Encrypt SSL 證書..."
echo "  （需要你輸入郵箱地址，用於證書到期提醒）"
echo ""

sudo certbot --nginx -d wysik.com -d www.wysik.com

# 6. 替換為完整的 HTTPS 配置
echo ""
echo "正在應用完整 HTTPS 配置..."

sudo tee /etc/nginx/conf.d/wysik.conf > /dev/null << 'NGINX_HTTPS'
server {
    listen 80;
    server_name wysik.com www.wysik.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name wysik.com www.wysik.com;

    ssl_certificate /etc/letsencrypt/live/wysik.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wysik.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 10M;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;
        client_max_body_size 10M;
    }

    location /health {
        proxy_pass http://localhost:8000/health;
    }
}
NGINX_HTTPS

sudo nginx -t && sudo systemctl reload nginx

# 7. 設置自動續期
echo ""
echo "設置 SSL 證書自動續期..."
(sudo crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | sudo crontab -

echo ""
echo "=========================================="
echo "  ✅ 全部完成！"
echo "=========================================="
echo ""
echo "  🌐 https://wysik.com"
echo "  🌐 https://www.wysik.com"
echo ""
echo "  • HTTP 自動跳轉到 HTTPS"
echo "  • SSL 證書 90 天自動續期"
echo "  • 前端代理: localhost:3000"
echo "  • 後端 API 代理: localhost:8000"
echo ""
