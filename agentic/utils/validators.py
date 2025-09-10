"""
Validadores y verificaciones.
Siguiendo el principio de Single Responsibility.
"""

import logging
import requests
from typing import Tuple
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


def check_postgresql_connection(db_url: str) -> bool:
    """Verifica la conectividad con PostgreSQL"""
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión exitosa con PostgreSQL")
            return True
    except Exception as e:
        logger.error(f"❌ Error conectando con PostgreSQL: {e}")
        logger.error(f"   URL: {db_url}")
        logger.error("   Verifique que PostgreSQL esté ejecutándose y accesible")
        return False


def check_ollama_connection(ollama_host: str, model_id: str, embedder_model: str) -> Tuple[bool, list]:
    """Verifica la conectividad con Ollama y los modelos disponibles"""
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if response.status_code == 200:
            logger.info(f"✅ Conexión exitosa con Ollama en {ollama_host}")
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models if 'name' in m]
            
            if model_id not in model_names:
                logger.warning(f"⚠️ Modelo {model_id} no encontrado en Ollama")
                logger.info(f"   Modelos disponibles: {model_names}")
            
            if embedder_model not in model_names:
                logger.warning(f"⚠️ Embedder {embedder_model} no encontrado en Ollama")
            
            return True, model_names
        else:
            logger.error(f"❌ Error conectando con Ollama: Status {response.status_code}")
            return False, []
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ No se pudo conectar con Ollama en {ollama_host}")
        logger.error("   Verifique que Ollama esté ejecutándose y accesible")
        return False, []
    except Exception as e:
        logger.warning(f"⚠️ Error verificando Ollama: {e}")
        return False, []


def check_ollama_tools_support() -> bool:
    """
    Check if the current ollama version supports tools parameter.
    Returns True if tools are supported, False otherwise.
    """
    try:
        import ollama
        version = getattr(ollama, '__version__', '0.0.0')
        logger.info(f"Checking Ollama version: {version}")
        
        try:
            major, minor = map(int, version.split('.')[:2])
            supports_tools = (major > 0) or (major == 0 and minor >= 3)
            
            if not supports_tools:
                logger.warning(f"⚠️ Ollama version {version} does not support tools.")
                logger.warning("   Please upgrade: pip install ollama>=0.3.3")
            else:
                logger.info(f"✅ Ollama version {version} supports tools")
            
            return supports_tools
        except:
            logger.warning("⚠️ Could not determine ollama version. Assuming no tools support.")
            return False
            
    except ImportError:
        logger.error("❌ Ollama module not found")
        return False
    except Exception as e:
        logger.error(f"Error checking ollama tools support: {e}")
        return False