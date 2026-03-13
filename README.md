# WysikHealth - 智能营养建议平台

一个基于 AI 的个性化营养补充品推荐平台。用户通过填写健康问卷，平台利用 AI（xAI Grok）分析健康状况，生成个性化的营养补充品推荐方案，并关联可购买的商家产品。

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Next.js 14 / TypeScript / Tailwind CSS / Zustand |
| **后端** | FastAPI / Python 3.11 / SQLAlchemy / Celery |
| **数据库** | PostgreSQL 15 |
| **缓存与队列** | Redis 7 |
| **AI 引擎** | xAI Grok API |
| **文件处理** | PaddleOCR / PDF2Image |
| **对象存储** | S3 / Cloudflare R2 |
| **反向代理** | Nginx + SSL (Let's Encrypt) |
| **容器化** | Docker Compose |

## 系统架构

```
用户浏览器
    │
    ▼
Nginx（反向代理 + SSL）
    ├──► Frontend :3000（Next.js）
    └──► Backend  :8000（FastAPI）
              ├──► PostgreSQL :5432
              ├──► Redis      :6379
              └──► Celery Worker（异步任务）
```

## 核心功能

### 智能问卷与 AI 推荐
- 涵盖 **30+ 种营养补充品**（维生素、矿物质、功能性成分等）
- 分**筛查阶段**和**详细评估**两阶段进行
- 调用 Grok AI API 生成个性化推荐，附带安全提醒与免责声明

### 健康报告 OCR 提取
- 支持上传 PDF / 图片格式的健康报告
- 通过 PaddleOCR 自动提取健康指标数据
- AI 结合报告数据提供更精准的推荐

### 用户系统
- OTP 验证码登录（邮箱/手机）
- 密码登录
- JWT Token 鉴权（24 小时有效期）
- 多因素认证（MFA）

### 产品与联盟营销
- 商家产品关联补充品推荐
- 产品审核上架流程
- 联盟点击/购买追踪
- 区域限制与每日/总量上限

### 历史与收藏
- 查看历史问卷与推荐结果
- 收藏感兴趣的产品

### 管理后台
- 用户数据分析仪表盘
- 产品审核管理
- 系统配置
- IP 白名单

### 国际化 (i18n)
- 支持英文 (en) 与繁体中文 (zh-TW)
- 前端界面与后端 API 响应均支持多语言

### 安全与合规
- **防 Prompt 注入**：19 种危险模式检测，三层防护
- **字段级加密**：Fernet (AES-128) 对称加密
- **PII 脱敏**：电话、邮箱、IP 地址遮罩
- **防 IDOR**：资源所有权校验 + 角色权限控制
- **文件扫描**：上传文件的扩展名、魔数、内容检测
- **去识别化导出**：支持遮罩、移除、哈希三种模式
- **访问审计**：敏感操作日志记录
- **速率限制**：100 请求/分钟

## 项目结构

```
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 应用入口
│   │   ├── api/               # API 路由
│   │   │   ├── auth.py        # 认证（OTP/密码）
│   │   │   ├── quiz.py        # 问卷与推荐
│   │   │   ├── product.py     # 产品管理
│   │   │   ├── admin.py       # 管理后台
│   │   │   ├── analytics.py   # 事件追踪
│   │   │   ├── report.py      # 健康报告处理
│   │   │   ├── affiliate.py   # 联盟追踪
│   │   │   └── ...
│   │   ├── models/            # 数据库模型
│   │   ├── services/          # 业务逻辑
│   │   ├── core/              # 核心工具（配置、数据库、鉴权）
│   │   ├── middleware/        # 中间件（限流、请求大小）
│   │   └── tasks/             # Celery 异步任务
│   ├── alembic/               # 数据库迁移
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/                   # Next.js 前端
│   ├── src/
│   │   ├── app/               # 页面与路由
│   │   │   ├── page.tsx       # 主问卷页面
│   │   │   ├── history/       # 历史记录
│   │   │   ├── favorites/     # 收藏
│   │   │   └── admin/         # 管理后台
│   │   ├── lib/               # 工具函数与 API
│   │   ├── components/        # React 组件
│   │   └── messages/          # i18n 翻译文件
│   ├── Dockerfile
│   └── package.json
│
├── nginx/                      # Nginx 反向代理
│   ├── nginx.conf
│   └── setup-ssl.sh
│
└── docker-compose.yml          # 容器编排
```

## 快速开始

### 前置要求

- Docker & Docker Compose
- xAI Grok API Key（用于 AI 推荐）

### 1. 克隆仓库

```bash
git clone https://github.com/yeqiu260/nutrition-platform.git
cd nutrition-platform
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 必填 - 安全密钥（生产环境务必修改）
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# 必填 - AI 推荐引擎
GROK_API_KEY=your-grok-api-key

# 可选 - 对象存储（S3/Cloudflare R2）
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=nutrition-reports
S3_REGION=auto

# 可选 - Shopify 集成
SHOPIFY_STORE_URL=
SHOPIFY_ACCESS_TOKEN=

# 可选 - 邮件发送（OTP）
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
```

### 3. 启动服务

```bash
docker-compose up -d
```

启动后各服务端口：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 4. 数据库迁移

```bash
docker exec -it nutrition-backend alembic upgrade head
```

## API 文档

启动后端服务后，访问以下地址查看自动生成的 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/send-otp` | 发送 OTP 验证码 |
| POST | `/api/auth/verify-otp` | 验证 OTP 并登录 |
| POST | `/api/quiz/submit` | 提交问卷获取 AI 推荐 |
| GET | `/api/products/recommendations` | 获取推荐产品 |
| POST | `/api/report/upload` | 上传健康报告 |
| GET | `/api/user/history` | 获取问卷历史 |
| GET | `/api/user/favorites` | 获取收藏列表 |

所有 API 支持通过 `Accept-Language` 请求头指定响应语言（`en` 或 `zh-TW`）。

## 业务流程

```
1. 用户填写营养补充品问卷（30+ 种类）
       │
2. 可选上传健康报告（PDF/图片），OCR 自动提取指标
       │
3. 后端校验输入 + Prompt 注入防护
       │
4. 调用 Grok AI API 生成个性化推荐
       │
5. 返回排序后的推荐列表 + 安全提醒
       │
6. 展示推荐结果与关联商品
       │
7. 用户可收藏产品、查看历史、跳转购买
```

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 测试

```bash
# 后端测试
cd backend
pytest

# 安全功能测试（56 个用例，100% 通过率）
pytest tests/test_prompt_injection_guard.py
pytest tests/test_security_compliance.py
```

## 部署

项目已配置 Nginx SSL 反向代理，适用于生产部署：

```bash
# 设置 SSL 证书（Let's Encrypt）
cd nginx
chmod +x setup-ssl.sh
./setup-ssl.sh

# 启动全部服务
docker-compose up -d
```

域名：**wysik.com**

## 许可证

本项目为私有项目，保留所有权利。
