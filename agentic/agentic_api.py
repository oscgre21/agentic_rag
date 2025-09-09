from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import hashlib
import json
import os
import shutil
import aiofiles
import logging
import sys
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env
load_dotenv()

# Configurar logging
LOG_LEVEL = os.environ.get("AGENTIC_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configurar logging para phi (el framework del agente)
phi_logger = logging.getLogger("phi")
phi_logger.setLevel(getattr(logging, LOG_LEVEL))

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.model.message import Message as PhiMessage
from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFKnowledgeBase
from phi.storage.agent.postgres import PgAgentStorage
from phi.vectordb.pgvector import PgVector, SearchType

# DTOs
class DocumentReference(BaseModel):
    """Referencia a un documento y página específica"""
    document_name: str = Field(..., description="Nombre del documento")
    pages: List[int] = Field(default=[], description="Páginas referenciadas")
    relevance_score: Optional[float] = Field(default=None, description="Score de relevancia")

class Message(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    message: str = Field(..., description="Current user message")
    messages: Optional[List[Message]] = Field(default=[], description="Conversation history")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation continuity")
    search_knowledge: bool = Field(default=True, description="Whether to search knowledge base")
    stream: bool = Field(default=False, description="Whether to stream the response")
    format_response: bool = Field(default=True, description="Whether to apply formatting to response")
    custom_format_prompt: Optional[str] = Field(default=None, description="Custom formatting prompt to use")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    sources: Optional[List[Dict[str, Any]]] = Field(default=[], description="Sources used for the response")
    document_references: List[DocumentReference] = Field(default=[], description="Documentos y páginas consultadas")
    messages: List[Message] = Field(..., description="Updated conversation history")
    metadata: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    model: str
    embedder: str
    knowledge_base_loaded: bool
    documents_count: Optional[int] = None

class FileUploadResponse(BaseModel):
    filename: str
    size: int
    message: str
    knowledge_base_updated: bool
    total_documents: int

# Initialize FastAPI app
app = FastAPI(
    title="Insurance Knowledge Base API",
    description="API para consultas sobre documentos de seguros usando RAG con Ollama",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global configuration - Read from environment variables with defaults
db_url = os.environ.get("AGENTIC_DB_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_ID = os.environ.get("AGENTIC_MODEL_ID", "qwen3:4b")
EMBEDDER_MODEL = os.environ.get("AGENTIC_EMBEDDER_MODEL", "nomic-embed-text")

# Debug: Imprimir la configuración cargada
print(f"📋 Configuración cargada:") 
print(f"   Ollama Host: {OLLAMA_HOST}")
print(f"   Model ID: {MODEL_ID}")
print(f"   Embedder: {EMBEDDER_MODEL}")

RESPONSE_MODEL = os.environ.get("AGENTIC_RESPONSE_MODEL", "qwen2.5:7b-instruct")

# Semantic Cache Configuration - Read from environment variables with defaults
CACHE_ENABLED = os.environ.get("AGENTIC_CACHE_ENABLED", "true").lower() == "true"
CACHE_SIMILARITY_THRESHOLD = float(os.environ.get("AGENTIC_CACHE_SIMILARITY_THRESHOLD", "0.88"))
CACHE_TTL_HOURS = int(os.environ.get("AGENTIC_CACHE_TTL_HOURS", "24"))
CACHE_MAX_ENTRIES = int(os.environ.get("AGENTIC_CACHE_MAX_ENTRIES", "1000"))

# File upload configuration
MAX_FILE_SIZE = int(os.environ.get("AGENTIC_MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB default
ALLOWED_EXTENSIONS = {".pdf"}

# Default formatting prompt
DEFAULT_FORMATTING_PROMPT = """
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

# Prompt de formateo personalizable - Read from environment or use default
FORMATTING_PROMPT = os.environ.get("AGENTIC_FORMATTING_PROMPT", DEFAULT_FORMATTING_PROMPT)

 

# Initialize knowledge base
logger.info("Inicializando knowledge base...")
pdf_path = Path("docs")
pdf_files = list(pdf_path.glob("*.pdf"))
logger.info(f"Encontrados {len(pdf_files)} archivos PDF en docs/")

if LOG_LEVEL == "DEBUG" and pdf_files:
    logger.debug("Archivos PDF encontrados:")
    for pdf in pdf_files[:5]:  # Mostrar primeros 5
        logger.debug(f"   - {pdf.name}")

for pdf in pdf_files:
    print(f"  - {pdf.name}")

knowledge_base = PDFKnowledgeBase(
    path="docs",
    vector_db=PgVector(
        table_name="insurance_docs_ollama",
        db_url=db_url,
        search_type=SearchType.hybrid,
        embedder=OllamaEmbedder(model=EMBEDDER_MODEL, dimensions=768, host=OLLAMA_HOST),
    ),
)

# Load knowledge base once at startup
try:
    # Verificar que pypdf esté instalado antes de cargar
    try:
        import pypdf
        logger.info(f"pypdf version {pypdf.__version__} detectado")
    except ImportError:
        logger.error("pypdf no está instalado. Instale con: pip install pypdf==5.4.0")
        raise ImportError("pypdf es requerido para PDFKnowledgeBase. Instale con: pip install pypdf==5.4.0")
    
    #knowledge_base.load(upsert=True)
    logger.info("Knowledge base cargado exitosamente")
except ImportError as ie:
    logger.error(f"Dependencia faltante: {ie}")
    logger.info("Continuando sin cargar el knowledge base...")
except Exception as e:
    logger.warning(f"Error cargando knowledge base: {e}")

# Store active agents by session
active_agents: Dict[str, Agent] = {}

# Instancia de Ollama para formateo
formatting_model = Ollama(id=RESPONSE_MODEL, host=OLLAMA_HOST)

# Clase para Semantic Caching
class SemanticCache:
    """
    Implementa un caché semántico usando PgVector para almacenar y recuperar
    respuestas basadas en similitud de embeddings.
    """
    
    def __init__(self, db_url: str, embedder_model: str, table_name: str = "semantic_cache_ollama"):
        self.db_url = db_url
        self.table_name = table_name
        self.embedder = OllamaEmbedder(model=embedder_model, dimensions=768, host=OLLAMA_HOST)
        self.vector_db = PgVector(
            table_name=table_name,
            db_url=db_url,
            search_type=SearchType.vector,  # Búsqueda vectorial por similitud para el caché
            embedder=self.embedder,
        )
        self.enabled = CACHE_ENABLED
        self.similarity_threshold = CACHE_SIMILARITY_THRESHOLD
        self.ttl_hours = CACHE_TTL_HOURS
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_queries": 0,
            "avg_similarity": 0.0
        }
        
        # Crear tabla si no existe
        try:
            self.vector_db.create()
            print(f"🗄️ Semantic Cache inicializado - Tabla: {table_name}")
        except Exception as e:
            print(f"⚠️ Nota sobre tabla de caché: {e}")
            
        print(f"   - Threshold: {self.similarity_threshold}")
        print(f"   - TTL: {self.ttl_hours} horas")
        print(f"   - Estado: {'Habilitado' if self.enabled else 'Deshabilitado'}")
    
    def _generate_cache_key(self, query: str, context: str = "") -> str:
        """Genera una clave única para la entrada del caché"""
        combined = f"{query}::{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _extract_quoted_terms(self, text: str) -> set:
        """Extrae términos importantes entre comillas (productos, servicios, etc.)"""
        import re
        terms = set()
        
        # Buscar texto entre comillas simples o dobles
        pattern = r"['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, text)
        for match in matches:
            # Normalizar: lowercase y strip
            term = match.lower().strip()
            if term:  # Solo agregar si no está vacío
                terms.add(term)
        
        return terms
    
    def _queries_are_about_different_topics(self, query1: str, query2: str) -> bool:
        """
        Determina si dos queries hablan de temas diferentes basándose en términos entre comillas.
        Si ambas tienen términos entre comillas y son diferentes, probablemente son temas diferentes.
        """
        terms1 = self._extract_quoted_terms(query1)
        terms2 = self._extract_quoted_terms(query2)
        
        # Si ambas queries tienen términos entre comillas
        if terms1 and terms2:
            # Si no comparten ningún término, son temas diferentes
            if not (terms1 & terms2):
                return True
        
        return False
    
    def _calculate_word_overlap(self, text1: str, text2: str) -> float:
        """Calcula el overlap de palabras entre dos textos (inglés y español)"""
        # Normalizar y dividir en palabras
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Stop words en español e inglés combinadas
        stop_words = {
            # Español
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'una', 'es', 'los', 'las', 'del', 'al', 
            'con', 'por', 'para', 'su', 'sus', 'como', 'más', 'pero', 'sus', 'le', 'ya', 'o', 
            'este', 'ese', 'eso', 'esta', 'estas', 'estos', 'esas', 'esos', 'si', 'no', 'lo',
            'me', 'mi', 'tu', 'te', 'se', 'nos', 'qué', 'cuál', 'cuáles', 'cómo', 'dónde',
            # Inglés
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 
            'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 
            'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 
            'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 
            'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like',
            'time', 'no', 'just', 'him', 'know', 'take', 'into', 'year', 'your', 'some',
            'them', 'see', 'other', 'than', 'then', 'now', 'only', 'its', 'also', 'is',
            'am', 'are', 'was', 'were', 'been', 'has', 'had', 'does', 'did', 'having'
        }
        
        # Eliminar stop words de ambos conjuntos
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        # También eliminar palabras de una sola letra y símbolos comunes
        words1 = {w for w in words1 if len(w) > 1 and w.isalnum()}
        words2 = {w for w in words2 if len(w) > 1 and w.isalnum()}
        
        if not words1 or not words2:
            return 0.0
        
        # Calcular overlap usando coeficiente de Jaccard
        common = words1 & words2
        total = len(words1 | words2)
        
        if total == 0:
            return 0.0
            
        return len(common) / total
    
    async def find_similar(self, query: str, context: str = "") -> Optional[Dict[str, Any]]:
        """
        Busca una consulta similar en el caché.
        Retorna la respuesta cacheada si encuentra una coincidencia.
        """
        if not self.enabled:
            return None
        
        try:
            self.stats["total_queries"] += 1
            
            # Buscar en el vector database usando el query directamente
            # PgVector usará el embedder configurado internamente
            results = self.vector_db.search(
                query=query,
                limit=5  # Buscar las 5 más similares
            )
            
            # Verificar si hay resultados (results es una lista de Documents)
            if not results or len(results) == 0:
                self.stats["misses"] += 1
                print(f"❌ Cache MISS para: {query[:50]}...")
                return None
            
            # Procesar resultados y encontrar el mejor match
            for i, doc in enumerate(results):
                if not doc or not doc.content:
                    continue
                    
                try:
                    # Parsear el contenido JSON almacenado
                    cached_data = json.loads(doc.content)
                    
                    # Obtener score de similitud si está disponible
                    # Por defecto, usar un score conservador
                    similarity_score = 0.70  # Score conservador por defecto
                    
                    # Intentar obtener el score real del documento
                    if hasattr(doc, 'score') and doc.score is not None:
                        similarity_score = float(doc.score)
                    elif hasattr(doc, 'meta_data') and doc.meta_data:
                        if 'score' in doc.meta_data and doc.meta_data['score'] is not None:
                            similarity_score = float(doc.meta_data['score'])
                        elif 'similarity' in doc.meta_data and doc.meta_data['similarity'] is not None:
                            similarity_score = float(doc.meta_data['similarity'])
                    
                    # Verificación adicional: comparar queries textualmente
                    original_query = cached_data.get('original_query', '')
                    
                    # PRIMERO: Verificar si las queries hablan de temas diferentes
                    if self._queries_are_about_different_topics(original_query, query):
                        # Si hablan de temas diferentes (ej: 'Core' vs 'Travel Assistance'), rechazar
                        quoted_original = self._extract_quoted_terms(original_query)
                        quoted_current = self._extract_quoted_terms(query)
                        
                        print(f"   ❌ Temas diferentes detectados:")
                        print(f"      Query actual menciona: {quoted_current}")
                        print(f"      Query cacheada menciona: {quoted_original}")
                        continue  # Saltar este resultado completamente
                    
                    # Calcular overlap de palabras
                    word_overlap = self._calculate_word_overlap(original_query, query)
                    
                    # Verificación especial: si las queries son idénticas o muy similares
                    if original_query.lower().strip() == query.lower().strip():
                        # Queries idénticas - máximo score
                        similarity_score = 1.0
                        print(f"   ✅ Match exacto encontrado")
                    elif word_overlap > 0.7:  # Más del 70% de palabras en común
                        # Muy similar - mantener score alto
                        similarity_score = max(similarity_score, 0.93)
                        print(f"   ✅ Alta similitud textual: {word_overlap:.2%}")
                    elif word_overlap < 0.3:  # Menos del 30% de palabras en común
                        # Verificar si comparten palabras clave importantes (nombres de productos, etc.)
                        # Extraer palabras entre comillas o nombres propios
                        import re
                        
                        # Buscar palabras entre comillas o nombres propios (palabras con mayúsculas)
                        pattern = r"'([^']+)'|\"([^\"]+)\"|([A-Z][a-z]+)"
                        
                        keywords1 = set()
                        for match in re.finditer(pattern, original_query):
                            for group in match.groups():
                                if group:
                                    keywords1.add(group.lower())
                        
                        keywords2 = set()
                        for match in re.finditer(pattern, query):
                            for group in match.groups():
                                if group:
                                    keywords2.add(group.lower())
                        
                        # Si comparten palabras clave importantes, no penalizar tanto
                        if keywords1 and keywords2 and keywords1 & keywords2:
                            shared_keywords = keywords1 & keywords2
                            similarity_score = similarity_score * 0.85  # Penalización menor
                            print(f"   🔑 Palabras clave compartidas: {shared_keywords}")
                            print(f"   Score ajustado: {similarity_score:.2f}")
                        else:
                            similarity_score = similarity_score * 0.5  # Reducir score a la mitad
                            print(f"   📉 Score ajustado por baja similitud textual: {similarity_score:.2f}")
                            print(f"      Query actual: '{query[:50]}...'")
                            print(f"      Query cacheada: '{original_query[:50]}...'")
                            print(f"      Overlap de palabras: {word_overlap:.2%}")
                    elif word_overlap < 0.5:  # Entre 30% y 50% de palabras en común
                        similarity_score = similarity_score * 0.8  # Reducir score un 20%
                        print(f"   ⚠️ Score ajustado por similitud textual moderada: {similarity_score:.2f}")
                    
                    # Verificar si supera el threshold y no ha expirado
                    if similarity_score >= self.similarity_threshold:
                        # Verificar TTL
                        cached_time = datetime.fromisoformat(cached_data.get("timestamp", ""))
                        if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                            print(f"⏰ Cache entry expirado para: {query[:50]}...")
                            continue
                        
                        # Incrementar hits
                        self.stats["hits"] += 1
                        hit_rate = (self.stats["hits"] / self.stats["total_queries"]) * 100
                        
                        print(f"✅ Cache HIT! Similitud: {similarity_score:.2f}")
                        print(f"   Query original: {cached_data.get('original_query', '')[:50]}...")
                        print(f"   Hit rate: {hit_rate:.1f}%")
                        
                        # Verificar que hay referencias de documentos
                        doc_refs = cached_data.get("document_references", [])
                        if not doc_refs:
                            print(f"⚠️ Cache entry sin referencias, saltando: {cached_data.get('original_query', '')[:50]}...")
                            continue
                        
                        return {
                            "response": cached_data.get("response"),
                            "cached_at": cached_data.get("timestamp"),
                            "similarity": similarity_score,
                            "original_query": cached_data.get("original_query"),
                            "metadata": cached_data.get("metadata", {}),
                            "document_references": doc_refs
                        }
                        
                except Exception as e:
                    print(f"Error procesando entrada de caché: {e}")
                    continue
            
            self.stats["misses"] += 1
            print(f"❌ Cache MISS - No se encontró similitud suficiente para: {query[:50]}...")
            return None
            
        except Exception as e:
            print(f"Error buscando en caché: {e}")
            return None
    
    async def store(self, query: str, response: str, context: str = "", metadata: Dict = None, document_references: List = None) -> bool:
        """
        Almacena una nueva entrada en el caché.
        Solo almacena si hay referencias de documentos.
        """
        if not self.enabled:
            return False
        
        # NO almacenar en caché si no hay referencias de documentos
        if not document_references or len(document_references) == 0:
            print(f"⚠️ No se cachea respuesta sin referencias de documentos para: {query[:50]}...")
            return False
        
        try:
            # Preparar datos para almacenar
            cache_data = {
                "original_query": query,
                "response": response,
                "context": context[:500] if context else "",  # Limitar contexto
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
                "cache_key": self._generate_cache_key(query, context),
                "document_references": [
                    {
                        "document_name": ref.document_name,
                        "pages": ref.pages
                    } for ref in document_references
                ] if document_references else []
            }
            
            # Crear documento para almacenar
            from phi.document import Document
            doc = Document(
                content=json.dumps(cache_data, ensure_ascii=False),
                meta_data={
                    "query": query[:200],  # Para búsquedas
                    "timestamp": cache_data["timestamp"],
                    "cache_key": cache_data["cache_key"]
                }
            )
            
            # Almacenar en vector database
            self.vector_db.upsert([doc])
            
            print(f"💾 Respuesta cacheada para: {query[:50]}...")
            print(f"   Cache key: {cache_data['cache_key'][:8]}...")
            
            # Limpiar entradas antiguas si excede el máximo
            await self._cleanup_old_entries()
            
            return True
            
        except Exception as e:
            print(f"Error almacenando en caché: {e}")
            return False
    
    async def _cleanup_old_entries(self):
        """Limpia entradas antiguas del caché"""
        # Esta función debería implementarse con consultas SQL directas
        # para eliminar entradas más antiguas que TTL o exceso sobre MAX_ENTRIES
        pass
    
    async def clear(self) -> bool:
        """Limpia todo el caché"""
        try:
            # Limpiar la tabla del vector database
            # Recrear la tabla para limpiarla completamente
            try:
                self.vector_db.delete()  # Eliminar tabla
                self.vector_db.create()  # Recrear tabla
            except:
                # Si falla, al menos intentar recrear
                try:
                    self.vector_db.create()
                except:
                    pass
            
            # Resetear estadísticas
            self.stats = {
                "hits": 0,
                "misses": 0, 
                "total_queries": 0,
                "avg_similarity": 0.0
            }
            print("🧹 Caché limpiado completamente")
            return True
        except Exception as e:
            print(f"Error limpiando caché: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del caché"""
        hit_rate = (self.stats["hits"] / self.stats["total_queries"] * 100) if self.stats["total_queries"] > 0 else 0
        return {
            **self.stats,
            "hit_rate": f"{hit_rate:.1f}%",
            "enabled": self.enabled,
            "threshold": self.similarity_threshold,
            "ttl_hours": self.ttl_hours
        }

# Inicializar Semantic Cache
semantic_cache = SemanticCache(
    db_url=db_url,
    embedder_model=EMBEDDER_MODEL,
    table_name="semantic_cache_ollama"
)

def get_or_create_agent(session_id: str = None, messages: List[Message] = None) -> tuple[Agent, str]:
    """Get existing agent or create new one for the session with conversation history"""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if session_id not in active_agents:
        agent = Agent(
            name=f"Insurance Agent - {session_id[:8]}",
            agent_id=f"insurance-agent-{session_id}",
            model=Ollama(id=MODEL_ID, host=OLLAMA_HOST),
            knowledge=knowledge_base,
            search_knowledge=True,
            read_chat_history=True,
            storage=PgAgentStorage(
                table_name="insurance_api_sessions",
                db_url=db_url
            ),
            instructions=[
                "Siempre busca primero en tu base de conocimientos y úsala si está disponible.",
                "Realiza la busqueda utilizando diferentes enfoques para obtener los mejores resultados. tomando en cuenta el contexto de la conversación. y el idioma en que se está llevando a cabo la conversación.",
                "IMPORTANTE: Al final de tu respuesta, SIEMPRE incluye una sección llamada 'REFERENCES:' donde listes EXACTAMENTE los documentos y páginas consultados en el formato: [DocumentName.pdf - Page X]",
                "Si se mencionan beneficios o coberturas, inclúyelos detalladamente en la respuesta.",
                "Importante: Usa tablas cuando sea posible para comparar productos o beneficios.",
                "Responde en español y sé claro con los términos de seguros.",
                "Mantén el contexto de la conversación previa cuando respondas.",
                "Cada vez que cites información, incluye la referencia entre corchetes [Document.pdf - Page X]",
            ],
            markdown=True,
            show_tool_calls=False,
        )
        active_agents[session_id] = agent
    
    # Si hay mensajes previos, actualizar el historial del agente
    agent = active_agents[session_id]
    
    # Si se proporcionaron mensajes del historial, agregarlos al agente
    if messages:
        # Limpiar el historial anterior del agente para esta sesión
        # y agregar los mensajes proporcionados
        for msg in messages:
            # Convertir nuestro Message a PhiMessage para el agente
            phi_msg = PhiMessage(
                role=msg.role,
                content=msg.content
            )
            # Agregar al historial del agente
            if not hasattr(agent, 'messages'):
                agent.messages = []
            # Solo agregar si no es el último mensaje (que es el actual)
            if messages.index(msg) < len(messages) - 1:
                agent.messages.append(phi_msg)
    
    return agent, session_id

def format_conversation_history(messages: List[Message]) -> str:
    """Format conversation history for context"""
    if not messages:
        return ""
    
    history = "Historial de conversación:\n"
    for msg in messages[-10:]:  # Últimos 10 mensajes para contexto
        role = "Usuario" if msg.role == "user" else "Asistente"
        history += f"{role}: {msg.content}\n"
    
    return history

def remove_think_blocks(text: str) -> str:
    """
    Remueve todos los bloques <think></think> del texto.
    """
    import re
    # Patrón para encontrar bloques <think>...</think> incluyendo saltos de línea
    pattern = r'<think>.*?</think>'
    # Eliminar todos los bloques think
    cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
    # Limpiar espacios en blanco extras que puedan quedar
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
    return cleaned_text.strip()

def extract_document_references(text: str) -> tuple[str, List[DocumentReference]]:
    """
    Extrae las referencias de documentos del texto y devuelve el texto limpio y las referencias.
    Busca patrones como [Document.pdf - Page X] o REFERENCES: ...
    Soporta tanto formato en inglés como español para compatibilidad.
    """
    import re
    
    references_dict = {}
    clean_text = text
    
    # Patrón para encontrar referencias en formato [Document.pdf - Page X] o similar
    # Busca tanto en español como en inglés
    pattern = r'\[([^]]*\.pdf)\s*[-–]\s*(?:[Pp]ág(?:ina)?\.?|[Pp]age)\s*(\d+)\]'
    matches = re.findall(pattern, text)
    
    for doc_name, page in matches:
        doc_name = doc_name.strip()
        page_num = int(page)
        
        if doc_name not in references_dict:
            references_dict[doc_name] = []
        if page_num not in references_dict[doc_name]:
            references_dict[doc_name].append(page_num)
    
    # Buscar sección de REFERENCES al final del texto
    referencias_section = re.search(r'REFERENCES:\s*(.+?)(?:\n\n|$)', text, re.DOTALL | re.IGNORECASE)
    if referencias_section:
        refs_text = referencias_section.group(1)
        # Remover la sección de referencias del texto limpio
        clean_text = text[:referencias_section.start()].strip()
        
        # Extraer referencias de la sección
        ref_lines = refs_text.strip().split('\n')
        for line in ref_lines:
            matches_in_line = re.findall(pattern, line)
            for doc_name, page in matches_in_line:
                doc_name = doc_name.strip()
                page_num = int(page)
                
                if doc_name not in references_dict:
                    references_dict[doc_name] = []
                if page_num not in references_dict[doc_name]:
                    references_dict[doc_name].append(page_num)
    
    # Convertir a lista de DocumentReference
    document_references = []
    for doc_name, pages in references_dict.items():
        document_references.append(DocumentReference(
            document_name=doc_name,
            pages=sorted(pages)
        ))
    
    return clean_text, document_references

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and configuration"""
    try:
        # Verificar si el knowledge base tiene documentos
        doc_count = None
        if hasattr(knowledge_base, 'vector_db'):
            # Intentar obtener conteo de documentos
            doc_count = len(pdf_files)
        
        return HealthResponse(
            status="healthy",
            model=MODEL_ID,
            embedder=EMBEDDER_MODEL,
            knowledge_base_loaded=True,
            documents_count=doc_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal para consultas al knowledge base.
    Soporta historial de conversación y sesiones persistentes.
    """
    try:
        # Obtener o crear agente para la sesión con el historial de mensajes
        agent, session_id = get_or_create_agent(request.session_id, request.messages)
        
        # El mensaje actual es el que viene en request.message
        # El historial ya fue pasado al agente
        context = request.message
        
        # Configurar búsqueda en knowledge base
        agent.search_knowledge = True
        
        # Obtener respuesta del agente RAG
        print(f"\n{'='*60}")
        print(f"🔍 Procesando consulta: {request.message[:300]}...")
        print(f"📚 Búsqueda en knowledge base: {request.search_knowledge}")
        print(f"🆔 Session ID: {session_id[:8]}...")
        
        # Intentar obtener respuesta del caché primero
        cached_response = None
        cache_used = False
        response = None  # Inicializar response para evitar error cuando se usa caché
        document_references = []  # Inicializar referencias vacías por defecto
        
        if CACHE_ENABLED and request.search_knowledge and not request.stream:
            cached_response = await semantic_cache.find_similar(
                query=request.message,
                context=context[:500]  # Limitar contexto para el caché
            )
            
            if cached_response:
                response_text = cached_response["response"]
                cache_used = True
                
                # Reconstruir document_references desde el caché
                if 'document_references' in cached_response:
                    # Crear objetos DocumentReference desde los datos cacheados
                    cached_refs = cached_response['document_references']
                    document_references = [
                        DocumentReference(
                            document_name=ref['document_name'],
                            pages=ref['pages']
                        ) for ref in cached_refs
                    ]
                    print(f"🚀 Usando respuesta cacheada (similitud: {cached_response['similarity']:.2f})")
                    print(f"   Cacheado en: {cached_response['cached_at']}")
                    print(f"   Referencias recuperadas: {len(document_references)} documentos")
                else:
                    # No debería pasar si el caché funciona correctamente
                    cache_used = False
                    print("⚠️ Cache sin referencias, ejecutando agente...")
        
        # Si no hay caché o está deshabilitado, ejecutar el agente
        if not cache_used:
            if request.stream:
                # Para streaming, necesitarías implementar SSE o WebSockets
                response_text = ""
                for chunk in agent.run(context, stream=True):
                    if hasattr(chunk, 'content'):
                        response_text += chunk.content
            else:
                response = agent.run(context)
                response_text = response.content if hasattr(response, 'content') else str(response)
            
            print(f"✅ Respuesta generada - Longitud: {len(response_text)} caracteres")
            
            # Extraer referencias de documentos ANTES de cachear
            response_with_refs, document_references = extract_document_references(response_text)
        else:
            # Si se usó caché, document_references ya fue establecido arriba
            response_with_refs = response_text  # Ya tenemos la respuesta del caché
            print(f"✅ Respuesta del caché - Longitud: {len(response_text)} caracteres")
        
        # Si no se usó caché y la respuesta es exitosa, almacenarla
        if not cache_used and CACHE_ENABLED and request.search_knowledge and not request.stream:
            # Preparar metadata incluyendo sources si están disponibles
            cache_metadata = {
                "session_id": session_id,
                "model": MODEL_ID,
                "timestamp": datetime.now().isoformat()
            }
            
            # Incluir sources en metadata si existen
            if response and hasattr(response, 'sources') and response.sources:
                cache_metadata["sources"] = response.sources
            
            # Almacenar en caché SOLO si hay referencias de documentos
            await semantic_cache.store(
                query=request.message,
                response=response_text,
                context=context[:500],
                metadata=cache_metadata,
                document_references=document_references  # Pasar las referencias
            )
        
        # Log de documentos referenciados
        if document_references:
            print(f"\n📄 Documentos consultados ({len(document_references)} documentos):")
            for ref in document_references:
                pages_str = ', '.join(map(str, ref.pages))
                print(f"   - {ref.document_name}: Páginas {pages_str}")
        else:
            print("⚠️ No se encontraron referencias a documentos en la respuesta")
        
        # Remover bloques <think></think> de la respuesta base
        response_with_refs = remove_think_blocks(response_with_refs)
        
        # Aplicar formateo adicional a la respuesta (sin las referencias)
        formatted_response = response_with_refs 
        try: 
            format_prompt = FORMATTING_PROMPT.format(question=request.message, response=response_text)
            print("Aplicando formateo a la respuesta...")
            # Crear mensaje para Ollama
            format_message = PhiMessage(role='user', content=format_prompt)
            # Usar el método response en lugar de invoke
            format_result = formatting_model.response([format_message])
            # Extraer el contenido del resultado
            formatted_response = format_result.content if hasattr(format_result, 'content') else str(format_result)
            # Remover bloques <think></think>
            formatted_response = remove_think_blocks(formatted_response)
            print(f"✨ Respuesta formateada exitosamente - Nueva longitud: {len(formatted_response)} caracteres")
        except Exception as e:
            print(f"Error al formatear respuesta: {e}")
            # Si falla el formateo, usar respuesta sin referencias
            formatted_response = response_with_refs
        
        # Actualizar historial de mensajes con respuesta formateada
        updated_messages = request.messages.copy() if request.messages else []
        updated_messages.append(Message(role="user", content=request.message))
        updated_messages.append(Message(role="assistant", content=formatted_response))
        
        # Extraer fuentes si están disponibles
        sources = []
        # Solo intentar obtener sources si response existe (no se usó caché)
        if response and hasattr(response, 'sources'):
            sources = response.sources
            if sources:
                print(f"\n🔎 Fuentes del agente ({len(sources)} fuentes):")
                for i, source in enumerate(sources, 1):
                    print(f"   {i}. {source}")
        elif cache_used:
            # Si se usó caché, intentar obtener sources del metadata cacheado
            if cached_response and 'metadata' in cached_response:
                sources = cached_response['metadata'].get('sources', [])
                if sources:
                    print(f"\n🔎 Fuentes del caché ({len(sources)} fuentes)")
            else:
                print("📝 Respuesta obtenida del caché (sin fuentes detalladas)")
        
        # Log resumen final
        print(f"\n{'='*60}")
        print(f"📊 Resumen de la respuesta:")
        print(f"   - Longitud original: {len(response_text)} caracteres")
        print(f"   - Longitud formateada: {len(formatted_response)} caracteres")
        print(f"   - Referencias encontradas: {len(document_references)}")
        print(f"   - Fuentes del agente: {len(sources)}")
        print(f"   - Formateo aplicado: {request.format_response and request.search_knowledge}")
        print(f"   - 🚀 Caché usado: {'SÍ' if cache_used else 'NO'}")
        if CACHE_ENABLED:
            cache_stats = semantic_cache.get_stats()
            print(f"   - 📈 Cache Hit Rate: {cache_stats['hit_rate']}")
            print(f"   - 📊 Total consultas en caché: {cache_stats['total_queries']}")
        print(f"{'='*60}\n")
        
        return ChatResponse(
            response=formatted_response,  # Usar respuesta formateada
            session_id=session_id,
            sources=sources,
            document_references=document_references,  # Agregar referencias extraídas
            messages=updated_messages,
            metadata={
                "model": MODEL_ID,
                "knowledge_search": request.search_knowledge,
                "timestamp": datetime.now().isoformat(),
                "formatted": request.format_response and request.search_knowledge,  # Indicar si se aplicó formateo
                "original_length": len(response_text),
                "formatted_length": len(formatted_response),
                "references_found": len(document_references),
                "cache_used": cache_used,
                "cache_similarity": cached_response["similarity"] if cache_used and cached_response else None,
                "cache_stats": semantic_cache.get_stats() if CACHE_ENABLED else None
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")

@app.post("/chat/simple")
async def simple_chat(message: str):
    """
    Endpoint simplificado para consultas rápidas sin manejo de sesión.
    """
    try:
        agent, _ = get_or_create_agent()
        response = agent.run(message)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        return {
            "response": response_text,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    Limpiar una sesión específica y su agente asociado.
    """
    if session_id in active_agents:
        del active_agents[session_id]
        return {"message": f"Sesión {session_id} eliminada exitosamente"}
    else:
        raise HTTPException(status_code=404, detail=f"Sesión {session_id} no encontrada")

@app.get("/sessions")
async def list_sessions():
    """
    Listar todas las sesiones activas.
    """
    return {
        "active_sessions": list(active_agents.keys()),
        "count": len(active_agents)
    }

# Endpoints adicionales útiles
@app.get("/documents")
async def list_documents():
    """
    Listar documentos cargados en el knowledge base.
    """
    docs = []
    for pdf in pdf_files:
        docs.append({
            "name": pdf.name,
            "path": str(pdf),
            "size": pdf.stat().st_size
        })
    
    return {
        "documents": docs,
        "total": len(docs)
    }

@app.post("/reload-knowledge")
async def reload_knowledge_base():
    """
    Recargar el knowledge base con los documentos actuales.
    """
    try:
        global knowledge_base
        knowledge_base.load(upsert=True)
        
        # Limpiar agentes para usar el nuevo knowledge base
        active_agents.clear()
        
        return {
            "message": "Knowledge base recargado exitosamente",
            "documents_loaded": len(pdf_files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recargando knowledge base: {str(e)}")

@app.post("/upload-pdf", response_model=FileUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Subir un archivo PDF y actualizar la base de conocimiento.
    
    Args:
        file: Archivo PDF a subir
    
    Returns:
        FileUploadResponse con detalles del archivo subido
    """
    try:
        # Validar extensión del archivo
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido. Solo se aceptan archivos PDF."
            )
        
        # Validar tamaño del archivo
        contents = await file.read()
        file_size = len(contents)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande. Tamaño máximo permitido: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío"
            )
        
        # Crear directorio docs si no existe
        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)
        
        # Generar nombre único para evitar colisiones
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}".replace(" ", "_")
        file_path = docs_dir / safe_filename
        
        # Verificar si el archivo ya existe (mismo nombre sin timestamp)
        original_path = docs_dir / file.filename
        if original_path.exists():
            # Renombrar el archivo existente con un backup
            backup_path = docs_dir / f"backup_{timestamp}_{file.filename}"
            shutil.move(str(original_path), str(backup_path))
            print(f"Archivo existente movido a: {backup_path}")
        
        # Guardar el archivo
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        print(f"Archivo guardado: {file_path}")
        
        # Actualizar la lista de archivos PDF
        global pdf_files
        pdf_files = list(Path("docs").glob("*.pdf"))
        
        # Recargar el knowledge base con el nuevo archivo
        print("Actualizando knowledge base...")
        try:
            knowledge_base.load(upsert=True)
            print("Knowledge base actualizado exitosamente")
            
            # Limpiar caché semántico para que las nuevas consultas usen el contenido actualizado
            if semantic_cache.enabled:
                await semantic_cache.clear()
                print("Caché semántico limpiado")
            
            # Limpiar agentes activos para usar el knowledge base actualizado
            active_agents.clear()
            
            kb_updated = True
        except Exception as kb_error:
            print(f"Advertencia: Error actualizando knowledge base: {kb_error}")
            kb_updated = False
        
        return FileUploadResponse(
            filename=file.filename,
            size=file_size,
            message=f"Archivo '{file.filename}' subido exitosamente",
            knowledge_base_updated=kb_updated,
            total_documents=len(pdf_files)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error procesando archivo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el archivo: {str(e)}"
        )

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    Eliminar un documento PDF del sistema.
    
    Args:
        filename: Nombre del archivo a eliminar
    
    Returns:
        Mensaje de confirmación
    """
    try:
        file_path = Path("docs") / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Archivo '{filename}' no encontrado"
            )
        
        if file_path.suffix.lower() != ".pdf":
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden eliminar archivos PDF"
            )
        
        # Eliminar el archivo
        file_path.unlink()
        print(f"Archivo eliminado: {file_path}")
        
        # Actualizar la lista de archivos
        global pdf_files
        pdf_files = list(Path("docs").glob("*.pdf"))
        
        # Recargar knowledge base
        try:
            knowledge_base.load(upsert=True)
            print("Knowledge base actualizado después de eliminar archivo")
            
            # Limpiar caché y agentes
            if semantic_cache.enabled:
                await semantic_cache.clear()
            active_agents.clear()
            
        except Exception as kb_error:
            print(f"Advertencia: Error actualizando knowledge base: {kb_error}")
        
        return {
            "message": f"Archivo '{filename}' eliminado exitosamente",
            "remaining_documents": len(pdf_files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando archivo: {str(e)}"
        )

# Endpoints para gestión del Semantic Cache
@app.get("/cache/stats")
async def get_cache_stats():
    """
    Obtener estadísticas del caché semántico.
    """
    return {
        "cache_enabled": CACHE_ENABLED,
        "stats": semantic_cache.get_stats(),
        "configuration": {
            "similarity_threshold": CACHE_SIMILARITY_THRESHOLD,
            "ttl_hours": CACHE_TTL_HOURS,
            "max_entries": CACHE_MAX_ENTRIES
        }
    }

@app.post("/cache/clear")
async def clear_cache():
    """
    Limpiar todo el caché semántico.
    """
    try:
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

@app.post("/cache/toggle")
async def toggle_cache(enabled: bool):
    """
    Habilitar o deshabilitar el caché semántico.
    """
    global CACHE_ENABLED
    CACHE_ENABLED = enabled
    semantic_cache.enabled = enabled
    
    return {
        "cache_enabled": CACHE_ENABLED,
        "message": f"Caché {'habilitado' if enabled else 'deshabilitado'} exitosamente",
        "timestamp": datetime.now().isoformat()
    }

@app.put("/cache/config")
async def update_cache_config(
    similarity_threshold: Optional[float] = None,
    ttl_hours: Optional[int] = None
):
    """
    Actualizar configuración del caché semántico.
    """
    global CACHE_SIMILARITY_THRESHOLD, CACHE_TTL_HOURS
    
    if similarity_threshold is not None:
        if 0.0 <= similarity_threshold <= 1.0:
            CACHE_SIMILARITY_THRESHOLD = similarity_threshold
            semantic_cache.similarity_threshold = similarity_threshold
        else:
            raise HTTPException(status_code=400, detail="Threshold debe estar entre 0.0 y 1.0")
    
    if ttl_hours is not None:
        if ttl_hours > 0:
            CACHE_TTL_HOURS = ttl_hours
            semantic_cache.ttl_hours = ttl_hours
        else:
            raise HTTPException(status_code=400, detail="TTL debe ser mayor a 0")
    
    return {
        "configuration": {
            "similarity_threshold": CACHE_SIMILARITY_THRESHOLD,
            "ttl_hours": CACHE_TTL_HOURS,
            "max_entries": CACHE_MAX_ENTRIES
        },
        "message": "Configuración actualizada exitosamente",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)