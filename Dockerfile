#############################
# Backend (FastAPI) container
#############################

# Stage 1: Build frontend (Vite)
FROM node:20-alpine AS webbuild
WORKDIR /web
ENV CI=true
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

# Stage 2: Build Python wheels
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System build deps for occasional source builds when wheel missing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# Upgrade pip/setuptools/wheel, then build wheels (prefer prebuilt, fallback to source)
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip wheel --no-cache-dir --prefer-binary --wheel-dir=/wheels -r requirements.txt

# Stage 3: Runtime
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies from prebuilt wheels
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Copy backend source code only (avoid bringing dev files)
COPY backend ./backend
COPY gstr1.py gstr3b.py json_import.py ./

# Copy built frontend assets into image
COPY --from=webbuild /web/dist ./frontend/dist

# Expose default Railway port (metadata)
EXPOSE 8080

# Container healthcheck for orchestration
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 CMD python -c "import os,urllib.request,sys;port=os.getenv('PORT','8000');url='http://127.0.0.1:'+port+'/api/health';sys.exit(0) if urllib.request.urlopen(url,timeout=2).status==200 else sys.exit(1)"

# Start FastAPI app; use PORT if provided (Railway), default 8000
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
