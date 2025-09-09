# 🐳 Agentic API - Docker Setup

Deploy the Agentic RAG API with one command using Docker!

## 🚀 Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-repo/knowledge-graph-rag.git
cd knowledge-graph-rag/agentic

# 2. Start all services
./docker-start.sh

# 3. Test the API
curl http://localhost:8000/health
```

That's it! The API is now running at http://localhost:8000

## 📦 What's Included

The Docker setup includes everything you need:

- ✅ **Agentic API** - The main RAG application
- ✅ **PostgreSQL + pgvector** - Database with vector search
- ✅ **Ollama** - Local LLM models (no external API needed!)
- ✅ **Auto-configuration** - Models download automatically
- ✅ **Health checks** - Services monitor themselves
- ✅ **Persistent storage** - Your data is safe between restarts

## 🛠️ Installation Options

### Option 1: Using the Quick Start Script (Recommended)

```bash
# Start services
./docker-start.sh start

# View logs
./docker-start.sh logs

# Stop services
./docker-start.sh stop

# Get help
./docker-start.sh help
```

### Option 2: Using Docker Compose Directly

```bash
# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 3: Build from Source

```bash
# Build and start
docker-compose up -d --build

# Or build specific image
docker build -t agentic-api .
```

## 📝 Configuration

### Basic Configuration

Create a `.env` file (or copy from `.env.example`):

```env
# Use smaller models for testing (faster)
AGENTIC_MODEL_ID=qwen2:0.5b
AGENTIC_EMBEDDER_MODEL=nomic-embed-text
AGENTIC_RESPONSE_MODEL=qwen2:0.5b

# Or use larger models for better quality
AGENTIC_MODEL_ID=qwen3:4b
AGENTIC_RESPONSE_MODEL=qwen2.5:7b-instruct

# Enable debug logging
AGENTIC_LOG_LEVEL=DEBUG
```

### Memory Requirements

| Model Size | RAM Required | Recommended |
|------------|--------------|-------------|
| 0.5B params | 2GB | Testing |
| 4B params | 4GB | Development |
| 7B params | 8GB | Production |
| 14B params | 16GB | High Quality |

## 📚 Usage Examples

### Upload a PDF Document

```bash
curl -X POST "http://localhost:8000/upload-pdf" \
  -F "file=@document.pdf"
```

### Ask Questions

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What insurance products are available?",
    "search_knowledge": true
  }'
```

### Python Client Example

```python
import httpx

async def chat_with_api():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/chat",
            json={
                "message": "Tell me about life insurance",
                "search_knowledge": True,
                "format_response": True
            }
        )
        print(response.json()["response"])
```

## 🔍 Monitoring

### Check Service Status

```bash
# Quick status
./docker-start.sh status

# Detailed status
docker-compose ps

# Service health
curl http://localhost:8000/health
curl http://localhost:11434/api/tags
```

### View Logs

```bash
# All services
./docker-start.sh logs

# Specific service
./docker-start.sh logs api
./docker-start.sh logs ollama
./docker-start.sh logs postgres

# Follow logs in real-time
docker-compose logs -f api
```

## 🐛 Troubleshooting

### Problem: Services won't start

```bash
# Check Docker is running
docker version

# Check ports are available
lsof -i :8000
lsof -i :11434
lsof -i :5532

# Reset everything
./docker-start.sh clean
./docker-start.sh start
```

### Problem: Out of memory

```bash
# Use smaller models
echo "AGENTIC_MODEL_ID=qwen2:0.5b" >> .env
docker-compose restart api

# Check memory usage
docker stats
```

### Problem: Slow responses

```bash
# Enable cache
echo "AGENTIC_CACHE_ENABLED=true" >> .env

# Use faster models
echo "AGENTIC_MODEL_ID=qwen2:0.5b" >> .env

# Restart
docker-compose restart api
```

### Problem: Models not downloading

```bash
# Manual pull
docker-compose run --rm ollama-pull

# Or directly
docker exec -it agentic-ollama ollama pull qwen3:4b
```

## 🚢 Production Deployment

### 1. Use Environment Variables

```bash
# Production .env
AGENTIC_LOG_LEVEL=WARNING
POSTGRES_PASSWORD=strong_password_here
AGENTIC_CACHE_ENABLED=true
AGENTIC_CACHE_TTL_HOURS=48
```

### 2. Add SSL/TLS (nginx example)

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Resource Limits

Edit `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### 4. Backup Strategy

```bash
# Backup script
#!/bin/bash
docker exec postgres pg_dump -U ai ai > backup-$(date +%Y%m%d).sql
tar czf docs-backup-$(date +%Y%m%d).tar.gz docs/
```

## 📊 Performance Tips

1. **Enable Semantic Cache**: Reduces response time by 80% for repeated queries
2. **Use Appropriate Models**: Balance speed vs quality
3. **Add More Workers**: Scale horizontally with `docker-compose scale api=3`
4. **Optimize PostgreSQL**: Tune `shared_buffers` and `work_mem`
5. **Use SSD Storage**: Especially for Ollama models

## 🔧 Advanced Configuration

### Custom Ollama Models

```bash
# Pull custom model
docker exec -it agentic-ollama ollama pull llama2:13b

# Update .env
echo "AGENTIC_MODEL_ID=llama2:13b" >> .env

# Restart
docker-compose restart api
```

### External PostgreSQL

```env
# Use external database
AGENTIC_DB_URL=postgresql+psycopg://user:pass@external-db:5432/dbname
```

### GPU Support (NVIDIA)

```yaml
# In docker-compose.yml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## 📄 License

See LICENSE file in the repository.

## 🤝 Support

- **Issues**: GitHub Issues
- **Docs**: See DOCKER_GUIDE.md for detailed documentation
- **Logs**: Always check logs first: `./docker-start.sh logs`

---

**Happy Deploying! 🚀**