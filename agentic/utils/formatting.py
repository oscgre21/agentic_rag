"""
Utilidades para formateo de respuestas.
Siguiendo el principio de Single Responsibility.
"""

import logging
from phi.model.ollama import Ollama
from phi.model.message import Message as PhiMessage

try:
    # Absolute imports for Docker/standalone execution
    from config.settings import settings
    from utils.text_processing import remove_think_blocks
except ImportError:
    # Relative imports for package execution
    from ..config.settings import settings
    from .text_processing import remove_think_blocks

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formatea las respuestas usando un modelo de Ollama"""
    
    def __init__(self):
        self.formatting_model = Ollama(
            id=settings.RESPONSE_MODEL, 
            host=settings.OLLAMA_HOST
        )
        self.formatting_prompt = settings.get_formatting_prompt()
    
    def format_response(self, message: str, response_text: str) -> str:
        """
        Aplica formateo a una respuesta usando el modelo configurado.
        
        Args:
            message: Mensaje original del usuario
            response_text: Texto de respuesta a formatear
            
        Returns:
            Respuesta formateada o la original si falla el formateo
        """
        try:
            format_prompt = self.formatting_prompt.format(
                question=message, 
                response=response_text
            )
            
            print("Aplicando formateo a la respuesta...")
            
            format_message = PhiMessage(role='user', content=format_prompt)
            format_result = self.formatting_model.response([format_message])
            
            formatted_response = format_result.content if hasattr(format_result, 'content') else str(format_result)
            formatted_response = remove_think_blocks(formatted_response)
            
            print(f"✨ Respuesta formateada exitosamente - Nueva longitud: {len(formatted_response)} caracteres")
            return formatted_response
            
        except Exception as e:
            print(f"Error al formatear respuesta: {e}")
            return response_text