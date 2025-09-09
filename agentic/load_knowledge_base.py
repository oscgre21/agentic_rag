#!/usr/bin/env python
"""
Script para cargar el knowledge base en la base de datos.
Ejecutar solo cuando se necesite actualizar los datos.
"""

from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector, SearchType
import sys

def load_knowledge_base():
    print("Iniciando carga del knowledge base...")
    
    db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
    
    knowledge_base = PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=PgVector(
            table_name="recipes_ollama",
            db_url=db_url,
            search_type=SearchType.hybrid,
            embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
        ),
    )
    
    try:
        knowledge_base.load(upsert=True)
        print("✅ Knowledge base cargado exitosamente!")
        return True
    except Exception as e:
        print(f"❌ Error al cargar knowledge base: {e}")
        return False

if __name__ == "__main__":
    success = load_knowledge_base()
    sys.exit(0 if success else 1)