#!/usr/bin/env python3
"""
Test script for the enhanced graph processing pipeline
"""

from dotenv import load_dotenv
import os
from langchain_neo4j import Neo4jGraph
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document

load_dotenv()

print("Testing Enhanced Pipeline...")
print("="*50)

# Initialize components
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

print("1. Initializing LLM...")
chat = ChatOllama(model="qwen2.5:7b-instruct", temperature=0)

print("2. Connecting to Neo4j...")
kg = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
)

# Test with sample health product text
sample_text = """
El Ibuprofeno 600mg es un medicamento antiinflamatorio no esteroideo (AINE) 
fabricado por Laboratorios Normon. Contiene ibuprofeno como principio activo.

Está indicado para el tratamiento del dolor leve a moderado, como dolor de cabeza, 
dolor dental, dolor muscular, y para reducir la fiebre. También se utiliza en 
procesos inflamatorios.

La dosis recomendada para adultos es de 1 comprimido cada 8 horas. No debe 
excederse la dosis máxima de 2400mg al día.

Contraindicaciones: No debe usarse en pacientes con úlcera péptica activa, 
insuficiencia cardíaca grave, o alergia al ibuprofeno. Puede interactuar con 
anticoagulantes como la warfarina.

Efectos secundarios comunes incluyen molestias gastrointestinales, náuseas, 
y en casos raros, reacciones alérgicas.
"""

print("3. Creating health product extraction prompt...")
health_prompt = ChatPromptTemplate.from_template("""
Extrae entidades y relaciones de productos de salud del siguiente texto.

Identifica:
- Productos/Medicamentos (tipo: Product)
- Ingredientes activos (tipo: ActiveIngredient)
- Fabricantes (tipo: Manufacturer)
- Síntomas que trata (tipo: Symptom)
- Contraindicaciones (tipo: Contraindication)
- Efectos secundarios (tipo: SideEffect)

Relaciones:
- CONTAINS: Producto contiene ingrediente
- MANUFACTURED_BY: Producto fabricado por
- RELIEVES: Producto alivia síntoma
- CONTRAINDICATED_FOR: Contraindicado para condición
- MAY_CAUSE: Puede causar efecto

Texto: {input}
""")

print("4. Initializing graph transformer...")
llm_transformer = LLMGraphTransformer(
    llm=chat,
    prompt=health_prompt,
    allowed_nodes=["Product", "ActiveIngredient", "Manufacturer", 
                   "Symptom", "Contraindication", "SideEffect"],
    allowed_relationships=["CONTAINS", "MANUFACTURED_BY", "RELIEVES",
                          "CONTRAINDICATED_FOR", "MAY_CAUSE"]
)

print("5. Processing sample document...")
sample_doc = Document(page_content=sample_text, metadata={"source": "test"})

try:
    graph_docs = llm_transformer.convert_to_graph_documents([sample_doc])
    print(f"   Generated {len(graph_docs)} graph documents")
    
    if graph_docs:
        graph_doc = graph_docs[0]
        print(f"   Extracted {len(graph_doc.nodes)} nodes")
        print(f"   Extracted {len(graph_doc.relationships)} relationships")
        
        # Show extracted entities
        print("\n6. Extracted Entities:")
        for node in graph_doc.nodes[:5]:  # Show first 5
            print(f"   - {node.type}: {node.id}")
        
        print("\n7. Extracted Relationships:")
        for rel in graph_doc.relationships[:5]:  # Show first 5
            print(f"   - {rel.source.id} -[{rel.type}]-> {rel.target.id}")
    
    # Clear and store in Neo4j
    print("\n8. Storing in Neo4j...")
    kg.query("MATCH (n:Product {id: 'test_product'}) DETACH DELETE n")
    
    # Store the graph
    kg.add_graph_documents(graph_docs)
    
    # Query the graph
    print("\n9. Testing graph queries:")
    
    # Find products containing ibuprofeno
    query = """
    MATCH (p:Product)-[:CONTAINS]->(i:ActiveIngredient)
    WHERE toLower(i.id) CONTAINS 'ibuprofeno'
    RETURN p.id as product, i.id as ingredient
    LIMIT 5
    """
    results = kg.query(query)
    print(f"   Products with ibuprofeno: {len(results)} found")
    for r in results:
        print(f"     - {r.get('product', 'N/A')}")
    
    # Find symptoms
    query2 = """
    MATCH (s:Symptom)
    RETURN s.id as symptom
    LIMIT 5
    """
    results2 = kg.query(query2)
    print(f"   Symptoms found: {len(results2)}")
    for r in results2:
        print(f"     - {r.get('symptom', 'N/A')}")
    
    print("\n✅ Enhanced pipeline test completed successfully!")
    
except Exception as e:
    print(f"\n❌ Error during processing: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("Test completed")