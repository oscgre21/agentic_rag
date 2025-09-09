# Agentic RAG API

API de RAG (Retrieval-Augmented Generation) usando Phi Framework con Ollama y PostgreSQL.

## Requisitos

### Local
- Python 3.11+
- PostgreSQL con pgvector
- Ollama ejecutándose localmente

### Docker
- Docker y Docker Compose
- PostgreSQL externo con pgvector
- Ollama externo

## Instalación de Dependencias

### Opción 1: Instalación Local

```bash
# Instalar todas las dependencias incluyendo PDF
pip install -r requirements.txt

# O instalar solo las dependencias mínimas
pip install -r requirements-minimal.txt
```

### Opción 2: Docker (Recomendado)

```bash
# Construir y desplegar con verificación
./deploy.sh

# O manualmente
docker-compose build
docker-compose up -d
```

## Solución de Problemas

### Error: `pypdf` not installed

Este error ocurre cuando las librerías de procesamiento PDF no están instaladas correctamente.

**Solución para instalación local:**
```bash
pip install pypdf==5.4.0 pdfplumber==0.11.7 PyPDF2==3.0.1
```

**Solución para Docker:**
El Dockerfile ya incluye estas dependencias. Si persiste el error:

1. Reconstruir la imagen sin caché:
```bash
docker-compose build --no-cache
```

2. Verificar instalación:
```bash
docker-compose run --rm api python -c "import pypdf; print(pypdf.__version__)"
```

## Configuración

### Variables de Entorno

Crear un archivo `.env` basado en `.env.example`:

```env
# Base de datos
AGENTIC_DB_URL=postgresql+psycopg://user:pass@localhost:5432/dbname

# Ollama
OLLAMA_HOST=http://localhost:11434
AGENTIC_MODEL_ID=qwen3:4b
AGENTIC_EMBEDDER_MODEL=nomic-embed-text

# Caché
AGENTIC_CACHE_ENABLED=true
AGENTIC_CACHE_SIMILARITY_THRESHOLD=0.88

# Logging
AGENTIC_LOG_LEVEL=INFO
```

## Endpoints Principales

- `GET /health` - Estado de salud de la API
- `POST /chat` - Consulta con RAG
- `POST /upload-pdf` - Subir documento PDF
- `GET /documents` - Listar documentos
- `POST /cache/clear` - Limpiar caché semántico

## Scripts Útiles

- `./deploy.sh` - Despliegue completo con verificación
- `./build_docker.sh` - Solo construcción de imagen
- `./test_chat_endpoint.sh` - Prueba del endpoint de chat

## Verificación de Instalación

Para verificar que todas las dependencias PDF están instaladas correctamente:

```python
python -c "
import pypdf
import pdfplumber
import PyPDF2
print('✅ Todas las librerías PDF instaladas')
print(f'pypdf: {pypdf.__version__}')
"
```

## Logs y Depuración

Ver logs del contenedor:
```bash
docker-compose logs -f api
```

Verificar estado:
```bash
curl http://localhost:8000/health
```