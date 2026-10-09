# ==========================================
# 多阶段构建 Dockerfile (Multi-Stage Build)
# ==========================================

# 阶段 1: 前端构建 (Node.js 20)
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# 阶段 2: 后端运行环境 (Python 3.11)
FROM python:3.11-slim AS runtime
WORKDIR /app

# 系统依赖与时区设置
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码与前端构建产物
COPY backend/ ./
COPY --from=frontend-builder /app/static ./static

# 数据持久化目录
RUN mkdir -p /data
ENV DATABASE_URL="sqlite:////data/world_sim.db"
ENV PORT=8080

EXPOSE 8080

# 启动单端口服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
