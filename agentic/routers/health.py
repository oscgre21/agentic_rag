"""
Router para health check y gestión de sesiones.
Siguiendo el principio de Single Responsibility.
"""

from fastapi import APIRouter, HTTPException

try:
    # Absolute imports for Docker/standalone execution
    from models.schemas import HealthResponse, SessionListResponse
    from core.dependencies import get_knowledge_service, get_agent_service
    from config.settings import settings
except ImportError:
    # Relative imports for package execution
    from ..models.schemas import HealthResponse, SessionListResponse
    from ..core.dependencies import get_knowledge_service, get_agent_service
    from ..config.settings import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and configuration"""
    try:
        knowledge_service = get_knowledge_service()
        doc_count = knowledge_service.get_document_count()
        
        return HealthResponse(
            status="healthy",
            model=settings.MODEL_ID,
            embedder=settings.EMBEDDER_MODEL,
            knowledge_base_loaded=True,
            documents_count=doc_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    """Listar todas las sesiones activas"""
    agent_service = get_agent_service()
    sessions = agent_service.get_active_sessions()
    
    return SessionListResponse(
        active_sessions=sessions,
        count=len(sessions)
    )


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Limpiar una sesión específica y su agente asociado"""
    agent_service = get_agent_service()
    
    if agent_service.remove_agent(session_id):
        return {"message": f"Sesión {session_id} eliminada exitosamente"}
    else:
        raise HTTPException(status_code=404, detail=f"Sesión {session_id} no encontrada")