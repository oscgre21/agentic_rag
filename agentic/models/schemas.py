"""
DTOs y modelos Pydantic para la API Agentic.
Siguiendo el principio de Single Responsibility.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class DocumentReference(BaseModel):
    """Referencia a un documento y página específica"""
    document_name: str = Field(..., description="Nombre del documento")
    pages: List[int] = Field(default=[], description="Páginas referenciadas")
    relevance_score: Optional[float] = Field(default=None, description="Score de relevancia")


class Message(BaseModel):
    """Mensaje en una conversación"""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Request para el endpoint de chat"""
    message: str = Field(..., description="Current user message")
    messages: Optional[List[Message]] = Field(default=[], description="Conversation history")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation continuity")
    search_knowledge: bool = Field(default=True, description="Whether to search knowledge base")
    stream: bool = Field(default=False, description="Whether to stream the response")
    format_response: bool = Field(default=True, description="Whether to apply formatting to response")
    custom_format_prompt: Optional[str] = Field(default=None, description="Custom formatting prompt to use")


class ChatResponse(BaseModel):
    """Response del endpoint de chat"""
    response: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    sources: Optional[List[Dict[str, Any]]] = Field(default=[], description="Sources used for the response")
    document_references: List[DocumentReference] = Field(default=[], description="Documentos y páginas consultadas")
    messages: List[Message] = Field(..., description="Updated conversation history")
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Response del health check"""
    status: str
    model: str
    embedder: str
    knowledge_base_loaded: bool
    documents_count: Optional[int] = None


class FileUploadResponse(BaseModel):
    """Response de subida de archivo"""
    filename: str
    size: int
    message: str
    knowledge_base_updated: bool
    total_documents: int


class SessionListResponse(BaseModel):
    """Response de listado de sesiones"""
    active_sessions: List[str]
    count: int


class DocumentListResponse(BaseModel):
    """Response de listado de documentos"""
    documents: List[Dict[str, Any]]
    total: int


class CacheStatsResponse(BaseModel):
    """Response de estadísticas del caché"""
    cache_enabled: bool
    stats: Dict[str, Any]
    configuration: Dict[str, Any]


class CacheConfigRequest(BaseModel):
    """Request para actualizar configuración del caché"""
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    ttl_hours: Optional[int] = Field(None, gt=0)