#!/usr/bin/env python3
"""
Script para reconstruir tanto el Knowledge Graph como la Vector Database
desde los archivos PDF en la carpeta docs/
"""

import os
import subprocess
import sys
from pathlib import Path

def check_neo4j():
    """Verifica si Neo4j está corriendo"""
    print("🔍 Verificando Neo4j...")
    result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True)
    if "neo4j" in result.stdout and "Up" in result.stdout:
        print("✅ Neo4j está corriendo")
        return True
    else:
        print("❌ Neo4j no está corriendo")
        print("Iniciando Neo4j...")
        subprocess.run(["docker-compose", "up", "-d"])
        import time
        time.sleep(10)  # Esperar a que Neo4j inicie
        return True

def rebuild_knowledge_graph():
    """Reconstruye el Knowledge Graph desde PDFs"""
    print("\n📊 Reconstruyendo Knowledge Graph...")
    
    # Verificar que existan PDFs
    pdf_dir = Path("./docs")
    pdfs = list(pdf_dir.glob("*.pdf"))
    print(f"   Encontrados {len(pdfs)} archivos PDF:")
    for pdf in pdfs:
        print(f"   - {pdf.name}")
    
    if not pdfs:
        print("❌ No se encontraron PDFs en ./docs/")
        return False
    
    # Ejecutar el procesador
    print("\n   Procesando PDFs...")
    try:
        subprocess.run([sys.executable, "kgraph_rag/bmi_process_graph.py"], check=True)
        print("✅ Knowledge Graph reconstruido exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al procesar PDFs: {e}")
        return False

def rebuild_vector_database():
    """Reconstruye la base de datos vectorial desde markdown"""
    print("\n📚 Reconstruyendo Vector Database...")
    
    # Verificar archivos markdown
    markdown_dir = Path("./markdown_output")
    if not markdown_dir.exists():
        print("❌ No existe la carpeta markdown_output")
        print("   Primero debes procesar los PDFs para el Knowledge Graph")
        return False
    
    markdowns = list(markdown_dir.glob("*.md"))
    print(f"   Encontrados {len(markdowns)} archivos markdown")
    
    # Eliminar base de datos existente
    import shutil
    if Path("./chroma_db").exists():
        print("   Eliminando base de datos anterior...")
        shutil.rmtree("./chroma_db")
    
    # Reconstruir
    print("   Construyendo nueva base de datos vectorial...")
    try:
        from kgraph_rag.markdown_rag_vectordb import MarkdownRAGSystem
        rag = MarkdownRAGSystem()
        rag.build_and_index()
        print("✅ Vector Database reconstruida exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error al construir vector database: {e}")
        return False

def test_systems():
    """Prueba que ambos sistemas funcionen"""
    print("\n🧪 Probando sistemas...")
    
    # Probar Vector RAG
    try:
        from kgraph_rag.markdown_rag_vectordb import query_rag
        result = query_rag("¿Qué es IDEAL GUARANTEE?")
        if result:
            print("✅ Vector RAG funcionando")
        else:
            print("⚠️  Vector RAG responde pero sin resultados")
    except Exception as e:
        print(f"❌ Error en Vector RAG: {e}")
    
    # Probar Knowledge Graph
    try:
        from langchain_neo4j import Neo4jGraph
        from dotenv import load_dotenv
        load_dotenv()
        
        kg = Neo4jGraph(
            url=os.environ["NEO4J_URI"],
            username=os.environ["NEO4J_USERNAME"],
            password=os.environ["NEO4J_PASSWORD"]
        )
        
        result = kg.query("MATCH (n) RETURN count(n) as total")
        total = result[0]['total'] if result else 0
        print(f"✅ Knowledge Graph funcionando ({total} nodos)")
    except Exception as e:
        print(f"❌ Error en Knowledge Graph: {e}")

def main():
    """Proceso principal de reconstrucción"""
    print("=== Reconstrucción Completa del Sistema RAG ===\n")
    
    # Paso 1: Verificar Neo4j
    if not check_neo4j():
        print("\n❌ No se pudo iniciar Neo4j")
        return
    
    # Paso 2: Reconstruir Knowledge Graph
    if not rebuild_knowledge_graph():
        print("\n⚠️  Continuando sin Knowledge Graph...")
    
    # Paso 3: Reconstruir Vector Database
    if not rebuild_vector_database():
        print("\n❌ No se pudo reconstruir Vector Database")
        return
    
    # Paso 4: Probar sistemas
    test_systems()
    
    print("\n✅ ¡Reconstrucción completa!")
    print("\n📝 Próximos pasos:")
    print("1. Para consultas solo con Vector RAG:")
    print("   python kgraph_rag/simple_rag_demo.py")
    print("\n2. Para sistema híbrido (KG + Vector):")
    print("   python kgraph_rag/hybrid_rag_system.py")

if __name__ == "__main__":
    main()