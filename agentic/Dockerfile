# Multi-stage build for optimized image size
FROM python:3.11-slim AS builder

# Disable pip root warning since we're in a container build stage
ENV PIP_ROOT_USER_ACTION=ignore

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONPATH="/home/appuser/app" \
    OLLAMA_HOST="http://localhost:11434"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /home/appuser/app/docs && \
    chown -R appuser:appuser /home/appuser

# Set working directory
WORKDIR /home/appuser/app

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy the refactored application structure
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser models/ ./models/
COPY --chown=appuser:appuser services/ ./services/
COPY --chown=appuser:appuser routers/ ./routers/
COPY --chown=appuser:appuser utils/ ./utils/
COPY --chown=appuser:appuser core/ ./core/

# Copy dist directory for Flowise chatbot (create if doesn't exist locally)
RUN mkdir -p dist && chown -R appuser:appuser dist
COPY --chown=appuser:appuser dist/ ./dist/ 2>/dev/null || true

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

# Default command - run the app directly
CMD ["python", "app.py"]