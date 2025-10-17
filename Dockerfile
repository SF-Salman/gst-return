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

COPY requirements.txt ./
RUN pip wheel --no-cache-dir --only-binary=:all: --wheel-dir=/wheels -r requirements.txt

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

# Expose FastAPI port (Railway sets PORT env)
EXPOSE 8000

# Start FastAPI app; use PORT if provided (Railway), default 8000
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
