"""
Aplicación principal de la API Agentic.
Siguiendo principios SOLID y Clean Architecture.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Use absolute imports when running as main module
try:
    from config.settings import LogConfig, settings
    from routers import health, chat, documents, cache
    from utils.validators import check_postgresql_connection, check_ollama_connection
except ImportError:
    # Use relative imports when imported as package
    from .config.settings import LogConfig, settings
    from .routers import health, chat, documents, cache
    from .utils.validators import check_postgresql_connection, check_ollama_connection

# Configurar logging
logger = LogConfig.setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación"""
    # Startup
    logger.info("🚀 Iniciando Insurance Knowledge Base API...")
    
    # Verificar configuración
    logger.info(f"📋 Configuración cargada:")
    logger.info(f"   Ollama Host: {settings.OLLAMA_HOST}")
    logger.info(f"   Model ID: {settings.MODEL_ID}")
    logger.info(f"   Embedder: {settings.EMBEDDER_MODEL}")
    logger.info(f"   Cache: {'Habilitado' if settings.CACHE_ENABLED else 'Deshabilitado'}")
    
    # Verificar conexiones
    check_postgresql_connection(settings.DB_URL)
    check_ollama_connection(
        settings.OLLAMA_HOST, 
        settings.MODEL_ID, 
        settings.EMBEDDER_MODEL
    )
    
    logger.info("✅ API iniciada exitosamente")
    
    yield  # La aplicación se ejecuta aquí
    
    # Shutdown
    logger.info("👋 Cerrando Insurance Knowledge Base API...")


# Inicializar FastAPI app con lifespan
app = FastAPI(
    title="Insurance Knowledge Base API",
    description="API para consultas sobre documentos de seguros usando RAG con Ollama",
    version="2.0.0",  # Nueva versión refactorizada
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(documents.router, tags=["Documents"])
app.include_router(cache.router, tags=["Cache"])


@app.get("/chatbot", response_class=HTMLResponse, tags=["UI"])
async def serve_chatbot():
    """Serve the Flowise chatbot interface"""
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Insurance Knowledge Base - Chatbot</title>
    </head>
    <body>
        <h1>Insurance Knowledge Base Chatbot</h1>
        <script type="module">
            import Chatbot from "https://cdn.jsdelivr.net/npm/flowise-embed/dist/web.js"
            Chatbot.init({
                chatflowid: "b8da04ee-edd9-4158-8deb-5741e47eea4a",
                apiHost: "https://flowise.oscgre.com",
            })
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable reload in Docker
    )