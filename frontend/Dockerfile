# 智能营养建议平台 - 前端 Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 接受构建参数
ARG NEXT_PUBLIC_API_URL

# 赋值给环境变量供构建时使用
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# 构建应用
RUN npm run build

# 生产镜像
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000
# 复制构建产物
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["node", "server.js"]
