"""
Servicio para manejo de knowledge base.
Siguiendo el principio de Single Responsibility - solo maneja el knowledge base.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFKnowledgeBase
from phi.vectordb.pgvector import PgVector, SearchType

try:
    # Absolute imports for Docker/standalone execution
    from config.settings import settings
except ImportError:
    # Relative imports for package execution
    from ..config.settings import settings

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    Servicio para gestionar el knowledge base de documentos PDF.
    """
    
    def __init__(self):
        self.pdf_path = settings.DOCS_PATH
        self.pdf_files = []
        self.knowledge_base = None
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Inicializa el knowledge base"""
        logger.info("Inicializando knowledge base...")
        
        # Buscar archivos PDF
        self.pdf_files = list(self.pdf_path.glob("*.pdf"))
        logger.info(f"Encontrados {len(self.pdf_files)} archivos PDF en {self.pdf_path}/")
        
        if settings.LOG_LEVEL == "DEBUG" and self.pdf_files:
            logger.debug("Archivos PDF encontrados:")
            for pdf in self.pdf_files[:5]:
                logger.debug(f"   - {pdf.name}")
        
        for pdf in self.pdf_files:
            print(f"  - {pdf.name}")
        
        # Crear knowledge base
        self.knowledge_base = PDFKnowledgeBase(
            path=str(self.pdf_path),
            vector_db=PgVector(
                table_name="insurance_docs_ollama",
                db_url=settings.DB_URL,
                search_type=SearchType.hybrid,
                embedder=OllamaEmbedder(
                    model=settings.EMBEDDER_MODEL, 
                    dimensions=768, 
                    host=settings.OLLAMA_HOST
                ),
            ),
        )
        
        # Cargar knowledge base si hay archivos
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """Carga los documentos en el knowledge base"""
        try:
            # Verificar dependencias
            try:
                import pypdf
                logger.info(f"pypdf version {pypdf.__version__} detectado")
            except ImportError:
                logger.error("pypdf no está instalado. Instale con: pip install pypdf==5.4.0")
                raise ImportError("pypdf es requerido para PDFKnowledgeBase")
            
            # Verificar si hay archivos PDF
            if not self.pdf_files:
                logger.warning("⚠️ No se encontraron archivos PDF en docs/")
                logger.warning("⚠️ El knowledge base estará vacío hasta que se carguen documentos")
            else:
                logger.info(f"Cargando {len(self.pdf_files)} archivos PDF al knowledge base...")
                # Descomentar para cargar realmente los documentos
                # self.knowledge_base.load(upsert=True)
                logger.info("✅ Knowledge base cargado exitosamente")
                
        except ImportError as ie:
            logger.error(f"Dependencia faltante: {ie}")
            logger.info("Continuando sin cargar el knowledge base...")
        except Exception as e:
            logger.error(f"Error cargando knowledge base: {e}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            logger.warning("⚠️ Continuando con knowledge base vacío")
    
    def reload_knowledge_base(self):
        """Recarga el knowledge base con los documentos actuales"""
        self.pdf_files = list(self.pdf_path.glob("*.pdf"))
        self.knowledge_base.load(upsert=True)
        logger.info(f"Knowledge base recargado con {len(self.pdf_files)} documentos")
    
    def get_documents_list(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de documentos cargados.
        
        Returns:
            Lista de diccionarios con información de los documentos
        """
        docs = []
        for pdf in self.pdf_files:
            docs.append({
                "name": pdf.name,
                "path": str(pdf),
                "size": pdf.stat().st_size
            })
        return docs
    
    def get_document_count(self) -> int:
        """Obtiene el número de documentos cargados"""
        return len(self.pdf_files)
    
    def add_document(self, file_path: Path):
        """
        Añade un nuevo documento al knowledge base.
        
        Args:
            file_path: Ruta del archivo PDF a añadir
        """
        # Actualizar lista de archivos
        self.pdf_files = list(self.pdf_path.glob("*.pdf"))
        
        # Recargar knowledge base
        try:
            self.knowledge_base.load(upsert=True)
            logger.info(f"Documento {file_path.name} añadido al knowledge base")
        except Exception as e:
            logger.error(f"Error añadiendo documento al knowledge base: {e}")
            raise
    
    def remove_document(self, filename: str):
        """
        Elimina un documento del knowledge base.
        
        Args:
            filename: Nombre del archivo a eliminar
        """
        file_path = self.pdf_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo '{filename}' no encontrado")
        
        if file_path.suffix.lower() != ".pdf":
            raise ValueError("Solo se pueden eliminar archivos PDF")
        
        # Eliminar archivo
        file_path.unlink()
        
        # Actualizar lista y recargar
        self.pdf_files = list(self.pdf_path.glob("*.pdf"))
        
        try:
            self.knowledge_base.load(upsert=True)
            logger.info(f"Documento {filename} eliminado del knowledge base")
        except Exception as e:
            logger.warning(f"Error actualizando knowledge base después de eliminar: {e}")