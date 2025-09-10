"""
Router para gestión del caché semántico.
Siguiendo el principio de Single Responsibility.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from ..models.schemas import CacheStatsResponse, CacheConfigRequest
from ..core.dependencies import get_semantic_cache
from ..config.settings import settings

router = APIRouter(prefix="/cache")


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Obtener estadísticas del caché semántico"""
    semantic_cache = get_semantic_cache()
    
    return CacheStatsResponse(
        cache_enabled=settings.CACHE_ENABLED,
        stats=semantic_cache.get_stats(),
        configuration={
            "similarity_threshold": settings.CACHE_SIMILARITY_THRESHOLD,
            "ttl_hours": settings.CACHE_TTL_HOURS,
            "max_entries": settings.CACHE_MAX_ENTRIES
        }
    )


@router.post("/clear")
async def clear_cache():
    """Limpiar todo el caché semántico"""
    try:
        semantic_cache = get_semantic_cache()
        success = await semantic_cache.clear()
        
        if success:
            return {
                "message": "Caché limpiado exitosamente",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Error al limpiar el caché")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error limpiando caché: {str(e)}")


@router.post("/toggle")
async def toggle_cache(enabled: bool):
    """Habilitar o deshabilitar el caché semántico"""
    semantic_cache = get_semantic_cache()
    
    # Actualizar configuración global
    settings.CACHE_ENABLED = enabled
    semantic_cache.enabled = enabled
    
    return {
        "cache_enabled": settings.CACHE_ENABLED,
        "message": f"Caché {'habilitado' if enabled else 'deshabilitado'} exitosamente",
        "timestamp": datetime.now().isoformat()
    }


@router.put("/config")
async def update_cache_config(config: CacheConfigRequest):
    """Actualizar configuración del caché semántico"""
    semantic_cache = get_semantic_cache()
    
    if config.similarity_threshold is not None:
        settings.CACHE_SIMILARITY_THRESHOLD = config.similarity_threshold
        semantic_cache.similarity_threshold = config.similarity_threshold
    
    if config.ttl_hours is not None:
        settings.CACHE_TTL_HOURS = config.ttl_hours
        semantic_cache.ttl_hours = config.ttl_hours
    
    return {
        "configuration": {
            "similarity_threshold": settings.CACHE_SIMILARITY_THRESHOLD,
            "ttl_hours": settings.CACHE_TTL_HOURS,
            "max_entries": settings.CACHE_MAX_ENTRIES
        },
        "message": "Configuración actualizada exitosamente",
        "timestamp": datetime.now().isoformat()
    }