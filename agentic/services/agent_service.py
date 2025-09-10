"""
Servicio para manejo de agentes de IA.
Siguiendo el principio de Single Responsibility - solo maneja agentes.
"""

import uuid
import logging
from typing import Dict, List, Optional, Tuple
from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.model.message import Message as PhiMessage
from phi.storage.agent.postgres import PgAgentStorage

from ..config.settings import settings
from ..models.schemas import Message
from ..utils.validators import check_ollama_tools_support

logger = logging.getLogger(__name__)


class OllamaNoTools(Ollama):
    """Ollama model without tools support for compatibility"""
    
    def invoke(self, messages, **kwargs):
        kwargs.pop('tools', None)
        kwargs.pop('tool_choice', None)
        return super().invoke(messages, **kwargs)
    
    def response(self, messages, **kwargs):
        kwargs.pop('tools', None)
        kwargs.pop('tool_choice', None)
        return super().response(messages, **kwargs)


class AgentService:
    """
    Servicio para gestionar agentes de IA.
    Implementa el patrón de repositorio para agentes.
    """
    
    def __init__(self, knowledge_base=None):
        self.active_agents: Dict[str, Agent] = {}
        self.knowledge_base = knowledge_base
        self.ollama_supports_tools = check_ollama_tools_support()
        
    def get_or_create_agent(self, session_id: str = None, 
                           messages: List[Message] = None) -> Tuple[Agent, str]:
        """
        Obtiene un agente existente o crea uno nuevo para la sesión.
        
        Args:
            session_id: ID de sesión opcional
            messages: Historial de mensajes opcional
            
        Returns:
            Tupla con el agente y el ID de sesión
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if session_id not in self.active_agents:
            self._create_agent(session_id)
        
        agent = self.active_agents[session_id]
        
        # Actualizar historial si se proporcionan mensajes
        if messages:
            self._update_agent_history(agent, messages)
        
        return agent, session_id
    
    def _create_agent(self, session_id: str):
        """Crea un nuevo agente para la sesión"""
        try:
            if not self.knowledge_base:
                logger.warning("⚠️ Knowledge base no está disponible para el agente")
            
            # Crear modelo según soporte de tools
            if not self.ollama_supports_tools:
                logger.warning("Creating Ollama model WITHOUT tools support")
                ollama_model = OllamaNoTools(id=settings.MODEL_ID, host=settings.OLLAMA_HOST)
                ollama_model.tools = None
                ollama_model.tool_choice = None
            else:
                ollama_model = Ollama(id=settings.MODEL_ID, host=settings.OLLAMA_HOST)
            
            agent = Agent(
                name=f"Insurance Agent - {session_id[:8]}",
                agent_id=f"insurance-agent-{session_id}",
                model=ollama_model,
                knowledge=self.knowledge_base if self.ollama_supports_tools else None,
                search_knowledge=self.ollama_supports_tools,
                read_chat_history=True,
                storage=PgAgentStorage(
                    table_name="insurance_api_sessions",
                    db_url=settings.DB_URL
                ),
                instructions=self._get_agent_instructions(),
                markdown=True,
                show_tool_calls=True,
                debug_mode=True,
                monitoring=True,
            )
            
            self.active_agents[session_id] = agent
            logger.debug(f"✅ Agente creado exitosamente para sesión: {session_id[:8]}")
            
        except Exception as e:
            logger.error(f"Error creando agente: {e}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            raise
    
    def _get_agent_instructions(self) -> List[str]:
        """Obtiene las instrucciones para el agente según configuración"""
        if self.ollama_supports_tools:
            return [
                "For the provided topic, run 3 different searches.",
                "Read the results carefully and prepare a worthy report.",
                "Focus on facts and make sure to provide references.",
                "If the knowledge base is empty or unavailable, provide a helpful response indicating this.",
            ]
        else:
            return [
                "Provide helpful information based on the query.",
                "Be informative and professional.",
                "Provide clear and accurate information.",
                "If the knowledge base is empty or unavailable, provide a helpful response indicating this.",
            ]
    
    def _update_agent_history(self, agent: Agent, messages: List[Message]):
        """Actualiza el historial del agente con mensajes previos"""
        for msg in messages[:-1]:  # Todos menos el último (que es el actual)
            phi_msg = PhiMessage(
                role=msg.role,
                content=msg.content
            )
            if not hasattr(agent, 'messages'):
                agent.messages = []
            agent.messages.append(phi_msg)
    
    def remove_agent(self, session_id: str) -> bool:
        """
        Elimina un agente de la sesión.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            True si se eliminó, False si no existía
        """
        if session_id in self.active_agents:
            del self.active_agents[session_id]
            return True
        return False
    
    def clear_all_agents(self):
        """Limpia todos los agentes activos"""
        self.active_agents.clear()
    
    def get_active_sessions(self) -> List[str]:
        """Obtiene la lista de sesiones activas"""
        return list(self.active_agents.keys())
    
    def run_agent(self, session_id: str, context: str, stream: bool = False):
        """
        Ejecuta un agente con el contexto dado.
        
        Args:
            session_id: ID de la sesión
            context: Contexto/mensaje para el agente
            stream: Si hacer streaming de la respuesta
            
        Returns:
            Respuesta del agente
        """
        if session_id not in self.active_agents:
            raise ValueError(f"No se encontró agente para sesión {session_id}")
        
        agent = self.active_agents[session_id]
        
        if stream:
            response_text = ""
            for chunk in agent.run(context, stream=True):
                if hasattr(chunk, 'content'):
                    response_text += chunk.content
            return response_text
        else:
            logger.debug(f"Ejecutando agent.run() para: {context[:100]}...")
            response = agent.run(context)
            response_text = response.content if hasattr(response, 'content') else str(response)
            logger.debug(f"Agent.run() completado exitosamente")
            return response