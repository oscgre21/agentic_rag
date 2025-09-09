#!/usr/bin/env python3
"""
Simple demo of the RAG system with health product documents
"""

from markdown_rag_vectordb import MarkdownRAGSystem
import os

def main():
    print("=== Sistema RAG para Productos de Salud ===\n")
    
    # Initialize RAG system
    rag_system = MarkdownRAGSystem()
    
    # Check if vector database exists
    if not os.path.exists(rag_system.persist_dir):
        print("Construyendo base de datos vectorial...")
        rag_system.build_and_index()
    else:
        print("Cargando base de datos existente...")
        rag_system.create_or_load_vectorstore()
    
    # Demo queries
    demo_queries = [
        "¿Cuál es el límite máximo de cobertura anual del plan IDEAL GUARANTEE?",
        "¿Qué tratamientos están excluidos de la cobertura?",
        "¿Cómo funciona el deducible en el plan IDEAL?",
        "¿Qué pasa si necesito servicios fuera de la red de proveedores?",
        "¿Cuáles son los requisitos de notificación antes de una hospitalización?"
    ]
    
    print("\n📋 Consultas de demostración:\n")
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'='*70}")
        print(f"Pregunta {i}: {query}")
        print(f"{'='*70}\n")
        
        # Get answer
        answer = rag_system.query(query, include_sources=True)
        
        # Clean up any <think> tags
        import re
        answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
        answer = answer.strip()
        
        print("📝 Respuesta:")
        print(answer)
        
        # Clear memory between different topics
        if i % 2 == 0:
            rag_system.clear_memory()
            print("\n[Memoria conversacional limpiada]")
    
    # Interactive mode
    print("\n\n" + "="*70)
    print("💬 Modo interactivo - Escribe tu pregunta (o 'salir' para terminar)")
    print("="*70 + "\n")
    
    while True:
        user_query = input("\n❓ Tu pregunta: ").strip()
        
        if user_query.lower() in ['salir', 'exit', 'quit']:
            print("\n👋 ¡Hasta luego!")
            break
        
        if not user_query:
            continue
        
        print("\n🤔 Procesando...\n")
        
        # Get answer
        answer = rag_system.query(user_query, include_sources=True)
        
        # Clean up any <think> tags
        answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
        answer = answer.strip()
        
        print("📝 Respuesta:")
        print(answer)

if __name__ == "__main__":
    main()