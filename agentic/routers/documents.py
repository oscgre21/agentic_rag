"""
Router para gestión de documentos.
Siguiendo el principio de Single Responsibility.
"""

import shutil
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from ..models.schemas import DocumentListResponse, FileUploadResponse
from ..core.dependencies import get_knowledge_service, get_semantic_cache, get_agent_service
from ..config.settings import settings

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """Listar documentos cargados en el knowledge base"""
    knowledge_service = get_knowledge_service()
    docs = knowledge_service.get_documents_list()
    
    return DocumentListResponse(
        documents=docs,
        total=len(docs)
    )


@router.post("/upload-pdf", response_model=FileUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Subir un archivo PDF y actualizar la base de conocimiento.
    """
    try:
        # Validar extensión
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Tipo de archivo no permitido. Solo se aceptan archivos PDF."
            )
        
        # Validar tamaño
        contents = await file.read()
        file_size = len(contents)
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande. Tamaño máximo: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío"
            )
        
        # Crear directorio si no existe
        settings.DOCS_PATH.mkdir(exist_ok=True)
        
        # Generar nombre único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}".replace(" ", "_")
        file_path = settings.DOCS_PATH / safe_filename
        
        # Verificar si existe
        original_path = settings.DOCS_PATH / file.filename
        if original_path.exists():
            backup_path = settings.DOCS_PATH / f"backup_{timestamp}_{file.filename}"
            shutil.move(str(original_path), str(backup_path))
            print(f"Archivo existente movido a: {backup_path}")
        
        # Guardar archivo
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        print(f"Archivo guardado: {file_path}")
        
        # Actualizar knowledge base
        knowledge_service = get_knowledge_service()
        semantic_cache = get_semantic_cache()
        agent_service = get_agent_service()
        
        try:
            knowledge_service.add_document(file_path)
            print("Knowledge base actualizado exitosamente")
            
            # Limpiar caché
            if semantic_cache.enabled:
                await semantic_cache.clear()
                print("Caché semántico limpiado")
            
            # Limpiar agentes
            agent_service.clear_all_agents()
            
            kb_updated = True
        except Exception as kb_error:
            print(f"Advertencia: Error actualizando knowledge base: {kb_error}")
            kb_updated = False
        
        return FileUploadResponse(
            filename=file.filename,
            size=file_size,
            message=f"Archivo '{file.filename}' subido exitosamente",
            knowledge_base_updated=kb_updated,
            total_documents=knowledge_service.get_document_count()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error procesando archivo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el archivo: {str(e)}"
        )


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Eliminar un documento PDF del sistema"""
    try:
        knowledge_service = get_knowledge_service()
        semantic_cache = get_semantic_cache()
        agent_service = get_agent_service()
        
        # Eliminar documento
        knowledge_service.remove_document(filename)
        
        # Limpiar caché y agentes
        if semantic_cache.enabled:
            await semantic_cache.clear()
        agent_service.clear_all_agents()
        
        return {
            "message": f"Archivo '{filename}' eliminado exitosamente",
            "remaining_documents": knowledge_service.get_document_count()
        }
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Archivo '{filename}' no encontrado"
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando archivo: {str(e)}"
        )


@router.post("/reload-knowledge")
async def reload_knowledge_base():
    """Recargar el knowledge base con los documentos actuales"""
    try:
        knowledge_service = get_knowledge_service()
        agent_service = get_agent_service()
        
        knowledge_service.reload_knowledge_base()
        agent_service.clear_all_agents()
        
        return {
            "message": "Knowledge base recargado exitosamente",
            "documents_loaded": knowledge_service.get_document_count()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error recargando knowledge base: {str(e)}"
        )