"""
Configuración centralizada de la aplicación.
Siguiendo el principio de Single Responsibility - solo maneja configuración.
"""

import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class Settings:
    """Configuración principal de la aplicación"""
    
    # Database
    DB_URL: str = os.environ.get("AGENTIC_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai")
    
    # Ollama
    OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    MODEL_ID: str = os.environ.get("AGENTIC_MODEL_ID", "qwen3:8b")
    EMBEDDER_MODEL: str = os.environ.get("AGENTIC_EMBEDDER_MODEL", "nomic-embed-text:latest")
    RESPONSE_MODEL: str = os.environ.get("AGENTIC_RESPONSE_MODEL", "qwen2.5:7b-instruct")
    
    # Cache Configuration
    CACHE_ENABLED: bool = os.environ.get("AGENTIC_CACHE_ENABLED", "true").lower() == "true"
    CACHE_SIMILARITY_THRESHOLD: float = float(os.environ.get("AGENTIC_CACHE_SIMILARITY_THRESHOLD", "0.88"))
    CACHE_TTL_HOURS: int = int(os.environ.get("AGENTIC_CACHE_TTL_HOURS", "24"))
    CACHE_MAX_ENTRIES: int = int(os.environ.get("AGENTIC_CACHE_MAX_ENTRIES", "1000"))
    
    # File Upload
    MAX_FILE_SIZE: int = int(os.environ.get("AGENTIC_MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB default
    ALLOWED_EXTENSIONS: set = {".pdf"}
    
    # Paths
    DOCS_PATH: Path = Path("docs")
    
    # Logging
    LOG_LEVEL: str = os.environ.get("AGENTIC_LOG_LEVEL", "INFO").upper()
    
    # Default Formatting Prompt
    DEFAULT_FORMATTING_PROMPT: str = """
You are an expert assistant specializing in clear, professional communication for insurance content.

Your task is to transform the following insurance response into a well-structured, user-friendly format that:

**STRUCTURE & CLARITY:**
- Creates a logical flow with clear sections and subsections
- Uses descriptive, scannable headings that preview the content
- Breaks down complex information into digestible chunks
- Ensures smooth transitions between topics

**FORMATTING REQUIREMENTS:**
- Apply proper markdown formatting (headers, lists, tables, code blocks when useful)
- Use **bold text** for key terms, important exclusions, and critical information
- Implement bullet points and numbered lists for better readability
- Add relevant emojis strategically (📋 📄 ✅ ⚠️ 💰 🚫 📍 💡) to enhance visual appeal

**CONTENT STANDARDS:**
- Use clear, jargon-free language while keeping technical accuracy
- Add practical examples where helpful
- Include actionable takeaways or next steps when appropriate
- Highlight potential gotchas or important caveats with warning callouts

**TONE & STYLE:**
- Professional yet approachable and conversational
- Helpful and informative without being condescending
- Confident and authoritative on insurance matters
 

This is the information collected about the user:
[{response}]

Base on the information below respond this question from user:
{question}

- Transform this into a polished, professional response that insurance customers will find easy to understand and act upon. 
- Avoid using markdown formatting in your answer.
- REMEMBER to respond in the same language as the question.
"""
    
    @classmethod
    def get_formatting_prompt(cls) -> str:
        """Obtiene el prompt de formateo, puede ser personalizado o default"""
        return os.environ.get("AGENTIC_FORMATTING_PROMPT", cls.DEFAULT_FORMATTING_PROMPT)


class LogConfig:
    """Configuración de logging"""
    
    @staticmethod
    def setup_logging():
        """Configura el sistema de logging"""
        settings = Settings()
        
        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Configurar logging para phi
        phi_logger = logging.getLogger("phi")
        phi_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        
        return logging.getLogger(__name__)


# Instancia singleton de configuración
settings = Settings()