# Refactoring de Agentic API - Documentación

## 🏗️ Nueva Estructura

La API ha sido refactorizada siguiendo los principios SOLID y Clean Architecture:

```
agentic/
├── app.py                    # Aplicación principal
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuración centralizada
├── models/
│   ├── __init__.py
│   └── schemas.py           # DTOs/Pydantic models
├── services/
│   ├── __init__.py
│   ├── agent_service.py    # Lógica de agentes
│   ├── knowledge_service.py # Manejo de knowledge base
│   └── cache_service.py    # SemanticCache
├── routers/
│   ├── __init__.py
│   ├── chat.py             # Endpoints de chat
│   ├── documents.py        # Endpoints de documentos
│   ├── cache.py            # Endpoints de cache
│   └── health.py           # Health check y sesiones
├── utils/
│   ├── __init__.py
│   ├── formatting.py       # Formateo de respuestas
│   ├── text_processing.py  # Procesamiento de texto
│   └── validators.py       # Validaciones
└── core/
    ├── __init__.py
    └── dependencies.py      # Dependencias compartidas
```

## 🎯 Principios SOLID Aplicados

### 1. **Single Responsibility Principle (SRP)**
- Cada módulo tiene una única responsabilidad
- `config/`: Solo configuración
- `models/`: Solo esquemas de datos
- `services/`: Lógica de negocio separada por dominio
- `routers/`: Solo manejo de endpoints
- `utils/`: Funciones auxiliares reutilizables

### 2. **Open/Closed Principle (OCP)**
- Extensible sin modificar código existente
- Nuevos servicios se pueden agregar sin cambiar los existentes
- Los routers son modulares y se pueden agregar nuevos

### 3. **Liskov Substitution Principle (LSP)**
- Interfaces consistentes en los servicios
- Los servicios pueden ser reemplazados por implementaciones alternativas

### 4. **Interface Segregation Principle (ISP)**
- Interfaces específicas para cada dominio
- No hay dependencias innecesarias entre módulos

### 5. **Dependency Inversion Principle (DIP)**
- Dependencias inyectadas a través de `core/dependencies.py`
- Los módulos de alto nivel no dependen de módulos de bajo nivel

## 📦 Módulos Principales

### Config (`config/`)
- **settings.py**: Configuración centralizada usando variables de entorno
- Manejo de logging
- Configuración de prompts

### Models (`models/`)
- **schemas.py**: Todos los DTOs/Pydantic models
- Validación de datos de entrada/salida
- Documentación automática de API

### Services (`services/`)
- **agent_service.py**: Gestión de agentes de IA
- **knowledge_service.py**: Manejo del knowledge base PDF
- **cache_service.py**: Caché semántico con PgVector

### Routers (`routers/`)
- **chat.py**: `/chat`, `/chat/simple`
- **documents.py**: `/documents`, `/upload-pdf`, `/reload-knowledge`
- **cache.py**: `/cache/stats`, `/cache/clear`, `/cache/config`
- **health.py**: `/health`, `/sessions`

### Utils (`utils/`)
- **formatting.py**: Formateo de respuestas con Ollama
- **text_processing.py**: Extracción de referencias, limpieza de texto
- **validators.py**: Validación de conexiones y configuraciones

### Core (`core/`)
- **dependencies.py**: Gestión de instancias singleton de servicios

## 🚀 Cómo Ejecutar

### Opción 1: Módulo Python
```bash
python -m agentic.app
```

### Opción 2: Script directo
```bash
cd agentic
python app.py
```

### Opción 3: Uvicorn
```bash
uvicorn agentic.app:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 Configuración

Todas las configuraciones están en `config/settings.py` y se leen de variables de entorno:

```bash
# Base de datos
AGENTIC_DB_URL=postgresql+psycopg://ai:ai@localhost:5532/ai

# Ollama
OLLAMA_HOST=http://localhost:11434
AGENTIC_MODEL_ID=qwen3:8b
AGENTIC_EMBEDDER_MODEL=nomic-embed-text:latest
AGENTIC_RESPONSE_MODEL=qwen2.5:7b-instruct

# Cache
AGENTIC_CACHE_ENABLED=true
AGENTIC_CACHE_SIMILARITY_THRESHOLD=0.88
AGENTIC_CACHE_TTL_HOURS=24

# Logging
AGENTIC_LOG_LEVEL=INFO
```

## 🧪 Testing

```python
# Test de importación
python -c "from agentic.app import app; print('OK')"

# Test de endpoints
curl http://localhost:8000/health
```

## 📝 Ventajas del Refactoring

1. **Mantenibilidad**: Código más fácil de mantener y entender
2. **Testabilidad**: Cada módulo se puede testear independientemente
3. **Escalabilidad**: Fácil agregar nuevas funcionalidades
4. **Reutilización**: Componentes reutilizables
5. **Separación de Concerns**: Clara separación de responsabilidades
6. **Dependency Injection**: Gestión flexible de dependencias
7. **Clean Architecture**: Arquitectura limpia y profesional

## 🔄 Migración desde la Versión Anterior

Si tienes código que usa `agentic_api.py`, no necesitas cambiar nada inmediatamente. 
El archivo original sigue funcionando pero mostrará un warning de deprecación.

Para migrar:
1. Cambia las importaciones de `agentic_api` a `agentic.app`
2. Los endpoints y funcionalidad permanecen iguales
3. La configuración sigue usando las mismas variables de entorno

## 📚 Documentación de API

La documentación automática de FastAPI está disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contribuir

Para agregar nuevas funcionalidades:
1. Crea nuevos servicios en `services/`
2. Define modelos en `models/schemas.py`
3. Agrega routers en `routers/`
4. Registra dependencias en `core/dependencies.py`
5. Incluye el router en `app.py`



python -m agentic.app 