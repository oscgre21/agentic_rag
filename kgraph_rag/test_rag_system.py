#!/usr/bin/env python3
"""
Test script for the RAG systems
"""

from markdown_rag_vectordb import MarkdownRAGSystem, build_rag_system, query_rag
import os

def test_vector_rag():
    """Test the vector RAG system"""
    print("=== Testing Vector RAG System ===\n")
    
    # Initialize system
    rag_system = MarkdownRAGSystem()
    
    # Build index if needed
    if not os.path.exists(rag_system.persist_dir):
        print("Building vector database from scratch...")
        rag_system.build_and_index()
    else:
        print("Loading existing vector database...")
        rag_system.create_or_load_vectorstore()
    
    # Test queries
    test_queries = [
        "¿Cuál es el límite de cobertura anual?",
        "¿Qué cubre el plan IDEAL GUARANTEE?",
        "¿Cuáles son las exclusiones principales?",
        "¿Qué es un deducible?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {query}")
        print(f"{'='*60}")
        
        answer = rag_system.query(query)
        print(answer)
        
        # Also test similarity search
        print("\n--- Direct Similarity Search ---")
        similar_docs = rag_system.similarity_search(query, k=3)
        for j, doc in enumerate(similar_docs, 1):
            print(f"\n{j}. Score: {doc['similarity_score']}")
            print(f"   File: {doc['metadata'].get('filename', 'Unknown')}")
            print(f"   Preview: {doc['content'][:100]}...")
    
    # Clear memory between different topics
    rag_system.clear_memory()
    
    print("\n✅ Vector RAG test completed!")

def test_hybrid_system():
    """Test the hybrid RAG system"""
    print("\n\n=== Testing Hybrid RAG System ===\n")
    
    try:
        from hybrid_rag_system import HybridRAGSystem, setup_hybrid_system
        
        # Initialize system
        hybrid_system = setup_hybrid_system()
        
        # Test queries
        test_queries = [
            "¿Cuál es el límite máximo de cobertura?",
            "¿Qué procedimientos requieren autorización previa?",
            "¿Cómo funciona el deducible familiar?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'='*60}")
            print(f"Hybrid Query {i}: {query}")
            print(f"{'='*60}")
            
            answer = hybrid_system.hybrid_query(query)
            print(answer)
        
        # Test comparison
        print("\n\n=== Method Comparison ===")
        hybrid_system.compare_methods("¿Qué cubre el seguro de salud?")
        
        print("\n✅ Hybrid RAG test completed!")
        
    except Exception as e:
        print(f"❌ Error testing hybrid system: {str(e)}")
        print("Make sure Neo4j is running and the Knowledge Graph is populated")

def main():
    """Run all tests"""
    print("Testing RAG Systems for Health Products\n")
    
    # Test vector RAG
    test_vector_rag()
    
    # Test hybrid system (if available)
    test_hybrid_system()
    
    print("\n\n🎉 All tests completed!")

if __name__ == "__main__":
    main()