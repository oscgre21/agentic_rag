"""
Dependencias compartidas de la aplicación.
Siguiendo el principio de Dependency Injection.
"""

try:
    # Absolute imports for Docker/standalone execution
    from services.agent_service import AgentService
    from services.knowledge_service import KnowledgeService
    from services.cache_service import SemanticCache
    from utils.formatting import ResponseFormatter
except ImportError:
    # Relative imports for package execution
    from ..services.agent_service import AgentService
    from ..services.knowledge_service import KnowledgeService
    from ..services.cache_service import SemanticCache
    from ..utils.formatting import ResponseFormatter

# Instancias singleton de servicios
knowledge_service = None
agent_service = None
semantic_cache = None
response_formatter = None


def get_knowledge_service() -> KnowledgeService:
    """Obtiene la instancia del servicio de knowledge base"""
    global knowledge_service
    if knowledge_service is None:
        knowledge_service = KnowledgeService()
    return knowledge_service


def get_agent_service() -> AgentService:
    """Obtiene la instancia del servicio de agentes"""
    global agent_service
    if agent_service is None:
        kb = get_knowledge_service()
        agent_service = AgentService(knowledge_base=kb.knowledge_base)
    return agent_service


def get_semantic_cache() -> SemanticCache:
    """Obtiene la instancia del caché semántico"""
    global semantic_cache
    if semantic_cache is None:
        semantic_cache = SemanticCache(table_name="semantic_cache_ollama")
    return semantic_cache


def get_response_formatter() -> ResponseFormatter:
    """Obtiene la instancia del formateador de respuestas"""
    global response_formatter
    if response_formatter is None:
        response_formatter = ResponseFormatter()
    return response_formatter