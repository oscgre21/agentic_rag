# 🐳 Agentic API - Docker Setup

## 📦 Estructura Docker Actualizada

La aplicación ha sido refactorizada y el Dockerfile actualizado para usar la nueva estructura modular:

```
agentic/
├── app.py                 # Aplicación principal
├── config/                # Configuración
├── models/                # Esquemas de datos
├── services/              # Lógica de negocio
├── routers/               # Endpoints API
├── utils/                 # Utilidades
├── core/                  # Dependencias
├── Dockerfile             # Imagen Docker
├── docker-compose.yml     # Orquestación
└── .dockerignore          # Archivos excluidos
```

## 🚀 Quick Start

### Opción 1: Docker Compose (Recomendado)

```bash
# Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f api

# Detener
docker-compose down
```

### Opción 2: Docker Build & Run

```bash
# Construir imagen
docker build -t agentic-api:latest .

# Ejecutar contenedor
docker run -d \
  --name agentic-api \
  -p 8000:8000 \
  -v $(pwd)/docs:/home/appuser/app/docs \
  -e AGENTIC_DB_URL='postgresql+psycopg://ai:ai@host.docker.internal:5532/ai' \
  -e OLLAMA_HOST='http://host.docker.internal:11434' \
  --add-host host.docker.internal:host-gateway \
  agentic-api:latest
```

### Opción 3: Script de Build

```bash
# Usar el script de build incluido
./build-docker.sh
```

## 🔧 Configuración

### Variables de Entorno

```bash
# Base de datos PostgreSQL
AGENTIC_DB_URL=postgresql+psycopg://ai:ai@host.docker.internal:5532/ai

# Ollama (LLM)
OLLAMA_HOST=http://host.docker.internal:11434
AGENTIC_MODEL_ID=qwen3:8b
AGENTIC_EMBEDDER_MODEL=nomic-embed-text:latest
AGENTIC_RESPONSE_MODEL=qwen2.5:7b-instruct

# Cache Semántico
AGENTIC_CACHE_ENABLED=true
AGENTIC_CACHE_SIMILARITY_THRESHOLD=0.88
AGENTIC_CACHE_TTL_HOURS=24
AGENTIC_CACHE_MAX_ENTRIES=1000

# Archivos
AGENTIC_MAX_FILE_SIZE=10485760  # 10MB

# Logging
AGENTIC_LOG_LEVEL=INFO
```

### Archivo .env

Crea un archivo `.env` en el directorio `agentic/`:

```env
# Configuración de producción
AGENTIC_DB_URL=postgresql+psycopg://user:pass@postgres:5432/dbname
OLLAMA_HOST=http://ollama:11434
AGENTIC_MODEL_ID=llama2:latest
AGENTIC_LOG_LEVEL=INFO
```

## 📁 Volúmenes

El contenedor expone los siguientes volúmenes:

- `/home/appuser/app/docs`: Directorio para documentos PDF

```bash
# Montar directorio local de documentos
docker run -v /path/to/your/pdfs:/home/appuser/app/docs ...
```

## 🔍 Health Check

El contenedor incluye un health check automático:

```bash
# Verificar estado del contenedor
docker ps
docker inspect agentic-api --format='{{.State.Health.Status}}'

# Verificar manualmente
curl http://localhost:8000/health
```

## 🌐 Endpoints Disponibles

- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/health
- **Chat**: POST http://localhost:8000/chat
- **Documents**: GET http://localhost:8000/documents
- **Upload**: POST http://localhost:8000/upload-pdf
- **Cache Stats**: GET http://localhost:8000/cache/stats

## 🏗️ Arquitectura Docker

### Multi-stage Build

El Dockerfile usa una construcción multi-etapa para optimizar el tamaño:

1. **Builder Stage**: Compila dependencias
2. **Runtime Stage**: Imagen final optimizada

### Seguridad

- ✅ Usuario no-root (`appuser`)
- ✅ Imagen base slim
- ✅ Sin archivos innecesarios (.dockerignore)
- ✅ Health checks integrados

## 🐛 Debugging

### Ver Logs

```bash
# Con docker-compose
docker-compose logs -f api

# Con docker
docker logs -f agentic-api
```

### Acceder al Contenedor

```bash
# Shell interactivo
docker exec -it agentic-api /bin/bash

# Como root (para debugging)
docker exec -it --user root agentic-api /bin/bash
```

### Verificar Conectividad

```bash
# Verificar Ollama
docker exec agentic-api curl http://host.docker.internal:11434/api/tags

# Verificar PostgreSQL
docker exec agentic-api python -c "
from config.settings import settings
from utils.validators import check_postgresql_connection
check_postgresql_connection(settings.DB_URL)
"
```

## 🚢 Deployment

### Producción con Docker Compose

```yaml
version: '3.8'

services:
  api:
    image: agentic-api:latest
    container_name: agentic-api-prod
    environment:
      AGENTIC_DB_URL: ${DATABASE_URL}
      OLLAMA_HOST: ${OLLAMA_URL}
      AGENTIC_LOG_LEVEL: WARNING
    ports:
      - "80:8000"
    volumes:
      - ./docs:/home/appuser/app/docs
      - ./.env.prod:/home/appuser/app/.env:ro
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentic-api
  template:
    metadata:
      labels:
        app: agentic-api
    spec:
      containers:
      - name: api
        image: agentic-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: AGENTIC_DB_URL
          valueFrom:
            secretKeyRef:
              name: agentic-secrets
              key: db-url
        - name: OLLAMA_HOST
          value: "http://ollama-service:11434"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

## 📊 Monitoreo

### Prometheus Metrics

La aplicación puede exportar métricas para Prometheus:

```python
# Agregar en requirements.txt
prometheus-fastapi-instrumentator

# El endpoint /metrics estará disponible
```

### Logs Estructurados

Los logs están en formato JSON para facilitar el parsing:

```bash
docker logs agentic-api | jq '.'
```

## 🔄 CI/CD

### GitHub Actions

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Build Docker image
      run: |
        cd agentic
        docker build -t agentic-api:${{ github.sha }} .
    
    - name: Push to Registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push agentic-api:${{ github.sha }}
```

## 🆘 Troubleshooting

### Problema: No se conecta a Ollama

```bash
# Solución: Usar host.docker.internal
OLLAMA_HOST=http://host.docker.internal:11434
```

### Problema: No se conecta a PostgreSQL

```bash
# Verificar que PostgreSQL esté corriendo
pg_isready -h localhost -p 5532

# Usar la IP del host en lugar de localhost
AGENTIC_DB_URL=postgresql+psycopg://ai:ai@192.168.1.100:5532/ai
```

### Problema: Permisos en volúmenes

```bash
# Cambiar permisos del directorio
sudo chown -R 1000:1000 ./docs
```

## 📚 Referencias

- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI in Containers](https://fastapi.tiangolo.com/deployment/docker/)