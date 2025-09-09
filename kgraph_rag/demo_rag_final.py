#!/usr/bin/env python3
"""
Simple demonstration of the Vector RAG system working
"""

from markdown_rag_vectordb import MarkdownRAGSystem
import os
import re

def clean_response(text):
    """Remove think tags and clean response"""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text.strip()

def main():
    print("=== Demostración del Sistema RAG con Vector Database ===\n")
    
    # Initialize system
    print("Inicializando sistema...")
    rag = MarkdownRAGSystem()
    
    # Load or build vector database
    if not os.path.exists(rag.persist_dir):
        print("Construyendo base de datos vectorial...")
        rag.build_and_index()
    else:
        print("Cargando base de datos existente...")
        rag.create_or_load_vectorstore()
    
    print("\n✅ Sistema listo!\n")
    
    # Demo queries
    queries = [
        "¿Cuál es el límite de cobertura anual del plan IDEAL GUARANTEE?",
        "¿Qué pasa si necesito servicios fuera de la red de proveedores?",
        "¿Cuáles son los beneficios para trasplantes de órganos?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*70}")
        print(f"📝 Pregunta {i}: {query}")
        print(f"{'='*70}\n")
        
        # Get answer
        answer = rag.query(query, include_sources=True)
        answer = clean_response(answer)
        
        print("💡 Respuesta:")
        print(answer)
        
        # Show similarity search results
        print("\n🔍 Búsqueda por similitud (top 3):")
        similar = rag.similarity_search(query, k=3)
        for j, doc in enumerate(similar, 1):
            print(f"\n{j}. Score: {doc['similarity_score']:.3f}")
            print(f"   Archivo: {doc['metadata'].get('filename', 'Unknown')}")
            print(f"   Vista previa: {doc['content'][:100]}...")
    
    print("\n\n✅ Demostración completada!")
    print("\n📌 El sistema RAG está funcionando correctamente con:")
    print("   - Base de datos vectorial: Chroma (persistente)")
    print("   - Embeddings locales: Ollama (nomic-embed-text)")
    print("   - LLM: Ollama (qwen2.5:7b-instruct)")
    print("   - Documentos procesados: archivos markdown de productos de salud")

if __name__ == "__main__":
    main()