# =============================================================================
# CarveNex Backend — Dev Dockerfile (国内镜像版)
# =============================================================================

FROM docker.m.daocloud.io/library/python:3.12-slim-bookworm

WORKDIR /backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 替换 apt 源为国内镜像
RUN sed -i \
    -e "s|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g" \
    -e "s|http://security.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g" \
    /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    python3-dev \
    default-libmysqlclient-dev \
    build-essential \
    binutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制项目代码
COPY . .

# 安装 Python 依赖
# INSTALL_TEST_DEPS=true 时额外安装 requirements/test.txt（pytest / factory_boy / locust 等），
# 便于在容器内直接跑契约测试与压测；生产构建默认不带（见 docker-compose.prod.yml）。
ARG INSTALL_TEST_DEPS=false
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/base.txt && \
    if [ "$INSTALL_TEST_DEPS" = "true" ]; then pip install --no-cache-dir -r requirements/test.txt; fi && \
    mkdir -p logs

RUN chmod +x setup.sh

ENTRYPOINT ["./setup.sh"]
CMD ["django"] 