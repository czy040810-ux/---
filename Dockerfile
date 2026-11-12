# 基于 Python 3.11 的单容器演示镜像，包含 OCR 中文语言包。
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/app/data \
    BACKEND_URL=http://127.0.0.1:8000 \
    OCR_LANG=chi_sim+eng

WORKDIR /app

# 中文 OCR 不依赖外部付费服务；安装 tini 处理进程退出信号。
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY backend ./backend
COPY frontend.py ./frontend.py
COPY batch_import.py ./batch_import.py
COPY start.sh ./start.sh
RUN chmod +x /app/start.sh && mkdir -p /app/data && chown -R 10001:10001 /app

USER 10001:10001
EXPOSE 10000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/start.sh"]
