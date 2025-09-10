"""
Router para endpoints de chat.
Siguiendo el principio de Single Responsibility.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException

try:
    # Absolute imports for Docker/standalone execution
    from models.schemas import ChatRequest, ChatResponse, Message, DocumentReference
    from core.dependencies import (
        get_agent_service, 
        get_semantic_cache, 
        get_response_formatter
    )
    from utils.text_processing import extract_document_references, remove_think_blocks
    from utils.validators import check_ollama_tools_support
    from config.settings import settings
except ImportError:
    # Relative imports for package execution
    from ..models.schemas import ChatRequest, ChatResponse, Message, DocumentReference
    from ..core.dependencies import (
        get_agent_service, 
        get_semantic_cache, 
        get_response_formatter
    )
    from ..utils.text_processing import extract_document_references, remove_think_blocks
    from ..utils.validators import check_ollama_tools_support
    from ..config.settings import settings

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal para consultas al knowledge base.
    Soporta historial de conversación y sesiones persistentes.
    """
    try:
        agent_service = get_agent_service()
        semantic_cache = get_semantic_cache()
        response_formatter = get_response_formatter()
        
        # Obtener o crear agente para la sesión
        agent, session_id = agent_service.get_or_create_agent(
            request.session_id, 
            request.messages
        )
        
        context = request.message
        
        # Configurar búsqueda en knowledge base
        ollama_supports_tools = check_ollama_tools_support()
        if request.search_knowledge and not ollama_supports_tools:
            print("⚠️ Knowledge base search requested but ollama doesn't support tools.")
            agent.search_knowledge = False
        else:
            agent.search_knowledge = request.search_knowledge
        
        print(f"\n{'='*60}")
        print(f"🔍 Procesando consulta: {request.message[:300]}...")
        print(f"📚 Búsqueda en knowledge base: {request.search_knowledge}")
        print(f"🆔 Session ID: {session_id[:8]}...")
        
        # Intentar obtener del caché
        cached_response = None
        cache_used = False
        response = None
        document_references = []
        
        if settings.CACHE_ENABLED and request.search_knowledge and not request.stream:
            cached_response = await semantic_cache.find_similar(
                query=request.message,
                context=context[:500]
            )
            
            if cached_response:
                response_text = cached_response["response"]
                cache_used = True
                
                # Reconstruir references desde caché
                if 'document_references' in cached_response:
                    cached_refs = cached_response['document_references']
                    document_references = [
                        DocumentReference(
                            document_name=ref['document_name'],
                            pages=ref['pages']
                        ) for ref in cached_refs
                    ]
                    print(f"🚀 Usando respuesta cacheada")
                    print(f"   Referencias recuperadas: {len(document_references)} documentos")
                else:
                    cache_used = False
                    print("⚠️ Cache sin referencias, ejecutando agente...")
        
        # Si no hay caché, ejecutar el agente
        if not cache_used:
            try:
                response_obj = agent_service.run_agent(session_id, context, request.stream)
                
                if request.stream:
                    response_text = response_obj
                else:
                    response = response_obj
                    response_text = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
                    
            except Exception as agent_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error ejecutando el agente: {str(agent_error)}"
                )
            
            print(f"✅ Respuesta generada - Longitud: {len(response_text)} caracteres")
            
            # Extraer referencias
            response_with_refs, document_references = extract_document_references(response_text)
        else:
            response_with_refs = response_text
            print(f"✅ Respuesta del caché - Longitud: {len(response_text)} caracteres")
        
        # Almacenar en caché si es necesario
        if not cache_used and settings.CACHE_ENABLED and request.search_knowledge and not request.stream:
            cache_metadata = {
                "session_id": session_id,
                "model": settings.MODEL_ID,
                "timestamp": datetime.now().isoformat()
            }
            
            if response and hasattr(response, 'sources'):
                cache_metadata["sources"] = response.sources
            
            await semantic_cache.store(
                query=request.message,
                response=response_text,
                context=context[:500],
                metadata=cache_metadata,
                document_references=document_references
            )
        
        # Log de documentos
        if document_references:
            print(f"\n📄 Documentos consultados ({len(document_references)} documentos):")
            for ref in document_references:
                pages_str = ', '.join(map(str, ref.pages))
                print(f"   - {ref.document_name}: Páginas {pages_str}")
        else:
            print("⚠️ No se encontraron referencias a documentos")
        
        # Limpiar y formatear respuesta
        response_with_refs = remove_think_blocks(response_with_refs)
        
        # Aplicar formateo si está habilitado
        formatted_response = response_with_refs
        if request.format_response and request.search_knowledge:
            formatted_response = response_formatter.format_response(
                request.message, 
                response_text
            )
        
        # Actualizar historial
        updated_messages = request.messages.copy() if request.messages else []
        updated_messages.append(Message(role="user", content=request.message))
        updated_messages.append(Message(role="assistant", content=formatted_response))
        
        # Extraer fuentes
        sources = []
        if response and hasattr(response, 'sources'):
            sources = response.sources
            if sources:
                print(f"\n🔎 Fuentes del agente ({len(sources)} fuentes)")
        elif cache_used and cached_response and 'metadata' in cached_response:
            sources = cached_response['metadata'].get('sources', [])
        
        # Log resumen
        print(f"\n{'='*60}")
        print(f"📊 Resumen de la respuesta:")
        print(f"   - Longitud original: {len(response_text)} caracteres")
        print(f"   - Longitud formateada: {len(formatted_response)} caracteres")
        print(f"   - Referencias encontradas: {len(document_references)}")
        print(f"   - Fuentes del agente: {len(sources)}")
        print(f"   - 🚀 Caché usado: {'SÍ' if cache_used else 'NO'}")
        
        if settings.CACHE_ENABLED:
            cache_stats = semantic_cache.get_stats()
            print(f"   - 📈 Cache Hit Rate: {cache_stats['hit_rate']}")
            print(f"   - 📊 Total consultas: {cache_stats['total_queries']}")
        print(f"{'='*60}\n")
        
        return ChatResponse(
            response=formatted_response,
            session_id=session_id,
            sources=sources,
            document_references=document_references,
            messages=updated_messages,
            metadata={
                "model": settings.MODEL_ID,
                "knowledge_search": request.search_knowledge,
                "timestamp": datetime.now().isoformat(),
                "formatted": request.format_response and request.search_knowledge,
                "original_length": len(response_text),
                "formatted_length": len(formatted_response),
                "references_found": len(document_references),
                "cache_used": cache_used,
                "cache_similarity": cached_response["similarity"] if cache_used and cached_response else None,
                "cache_stats": semantic_cache.get_stats() if settings.CACHE_ENABLED else None
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")


@router.post("/chat/simple")
async def simple_chat(message: str):
    """
    Endpoint simplificado para consultas rápidas sin manejo de sesión.
    """
    try:
        agent_service = get_agent_service()
        agent, session_id = agent_service.get_or_create_agent()
        response = agent_service.run_agent(session_id, message)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        return {
            "response": response_text,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")