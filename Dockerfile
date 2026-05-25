# ========== 第一阶段：构建前端静态资源 ==========

# 使用百度内部 Node.js 24 镜像作为前端构建环境
FROM iregistry.baidu-int.com/baidu-base/node:24-noble AS frontend-builder
# 安装 nodejs24 对应的 npm 包管理器
RUN apt-get update && apt-get install -y nodejs24-npm
# 验证 npm 版本（调试用）
RUN npm version
# 全局安装 pnpm 包管理器
RUN npm install -g pnpm
# 设置前端工作目录
WORKDIR /app/frontend
# 复制前端源码到工作目录
COPY output/frontend/ ./
# 将 nodejs24 的 bin 目录加入 PATH，确保后续命令能找到 node/npm
ENV PATH="/usr/lib/nodejs24/bin:$PATH"
RUN pnpm config set registry http://registry.npm.baidu-int.com
# 安装前端依赖
RUN npm install
# 构建前端静态文件
RUN npm run build


# ========== 第二阶段：生产环境运行时镜像 ==========

# 使用百度内部 Ubuntu noble 镜像作为运行环境基础镜像
FROM iregistry.baidu-int.com/baidu-base/ubuntu:noble

# 禁止 apt 安装时弹出交互式配置界面
ENV DEBIAN_FRONTEND=noninteractive
# 禁止 Python 生成 .pyc 字节码文件
ENV PYTHONDONTWRITEBYTECODE=1
# 设置 Python 日志/输出不缓冲，实时输出
ENV PYTHONUNBUFFERED=1
# 定义 Python 虚拟环境路径
ENV VIRTUAL_ENV=/app/venv
# 将虚拟环境的 bin 目录加入 PATH，优先使用虚拟环境中的 Python 和工具
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    nginx-full \
    curl \
    gnupg \
    ca-certificates \
    wget vim net-tools iputils-ping nano htop iftop iotop git unzip zip rsync procps tree lsof netcat-traditional traceroute mtr-tiny \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录和虚拟环境
WORKDIR /app
# 创建后端代码目录、模板目录、静态资源目录和日志目录
RUN mkdir -p /app/backend /app/backend/templates/ /app/backend/static/assets /app/logs
# 使用 Python 3.12 创建虚拟环境
RUN python3.12 -m venv /app/venv

# 升级 pip 并安装依赖
# 复制后端依赖声明文件到镜像中
COPY output/requirements.txt /app/
# 升级 pip 并使用百度内部 PyPI 镜像安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip -i https://pip.baidu-int.com/simple/ --trusted-host pip.baidu-int.com \
    && pip install --no-cache-dir -r /app/requirements.txt -i https://pip.baidu-int.com/simple/ --trusted-host pip.baidu-int.com

# 复制应用代码
COPY output/ /app/

# 从前端构建阶段产物中复制构建好的静态文件
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist
# 复制前端入口 HTML 到后端模板目录（由后端服务渲染）
COPY --from=frontend-builder /app/frontend/dist/index.html /app/backend/templates/
# 复制前端静态资源（JS/CSS/图片等）到后端静态资源目录
COPY --from=frontend-builder /app/frontend/dist/assets/ /app/backend/static/assets/

# 设置权限
RUN chmod +x /app/entrypoint.sh

# 暴露端口
EXPOSE 8000

# 启动脚本
ENV PORT=8000
# 后端 SPA 托管子路径，与前端 VITE_BASE_PATH 对应（不带尾部斜杠）
CMD ["/app/entrypoint.sh"]
