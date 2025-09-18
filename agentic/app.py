"""
Aplicación principal de la API Agentic.
Siguiendo principios SOLID y Clean Architecture.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

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

# Montar la carpeta dist para servir archivos estáticos del chatbot
dist_path = Path(__file__).parent / "dist"
if dist_path.exists():
    app.mount("/dist", StaticFiles(directory=str(dist_path)), name="dist")
    logger.info(f"📁 Carpeta dist montada en /dist")



@app.get("/docs-files/", tags=["Files"])
async def list_docs_files():
    """Listar todos los archivos PDF en la carpeta docs"""
    docs_path = Path(__file__).parent / "docs"
    if not docs_path.exists():
        return {"error": "La carpeta docs no existe"}
    
    pdf_files = []
    for file in docs_path.glob("*.pdf"):
        pdf_files.append({
            "name": file.name,
            "size": file.stat().st_size,
            "url": f"/docs-files/{file.name}"
        })
    
    return {
        "total": len(pdf_files),
        "files": pdf_files
    }


@app.get("/docs-files/{filename}", tags=["Files"])
async def get_pdf_file(filename: str):
    """Descargar un archivo PDF específico de la carpeta docs como blob"""
    from fastapi import HTTPException, Response
    
    file_path = Path(__file__).parent / "docs" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    if not file_path.suffix.lower() == ".pdf":
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
    
    # Leer el archivo como bytes (blob)
    with open(file_path, "rb") as file:
        blob_data = file.read()
    
    return Response(
        content=blob_data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}"
        }
    )


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
            import Chatbot from "/dist/web.js"
            Chatbot.init({
                chatflowid: "6d7a2d52-e6a0-4bce-8b17-a061f423842c",
                apiHost: "https://flowise.oscgre.com",
                title: "BMI Insurance Knowledge Base",
                showTitle: true,
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