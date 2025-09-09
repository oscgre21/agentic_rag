# Multi-stage build for optimized image size
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages and PDF processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    curl \
    # PDF processing dependencies
    libpoppler-cpp-dev \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file - use minimal for faster builds
COPY requirements-minimal.txt requirements.txt* ./

# Install Python dependencies
RUN if [ -f requirements-minimal.txt ]; then \
        pip install --no-cache-dir --user -r requirements-minimal.txt; \
    else \
        pip install --no-cache-dir --user -r requirements.txt; \
    fi

# Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:${PATH}" \
    OLLAMA_HOST=${OLLAMA_HOST:-http://localhost:11434}

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    # PDF processing runtime dependencies
    libpoppler-cpp0v5 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /home/appuser/app/docs && \
    chown -R appuser:appuser /home/appuser

# Set working directory
WORKDIR /home/appuser/app

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser agentic_api.py .
COPY --chown=appuser:appuser .env.example .

# Create docs directory for PDFs
RUN mkdir -p docs && chown -R appuser:appuser docs

# Switch to non-root user
USER appuser

# Create volume for PDF documents
VOLUME ["/home/appuser/app/docs"]

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "agentic_api.py"]