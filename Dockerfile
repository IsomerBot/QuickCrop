# Multi-stage production Dockerfile for QuickCrop

# Stage 1: Frontend Builder
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm ci --only=production

# Copy frontend source code
COPY frontend/ ./

# Build the frontend
RUN npm run build

# Stage 2: Backend Builder
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Final Production Image
FROM python:3.11-slim

# Install runtime dependencies for image processing
RUN apt-get update && apt-get install -y \
    # OpenCV dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libgl1-mesa-glx \
    # Image optimization tools
    oxipng \
    pngquant \
    jpegoptim \
    webp \
    # Security and utility
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r quickcrop && useradd -r -g quickcrop quickcrop

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=backend-builder --chown=quickcrop:quickcrop /root/.local /home/quickcrop/.local

# Copy backend application code
COPY --chown=quickcrop:quickcrop backend/ ./backend/

# Copy built frontend from builder
COPY --from=frontend-builder --chown=quickcrop:quickcrop /app/.next ./frontend/.next
COPY --from=frontend-builder --chown=quickcrop:quickcrop /app/public ./frontend/public
COPY --from=frontend-builder --chown=quickcrop:quickcrop /app/package*.json ./frontend/

# Create necessary directories with proper permissions
RUN mkdir -p /app/uploads /app/exports /app/temp /app/logs && \
    chown -R quickcrop:quickcrop /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/quickcrop/.local/bin:$PATH \
    ENV=production \
    UPLOAD_DIR=/app/uploads \
    EXPORT_DIR=/app/exports \
    TEMP_DIR=/app/temp \
    LOG_DIR=/app/logs

# Switch to non-root user
USER quickcrop

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose ports
EXPOSE 8000 3000

# Volume mount points
VOLUME ["/app/uploads", "/app/exports", "/app/logs"]

# Start command using a shell script for proper process management
COPY --chown=quickcrop:quickcrop docker/start.sh /app/
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]