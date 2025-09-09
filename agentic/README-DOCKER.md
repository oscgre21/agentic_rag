# Docker Setup for Agentic API

## Simplified Setup (API Only)

This setup runs only the Agentic API in Docker, connecting to external PostgreSQL and Ollama services.

### Prerequisites
- Docker and Docker Compose installed
- External PostgreSQL database running (e.g., on port 5532)
- External Ollama service running (e.g., on port 11434)

### Quick Start

1. **Build and run the container:**
```bash
docker-compose -f docker-compose-simple.yml up -d
```

2. **Check status:**
```bash
docker-compose -f docker-compose-simple.yml ps
docker-compose -f docker-compose-simple.yml logs
```

3. **Test the API:**
```bash
curl http://localhost:8000/health
```

### Configuration

Create a `.env` file with your configuration:

```env
# Database (external)
AGENTIC_DB_URL=postgresql+psycopg://ai:ai@host.docker.internal:5532/ai

# Ollama server (external)
OLLAMA_HOST=http://host.docker.internal:11434
AGENTIC_MODEL_ID=qwen3:4b
AGENTIC_EMBEDDER_MODEL=nomic-embed-text
AGENTIC_RESPONSE_MODEL=qwen2.5:7b-instruct

# Cache settings
AGENTIC_CACHE_ENABLED=true
AGENTIC_CACHE_SIMILARITY_THRESHOLD=0.88
AGENTIC_CACHE_TTL_HOURS=24
AGENTIC_CACHE_MAX_ENTRIES=1000

# Other settings
AGENTIC_MAX_FILE_SIZE=10485760
AGENTIC_LOG_LEVEL=INFO
```

### Files

- `docker-compose-simple.yml` - Docker Compose configuration (API only)
- `Dockerfile` - Multi-stage production Dockerfile
- `Dockerfile.simple` - Simplified Dockerfile for faster builds
- `requirements-minimal.txt` - Minimal dependencies for the API

### Volumes

The container mounts the following volumes:
- `./docs:/home/appuser/app/docs` - PDF documents directory
- `./.env:/home/appuser/app/.env:ro` - Environment configuration (read-only)

### Stopping the Container

```bash
docker-compose -f docker-compose-simple.yml down
```

### Troubleshooting

1. **Connection to external services:** The container uses `host.docker.internal` to connect to services on the host machine.

2. **Logs:** Check logs with:
```bash
docker-compose -f docker-compose-simple.yml logs -f
```

3. **Rebuild after changes:**
```bash
docker-compose -f docker-compose-simple.yml build --no-cache
docker-compose -f docker-compose-simple.yml up -d
```