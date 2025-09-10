"""
Servicio de caché semántico.
Siguiendo el principio de Single Responsibility - solo maneja el caché.
"""

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
import logging

from phi.document import Document
from phi.embedder.ollama import OllamaEmbedder
from phi.vectordb.pgvector import PgVector, SearchType

try:
    # Absolute imports for Docker/standalone execution
    from config.settings import settings
    from models.schemas import DocumentReference
except ImportError:
    # Relative imports for package execution
    from ..config.settings import settings
    from ..models.schemas import DocumentReference

logger = logging.getLogger(__name__)


class SemanticCache:
    """
    Implementa un caché semántico usando PgVector para almacenar y recuperar
    respuestas basadas en similitud de embeddings.
    """
    
    def __init__(self, table_name: str = "semantic_cache_ollama"):
        self.db_url = settings.DB_URL
        self.table_name = table_name
        self.embedder = OllamaEmbedder(
            model=settings.EMBEDDER_MODEL, 
            dimensions=768, 
            host=settings.OLLAMA_HOST
        )
        self.vector_db = PgVector(
            table_name=table_name,
            db_url=self.db_url,
            search_type=SearchType.vector,
            embedder=self.embedder,
        )
        self.enabled = settings.CACHE_ENABLED
        self.similarity_threshold = settings.CACHE_SIMILARITY_THRESHOLD
        self.ttl_hours = settings.CACHE_TTL_HOURS
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_queries": 0,
            "avg_similarity": 0.0
        }
        
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Inicializa la tabla del caché"""
        try:
            self.vector_db.create()
            logger.info(f"🗄️ Semantic Cache inicializado - Tabla: {self.table_name}")
        except Exception as e:
            logger.warning(f"⚠️ Nota sobre tabla de caché: {e}")
        
        print(f"   - Threshold: {self.similarity_threshold}")
        print(f"   - TTL: {self.ttl_hours} horas")
        print(f"   - Estado: {'Habilitado' if self.enabled else 'Deshabilitado'}")
    
    def _generate_cache_key(self, query: str, context: str = "") -> str:
        """Genera una clave única para la entrada del caché"""
        combined = f"{query}::{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _extract_quoted_terms(self, text: str) -> Set[str]:
        """Extrae términos importantes entre comillas"""
        terms = set()
        pattern = r"['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, text)
        for match in matches:
            term = match.lower().strip()
            if term:
                terms.add(term)
        return terms
    
    def _queries_are_about_different_topics(self, query1: str, query2: str) -> bool:
        """Determina si dos queries hablan de temas diferentes"""
        terms1 = self._extract_quoted_terms(query1)
        terms2 = self._extract_quoted_terms(query2)
        
        if terms1 and terms2:
            if not (terms1 & terms2):
                return True
        
        return False
    
    def _calculate_word_overlap(self, text1: str, text2: str) -> float:
        """Calcula el overlap de palabras entre dos textos"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Stop words combinadas (español e inglés)
        stop_words = {
            # Español
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'una', 'es', 'los', 'las', 
            'del', 'al', 'con', 'por', 'para', 'su', 'sus', 'como', 'más', 'pero', 
            'le', 'ya', 'o', 'este', 'ese', 'eso', 'esta', 'estas', 'estos', 'esas', 
            'esos', 'si', 'no', 'lo', 'me', 'mi', 'tu', 'te', 'se', 'nos', 'qué', 
            'cuál', 'cuáles', 'cómo', 'dónde',
            # Inglés
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 
            'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 
            'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 
            'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 
            'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 
            'like', 'time', 'no', 'just', 'him', 'know', 'take', 'into', 'year', 
            'your', 'some', 'them', 'see', 'other', 'than', 'then', 'now', 'only', 
            'its', 'also', 'is', 'am', 'are', 'was', 'were', 'been', 'has', 'had', 
            'does', 'did', 'having'
        }
        
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        words1 = {w for w in words1 if len(w) > 1 and w.isalnum()}
        words2 = {w for w in words2 if len(w) > 1 and w.isalnum()}
        
        if not words1 or not words2:
            return 0.0
        
        common = words1 & words2
        total = len(words1 | words2)
        
        if total == 0:
            return 0.0
            
        return len(common) / total
    
    async def find_similar(self, query: str, context: str = "") -> Optional[Dict[str, Any]]:
        """Busca una consulta similar en el caché"""
        if not self.enabled:
            return None
        
        try:
            self.stats["total_queries"] += 1
            
            results = self.vector_db.search(
                query=query,
                limit=5
            )
            
            if not results or len(results) == 0:
                self.stats["misses"] += 1
                print(f"❌ Cache MISS para: {query[:50]}...")
                return None
            
            for i, doc in enumerate(results):
                if not doc or not doc.content:
                    continue
                
                try:
                    cached_data = json.loads(doc.content)
                    similarity_score = 0.70
                    
                    if hasattr(doc, 'score') and doc.score is not None:
                        similarity_score = float(doc.score)
                    elif hasattr(doc, 'meta_data') and doc.meta_data:
                        if 'score' in doc.meta_data and doc.meta_data['score'] is not None:
                            similarity_score = float(doc.meta_data['score'])
                        elif 'similarity' in doc.meta_data and doc.meta_data['similarity'] is not None:
                            similarity_score = float(doc.meta_data['similarity'])
                    
                    original_query = cached_data.get('original_query', '')
                    
                    if self._queries_are_about_different_topics(original_query, query):
                        quoted_original = self._extract_quoted_terms(original_query)
                        quoted_current = self._extract_quoted_terms(query)
                        
                        print(f"   ❌ Temas diferentes detectados:")
                        print(f"      Query actual menciona: {quoted_current}")
                        print(f"      Query cacheada menciona: {quoted_original}")
                        continue
                    
                    word_overlap = self._calculate_word_overlap(original_query, query)
                    
                    if original_query.lower().strip() == query.lower().strip():
                        similarity_score = 1.0
                        print(f"   ✅ Match exacto encontrado")
                    elif word_overlap > 0.7:
                        similarity_score = max(similarity_score, 0.93)
                        print(f"   ✅ Alta similitud textual: {word_overlap:.2%}")
                    elif word_overlap < 0.3:
                        self._adjust_score_for_keywords(original_query, query, similarity_score, word_overlap)
                    elif word_overlap < 0.5:
                        similarity_score = similarity_score * 0.8
                        print(f"   ⚠️ Score ajustado por similitud textual moderada: {similarity_score:.2f}")
                    
                    if similarity_score >= self.similarity_threshold:
                        cached_time = datetime.fromisoformat(cached_data.get("timestamp", ""))
                        if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                            print(f"⏰ Cache entry expirado para: {query[:50]}...")
                            continue
                        
                        self.stats["hits"] += 1
                        hit_rate = (self.stats["hits"] / self.stats["total_queries"]) * 100
                        
                        print(f"✅ Cache HIT! Similitud: {similarity_score:.2f}")
                        print(f"   Query original: {cached_data.get('original_query', '')[:50]}...")
                        print(f"   Hit rate: {hit_rate:.1f}%")
                        
                        doc_refs = cached_data.get("document_references", [])
                        if not doc_refs:
                            print(f"⚠️ Cache entry sin referencias, saltando")
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
    
    def _adjust_score_for_keywords(self, original_query: str, query: str, 
                                   similarity_score: float, word_overlap: float) -> float:
        """Ajusta el score basado en palabras clave compartidas"""
        import re
        
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
        
        if keywords1 and keywords2 and keywords1 & keywords2:
            shared_keywords = keywords1 & keywords2
            similarity_score = similarity_score * 0.85
            print(f"   🔑 Palabras clave compartidas: {shared_keywords}")
            print(f"   Score ajustado: {similarity_score:.2f}")
        else:
            similarity_score = similarity_score * 0.5
            print(f"   📉 Score ajustado por baja similitud textual: {similarity_score:.2f}")
            print(f"      Query actual: '{query[:50]}...'")
            print(f"      Query cacheada: '{original_query[:50]}...'")
            print(f"      Overlap de palabras: {word_overlap:.2%}")
        
        return similarity_score
    
    async def store(self, query: str, response: str, context: str = "", 
                   metadata: Dict = None, document_references: List = None) -> bool:
        """Almacena una nueva entrada en el caché"""
        if not self.enabled:
            return False
        
        if not document_references or len(document_references) == 0:
            print(f"⚠️ No se cachea respuesta sin referencias de documentos")
            return False
        
        try:
            cache_data = {
                "original_query": query,
                "response": response,
                "context": context[:500] if context else "",
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
            
            doc = Document(
                content=json.dumps(cache_data, ensure_ascii=False),
                meta_data={
                    "query": query[:200],
                    "timestamp": cache_data["timestamp"],
                    "cache_key": cache_data["cache_key"]
                }
            )
            
            self.vector_db.upsert([doc])
            
            print(f"💾 Respuesta cacheada para: {query[:50]}...")
            print(f"   Cache key: {cache_data['cache_key'][:8]}...")
            
            await self._cleanup_old_entries()
            
            return True
            
        except Exception as e:
            print(f"Error almacenando en caché: {e}")
            return False
    
    async def _cleanup_old_entries(self):
        """Limpia entradas antiguas del caché"""
        # TODO: Implementar limpieza de entradas antiguas
        pass
    
    async def clear(self) -> bool:
        """Limpia todo el caché"""
        try:
            try:
                self.vector_db.delete()
                self.vector_db.create()
            except:
                try:
                    self.vector_db.create()
                except:
                    pass
            
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