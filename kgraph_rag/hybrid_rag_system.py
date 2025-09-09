from dotenv import load_dotenv
import os
from typing import List, Dict, Tuple
from langchain_neo4j import Neo4jGraph
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from markdown_rag_vectordb import MarkdownRAGSystem

load_dotenv()

# Configuration
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

# Initialize components
print("Initializing hybrid RAG system...")
llm = ChatOllama(model="qwen3:4b", temperature=0)
kg = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
vector_rag = MarkdownRAGSystem()

class HybridRAGSystem:
    """Combines Knowledge Graph and Vector Database for enhanced RAG"""
    
    def __init__(self, kg: Neo4jGraph, vector_rag: MarkdownRAGSystem, llm):
        self.kg = kg
        self.vector_rag = vector_rag
        self.llm = llm
        
        # Load vector store if exists
        if os.path.exists(vector_rag.persist_dir):
            self.vector_rag.create_or_load_vectorstore()
        
    def extract_entities_from_question(self, question: str) -> List[str]:
        """Extract key entities from the question"""
        
        entity_prompt = ChatPromptTemplate.from_template("""
        Extract key entities from this health insurance question.
        Only return entity names found in the question, separated by commas.
        DO NOT include explanations or thinking process.
        
        Examples:
        Question: "What is the coverage limit?" → coverage, limit
        Question: "Does it cover diabetes treatment?" → diabetes, treatment
        Question: "What is IDEAL GUARANTEE?" → IDEAL GUARANTEE
        
        Question: {question}
        
        Entities:""")
        
        chain = entity_prompt | self.llm | StrOutputParser()
        entities_str = chain.invoke({"question": question})
        
        # Clean response - remove any <think> tags and extract only valid entities
        import re
        entities_str = re.sub(r'<think>.*?</think>', '', entities_str, flags=re.DOTALL)
        entities_str = entities_str.strip()
        
        # Extract only alphanumeric entities
        entities = []
        if entities_str:
            # Split by common delimiters and clean
            potential_entities = re.split(r'[,;|\n]', entities_str)
            for e in potential_entities:
                e = e.strip()
                # Only keep reasonable entities (not full sentences)
                if e and len(e) < 50 and not e.startswith('<') and not e.startswith('['):
                    entities.append(e)
        
        # Fallback: extract key terms from the question itself
        if not entities:
            # Extract capitalized words and important terms
            words = question.split()
            for word in words:
                if word.isupper() or (word[0].isupper() and len(word) > 2):
                    entities.append(word.strip('?.,!'))
            
            # Add common health insurance terms if present
            health_terms = ['coverage', 'limit', 'deductible', 'cobertura', 'límite', 'deducible']
            for term in health_terms:
                if term.lower() in question.lower():
                    entities.append(term)
        
        return list(set(entities))[:5]  # Return max 5 unique entities
    
    def query_knowledge_graph(self, question: str, entities: List[str]) -> Tuple[str, List]:
        """Query knowledge graph for structured information"""
        
        # Build dynamic Cypher query with proper escaping
        entity_conditions = []
        for entity in entities:
            # Escape single quotes in entity names
            escaped_entity = entity.replace("'", "\\'")
            entity_conditions.append(f"""
                toLower(n.name) CONTAINS toLower('{escaped_entity}') OR
                toLower(n.original_name) CONTAINS toLower('{escaped_entity}')
            """)
        
        where_clause = " OR ".join(entity_conditions) if entity_conditions else "1=1"
        
        cypher_query = f"""
        MATCH (n)
        WHERE {where_clause}
        OPTIONAL MATCH (n)-[r]-(related)
        OPTIONAL MATCH (doc:Document)-[:MENTIONS]->(n)
        OPTIONAL MATCH (file:File)-[:CONTAINS]->(n)
        RETURN n as node, 
               collect(DISTINCT {{
                   type: type(r), 
                   related_node: related,
                   related_labels: labels(related)
               }}) as relationships,
               collect(DISTINCT doc) as documents,
               collect(DISTINCT file) as files
        LIMIT 20
        """
        
        results = self.kg.query(cypher_query)
        
        # Format graph context
        graph_context = "### Información del Knowledge Graph:\n"
        sources = set()
        
        for result in results:
            if result.get('node'):
                node = result['node']
                node_info = f"\n**{node.get('name', node.get('id', 'Unknown'))}**"
                
                # Add node properties
                for key, value in node.items():
                    if key not in ['id', 'name'] and value:
                        node_info += f"\n  - {key}: {value}"
                
                graph_context += node_info
                
                # Add relationships
                if result.get('relationships'):
                    for rel in result['relationships']:
                        if rel and rel.get('related_node'):
                            related = rel['related_node']
                            rel_type = rel.get('type', 'RELATED')
                            graph_context += f"\n  → {rel_type}: {related.get('name', 'Unknown')}"
                
                # Track sources
                if result.get('files'):
                    for file in result['files']:
                        if file:
                            sources.add(file.get('filename', 'Unknown'))
        
        return graph_context, list(sources)
    
    def query_vector_store(self, question: str) -> Tuple[str, List]:
        """Query vector store for relevant text chunks"""
        
        if not self.vector_rag.vectorstore:
            return "", []
        
        # Get relevant documents
        results = self.vector_rag.similarity_search(question, k=5)
        
        vector_context = "\n### Información de documentos (Vector RAG):\n"
        sources = set()
        
        for i, result in enumerate(results, 1):
            vector_context += f"\n**Fragmento {i}** (Similitud: {result['similarity_score']}):\n"
            vector_context += f"{result['content'][:300]}...\n"
            
            # Track sources
            filename = result['metadata'].get('filename', 'Unknown')
            page = result['metadata'].get('page', None)
            if page:
                sources.add(f"{filename} (página {page})")
            else:
                sources.add(filename)
        
        return vector_context, list(sources)
    
    def hybrid_query(self, question: str) -> str:
        """Perform hybrid query combining KG and Vector search"""
        
        print("🔍 Extrayendo entidades...")
        entities = self.extract_entities_from_question(question)
        print(f"   Entidades encontradas: {entities}")
        
        print("🔎 Consultando Knowledge Graph...")
        kg_context, kg_sources = self.query_knowledge_graph(question, entities)
        
        print("📚 Consultando Vector Store...")
        vector_context, vector_sources = self.query_vector_store(question)
        
        # Combine contexts
        combined_context = kg_context + "\n\n" + vector_context
        all_sources = list(set(kg_sources + vector_sources))
        
        # Generate final answer
        answer_prompt = ChatPromptTemplate.from_template("""
        Eres un experto en productos de salud. Usa la siguiente información para responder la pregunta.
        
        {context}
        
        Pregunta: {question}
        
        Proporciona una respuesta completa y precisa basada en la información disponible.
        Si la información del Knowledge Graph y los documentos se complementan, combínalas coherentemente.
        No inventes información que no esté en el contexto proporcionado.
        """)
        
        chain = answer_prompt | self.llm | StrOutputParser()
        answer = chain.invoke({"context": combined_context, "question": question})
        
        # Add sources
        if all_sources:
            answer += "\n\n📄 **Fuentes consultadas:**"
            for source in sorted(all_sources):
                answer += f"\n- {source}"
        
        # Add search method info
        answer += "\n\n🔍 **Métodos de búsqueda utilizados:**"
        answer += "\n- Knowledge Graph: Relaciones estructuradas entre entidades"
        answer += "\n- Vector RAG: Búsqueda semántica en documentos"
        
        return answer
    
    def compare_methods(self, question: str):
        """Compare results from different methods"""
        
        print("\n=== Comparación de métodos de búsqueda ===\n")
        
        # Method 1: Knowledge Graph only
        print("1️⃣ **Solo Knowledge Graph:**")
        entities = self.extract_entities_from_question(question)
        kg_context, kg_sources = self.query_knowledge_graph(question, entities)
        if kg_context.strip():
            print(kg_context[:500] + "...")
        else:
            print("   No se encontró información relevante")
        
        # Method 2: Vector RAG only
        print("\n2️⃣ **Solo Vector RAG:**")
        vector_context, vector_sources = self.query_vector_store(question)
        if vector_context.strip():
            print(vector_context[:500] + "...")
        else:
            print("   No se encontró información relevante")
        
        # Method 3: Hybrid
        print("\n3️⃣ **Método Híbrido (KG + Vector):**")
        hybrid_answer = self.hybrid_query(question)
        print(hybrid_answer)

# Helper functions
def setup_hybrid_system():
    """Setup the hybrid RAG system"""
    system = HybridRAGSystem(kg, vector_rag, llm)
    
    # Build vector store if needed
    if not os.path.exists(vector_rag.persist_dir):
        print("Building vector database...")
        vector_rag.build_and_index()
    
    return system

if __name__ == "__main__":
    print("=== Sistema RAG Híbrido (KG + Vector) ===\n")
    
    # Initialize system
    hybrid_system = setup_hybrid_system()
    
    # Example queries
    example_queries = [
        "¿Cuál es el límite de cobertura anual?",
        "¿Qué medicamentos contienen paracetamol?",
        "¿Cuáles son los efectos secundarios del ibuprofeno?",
        "¿Qué cubre el seguro IDEAL GUARANTEE?"
    ]
    
    print("Ejemplos de consultas:")
    for i, q in enumerate(example_queries, 1):
        print(f"{i}. {q}")
    
    print("\nComandos especiales:")
    print("- 'comparar': Comparar métodos de búsqueda")
    print("- 'salir': Terminar el programa\n")
    
    while True:
        question = input("\n💬 Pregunta: ").strip()
        
        if question.lower() == 'salir':
            break
        elif question.lower() == 'comparar':
            test_question = input("Pregunta para comparar: ").strip()
            if test_question:
                hybrid_system.compare_methods(test_question)
        elif question:
            print("\n🤖 Procesando con sistema híbrido...")
            answer = hybrid_system.hybrid_query(question)
            print(f"\n📊 Respuesta:\n{answer}")