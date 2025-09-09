# Docker Deployment Guide for Agentic API

## Overview

This guide explains how to deploy the Agentic API using Docker and Docker Compose. The setup includes:
- **PostgreSQL with pgvector** for knowledge base and semantic cache
- **Ollama** for running LLM models locally
- **Agentic API** the main application

## Prerequisites

- Docker Engine 20.10 or higher
- Docker Compose 2.0 or higher
- At least 8GB of RAM (16GB recommended for larger models)
- 20GB of free disk space

## Quick Start

### 1. Clone and Navigate

```bash
cd /path/to/knowledge-graph-rag/agentic
```

### 2. Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database (optional - defaults work for local development)
POSTGRES_USER=ai
POSTGRES_PASSWORD=ai
POSTGRES_DB=ai
POSTGRES_PORT=5532

# Models (optional - defaults to smaller models)
AGENTIC_MODEL_ID=qwen3:4b
AGENTIC_EMBEDDER_MODEL=nomic-embed-text
AGENTIC_RESPONSE_MODEL=qwen2.5:7b-instruct

# Logging
AGENTIC_LOG_LEVEL=INFO
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Or build and start (if you made changes)
docker-compose up -d --build

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api
```

### 4. Verify Services

Check that all services are running:

```bash
# Check service status
docker-compose ps

# Test API health
curl http://localhost:8000/health

# Test Ollama
curl http://localhost:11434/api/tags
```

## Service Details

### PostgreSQL with pgvector

- **Port**: 5532 (customizable)
- **Database**: ai
- **User**: ai
- **Features**: 
  - pgvector extension for semantic search
  - Persistent volume for data
  - Automatic initialization

### Ollama

- **Port**: 11434
- **Models**: Automatically pulls configured models
- **Volume**: Persistent storage for models
- **Memory**: 4-8GB allocated

### Agentic API

- **Port**: 8000
- **Volume**: `./docs` mounted for PDF files
- **Health Check**: http://localhost:8000/health
- **Features**:
  - Non-root user for security
  - Automatic restart on failure
  - Environment variable configuration

## Common Operations

### Upload PDF Documents

```bash
# Upload a PDF file
curl -X POST "http://localhost:8000/upload-pdf" \
  -H "accept: application/json" \
  -F "file=@/path/to/document.pdf"
```

### Make Chat Queries

```bash
# Simple query
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What insurance products do you offer?",
    "search_knowledge": true
  }'
```

### Manage Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v

# Restart a specific service
docker-compose restart api

# Scale services (if needed)
docker-compose up -d --scale api=2

# Update services with new images
docker-compose pull
docker-compose up -d
```

## Production Deployment

### 1. Security Considerations

For production, update `.env`:

```env
# Use strong passwords
POSTGRES_PASSWORD=<strong-password>

# Restrict CORS in docker-compose.yml
# Update the api service environment:
CORS_ORIGINS=https://yourdomain.com

# Use HTTPS (add reverse proxy like nginx)
```

### 2. Performance Tuning

```yaml
# In docker-compose.yml, adjust resources:
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
  
  ollama:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
        reservations:
          cpus: '2'
          memory: 8G
```

### 3. Monitoring

Add monitoring services to docker-compose.yml:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    # ... configuration

  grafana:
    image: grafana/grafana:latest
    # ... configuration
```

## Troubleshooting

### Issue: Services won't start

```bash
# Check logs
docker-compose logs

# Check disk space
df -h

# Check memory
docker stats
```

### Issue: Ollama models not loading

```bash
# Manually pull models
docker-compose run --rm ollama-pull

# Or directly
docker exec -it agentic-ollama ollama pull qwen3:4b
```

### Issue: Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker exec -it agentic-postgres psql -U ai -d ai -c "SELECT 1"

# Reset database (CAUTION: deletes data)
docker-compose down -v
docker-compose up -d
```

### Issue: Out of memory

```bash
# Use smaller models
AGENTIC_MODEL_ID=qwen2:0.5b docker-compose up -d

# Or increase Docker memory allocation
# Docker Desktop: Settings > Resources > Memory
```

## Building Custom Image

### Build for Different Architectures

```bash
# Build for ARM64 (Apple Silicon)
docker buildx build --platform linux/arm64 -t agentic-api:arm64 .

# Build for AMD64 (Intel/AMD)
docker buildx build --platform linux/amd64 -t agentic-api:amd64 .

# Build multi-platform
docker buildx build --platform linux/amd64,linux/arm64 -t agentic-api:latest .
```

### Push to Registry

```bash
# Tag image
docker tag agentic-api:latest your-registry/agentic-api:latest

# Push to registry
docker push your-registry/agentic-api:latest

# Update docker-compose.yml
# Change: build: .
# To: image: your-registry/agentic-api:latest
```

## Environment Variables Reference

All environment variables can be set in `.env` or docker-compose.yml:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTIC_DB_URL` | postgresql://... | Database connection URL |
| `AGENTIC_MODEL_ID` | qwen3:4b | Main chat model |
| `AGENTIC_EMBEDDER_MODEL` | nomic-embed-text | Embedding model |
| `AGENTIC_RESPONSE_MODEL` | qwen2.5:7b-instruct | Response formatting model |
| `AGENTIC_CACHE_ENABLED` | true | Enable semantic cache |
| `AGENTIC_LOG_LEVEL` | INFO | Logging level |
| `AGENTIC_MAX_FILE_SIZE` | 10485760 | Max upload size (bytes) |

## Backup and Restore

### Backup Database

```bash
# Backup PostgreSQL
docker exec agentic-postgres pg_dump -U ai ai > backup.sql

# Backup Ollama models
docker run --rm -v agentic_ollama_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/ollama-backup.tar.gz -C /data .

# Backup PDFs
tar czf docs-backup.tar.gz docs/
```

### Restore Database

```bash
# Restore PostgreSQL
docker exec -i agentic-postgres psql -U ai ai < backup.sql

# Restore Ollama models
docker run --rm -v agentic_ollama_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/ollama-backup.tar.gz -C /data

# Restore PDFs
tar xzf docs-backup.tar.gz
```

## Development Mode

For development with hot reload:

```bash
# Mount source code as volume (add to docker-compose.yml)
services:
  api:
    volumes:
      - ./agentic_api.py:/home/appuser/app/agentic_api.py:ro
      - ./docs:/home/appuser/app/docs
    command: python -u agentic_api.py
    environment:
      AGENTIC_LOG_LEVEL: DEBUG
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Verify services: `docker-compose ps`
3. Test health endpoints
4. Review environment variables

## License

See LICENSE file in the repository root.