#!/usr/bin/env python3
"""
Demo script for testing hybrid RAG system without interactive input
"""

from hybrid_rag_system import HybridRAGSystem, setup_hybrid_system, kg, vector_rag, llm
import os

def test_entity_extraction():
    """Test the improved entity extraction"""
    print("=== Testing Entity Extraction ===\n")
    
    system = HybridRAGSystem(kg, vector_rag, llm)
    
    test_questions = [
        "What is the coverage limit of IDEAL GUARANTEE?",
        "¿Cuál es el límite de cobertura anual?",
        "Does it cover diabetes treatment?",
        "¿Qué medicamentos están excluidos?"
    ]
    
    for q in test_questions:
        print(f"Question: {q}")
        entities = system.extract_entities_from_question(q)
        print(f"Entities: {entities}")
        print("-" * 50)

def test_hybrid_queries():
    """Test hybrid queries with both KG and vector search"""
    print("\n\n=== Testing Hybrid Queries ===\n")
    
    try:
        system = setup_hybrid_system()
        
        # Test queries
        queries = [
            "What is IDEAL GUARANTEE coverage limit?",
            "¿Qué tratamientos están excluidos?",
            "What is the deductible amount?"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n{'='*70}")
            print(f"Query {i}: {query}")
            print(f"{'='*70}\n")
            
            try:
                # Test hybrid query
                answer = system.hybrid_query(query)
                
                # Clean any think tags
                import re
                answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
                answer = answer.strip()
                
                print("Answer:")
                print(answer)
                
            except Exception as e:
                print(f"Error processing query: {str(e)}")
                print("This might be due to Neo4j not running or empty Knowledge Graph")
    
    except Exception as e:
        print(f"Error setting up hybrid system: {str(e)}")
        print("Make sure Neo4j is running: docker-compose up -d")

def test_vector_only():
    """Test vector RAG only (no KG required)"""
    print("\n\n=== Testing Vector RAG Only ===\n")
    
    from markdown_rag_vectordb import MarkdownRAGSystem
    
    rag = MarkdownRAGSystem()
    if not os.path.exists(rag.persist_dir):
        print("Building vector database...")
        rag.build_and_index()
    else:
        rag.create_or_load_vectorstore()
    
    # Test query
    query = "What is the annual coverage limit for IDEAL GUARANTEE?"
    print(f"Query: {query}\n")
    
    answer = rag.query(query, include_sources=True)
    
    # Clean think tags
    import re
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
    answer = answer.strip()
    
    print("Answer from Vector RAG:")
    print(answer)

def main():
    """Run all tests"""
    print("Testing Hybrid RAG System Components\n")
    
    # Test 1: Entity extraction
    test_entity_extraction()
    
    # Test 2: Vector RAG only (always works)
    test_vector_only()
    
    # Test 3: Hybrid system (requires Neo4j)
    test_hybrid_queries()
    
    print("\n\n✅ All tests completed!")

if __name__ == "__main__":
    main()