"""
Enhanced RAG Query System with Smart Routing and Hybrid Search
For BMI Healthcare Knowledge Graph
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from langchain_neo4j import Neo4jGraph
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class QueryResult:
    """Structure for query results"""
    content: str
    source: str
    confidence: float
    metadata: Dict[str, Any]


class SmartQueryRouter:
    """Intelligent query routing based on intent detection"""
    
    def __init__(self, kg: Neo4jGraph, llm: ChatOllama):
        self.kg = kg
        self.llm = llm
        self.query_templates = {
            'symptom_search': """
                MATCH (s:Symptom)-[:INCLUDES*0..1]-(sg:SymptomGroup)
                WHERE toLower(s.name) CONTAINS toLower($term)
                   OR toLower(sg.name) CONTAINS toLower($term)
                MATCH (s)<-[:RELIEVES]-(p:Product)
                OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
                OPTIONAL MATCH (p)-[:CONTRAINDICATED_FOR]->(c:Contraindication)
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(cat:Category)
                OPTIONAL MATCH (d:Document)-[:MENTIONS]->(p)
                RETURN DISTINCT p.name as product,
                       p.description as description,
                       COLLECT(DISTINCT i.name) as ingredients,
                       COLLECT(DISTINCT c.name) as contraindications,
                       COLLECT(DISTINCT cat.name) as categories,
                       s.name as symptom,
                       COLLECT(DISTINCT {filename: d.filename, page: d.page}) as sources
                ORDER BY p.confidence_score DESC
                LIMIT 10
            """,
            
            'interaction_check': """
                MATCH (p1:Product)
                WHERE toLower(p1.name) CONTAINS toLower($product1)
                MATCH (p2:Product)
                WHERE toLower(p2.name) CONTAINS toLower($product2)
                OPTIONAL MATCH (p1)-[:INTERACTS_WITH]-(p2)
                OPTIONAL MATCH (p1)-[:CONTAINS]->(i1:ActiveIngredient)
                OPTIONAL MATCH (p2)-[:CONTAINS]->(i2:ActiveIngredient)
                OPTIONAL MATCH (i1)-[:INTERACTS_WITH]-(i2)
                RETURN p1.name as product1,
                       p2.name as product2,
                       EXISTS((p1)-[:INTERACTS_WITH]-(p2)) as direct_interaction,
                       EXISTS((i1)-[:INTERACTS_WITH]-(i2)) as ingredient_interaction,
                       COLLECT(DISTINCT i1.name) as ingredients1,
                       COLLECT(DISTINCT i2.name) as ingredients2
            """,
            
            'alternative_products': """
                MATCH (p:Product)
                WHERE toLower(p.name) CONTAINS toLower($product)
                MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
                MATCH (i)<-[:CONTAINS]-(alt:Product)
                WHERE alt.id <> p.id
                OPTIONAL MATCH (alt)-[:BELONGS_TO]->(c:Category)
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(pc:Category)
                OPTIONAL MATCH (alt)-[:RELIEVES]->(s:Symptom)
                WITH alt, p, 
                     COLLECT(DISTINCT c.name) as categories,
                     COLLECT(DISTINCT pc.name) as original_categories,
                     COUNT(DISTINCT i) as shared_ingredients,
                     COLLECT(DISTINCT s.name) as symptoms
                RETURN alt.name as alternative,
                       alt.description as description,
                       categories,
                       shared_ingredients,
                       symptoms,
                       CASE 
                         WHEN categories = original_categories THEN 3
                         WHEN ANY(c IN categories WHERE c IN original_categories) THEN 2
                         ELSE 1
                       END as category_match_score
                ORDER BY category_match_score DESC, shared_ingredients DESC
                LIMIT 10
            """,
            
            'contraindication_check': """
                MATCH (p:Product)
                WHERE toLower(p.name) CONTAINS toLower($product)
                OPTIONAL MATCH (p)-[:CONTRAINDICATED_FOR]->(c:Contraindication)
                OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
                OPTIONAL MATCH (i)-[:CONTRAINDICATED_FOR]->(ic:Contraindication)
                RETURN p.name as product,
                       COLLECT(DISTINCT c.name) as direct_contraindications,
                       COLLECT(DISTINCT ic.name) as ingredient_contraindications,
                       COLLECT(DISTINCT i.name) as ingredients
            """,
            
            'general': """
                // General search combining multiple aspects
                MATCH (p:Product)
                WHERE toLower(p.name) CONTAINS toLower($term)
                   OR toLower(p.description) CONTAINS toLower($term)
                OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
                OPTIONAL MATCH (p)-[:RELIEVES]->(s:Symptom)
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
                OPTIONAL MATCH (d:Document)-[:MENTIONS]->(p)
                RETURN p.name as product,
                       p.description as description,
                       COLLECT(DISTINCT i.name) as ingredients,
                       COLLECT(DISTINCT s.name) as symptoms,
                       COLLECT(DISTINCT c.name) as categories,
                       COLLECT(DISTINCT {filename: d.filename, page: d.page}) as sources
                LIMIT 10
            """
        }
    
    def classify_query(self, question: str) -> Tuple[str, Dict[str, Any]]:
        """Classify query intent and extract parameters"""
        
        classification_prompt = ChatPromptTemplate.from_template("""
        Analiza esta pregunta sobre productos de salud y clasifícala en una categoría.
        
        Categorías:
        - symptom_search: búsqueda de productos para síntomas específicos
        - interaction_check: verificación de interacciones entre dos productos
        - alternative_products: búsqueda de productos alternativos o similares
        - contraindication_check: consulta sobre contraindicaciones
        - general: consulta general sobre productos
        
        También extrae los parámetros relevantes (productos, síntomas, etc.)
        
        Pregunta: {question}
        
        Responde en formato:
        Categoría: [categoria]
        Parámetros: [parametros separados por comas]
        """)
        
        response = self.llm.invoke(
            classification_prompt.format(question=question)
        )
        
        # Parse response
        lines = response.strip().split('\n')
        category = 'general'
        params = {}
        
        for line in lines:
            if 'Categoría:' in line or 'Categoria:' in line:
                category = line.split(':')[1].strip().lower()
            elif 'Parámetros:' in line or 'Parametros:' in line:
                param_str = line.split(':')[1].strip()
                param_list = [p.strip() for p in param_str.split(',')]
                
                # Map parameters based on category
                if category == 'interaction_check' and len(param_list) >= 2:
                    params = {'product1': param_list[0], 'product2': param_list[1]}
                elif category == 'alternative_products' and param_list:
                    params = {'product': param_list[0]}
                elif category == 'contraindication_check' and param_list:
                    params = {'product': param_list[0]}
                elif param_list:
                    params = {'term': param_list[0]}
        
        # Default parameter if none found
        if not params:
            params = {'term': question}
        
        return category, params
    
    def route_query(self, question: str) -> List[Dict[str, Any]]:
        """Route query to appropriate template and execute"""
        
        category, params = self.classify_query(question)
        template = self.query_templates.get(category, self.query_templates['general'])
        
        try:
            results = self.kg.query(template, params)
            return results
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            # Fallback to general search
            return self.kg.query(self.query_templates['general'], {'term': question})


class HybridGraphSearch:
    """Hybrid search combining vector, graph, and text search"""
    
    def __init__(self, kg: Neo4jGraph, embeddings: HuggingFaceEmbeddings, llm: ChatOllama):
        self.kg = kg
        self.embeddings = embeddings
        self.llm = llm
        self.router = SmartQueryRouter(kg, llm)
    
    def vector_search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """Search using vector embeddings"""
        
        query_embedding = self.embeddings.embed_query(query)
        
        # Note: This is a simplified version. In production, you'd use Neo4j vector indexes
        search_query = """
        MATCH (p:Product)
        WHERE p.has_embedding = true
        WITH p, p.embedding_text as text
        OPTIONAL MATCH (p)-[:RELIEVES]->(s:Symptom)
        OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
        OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
        RETURN p.name as product,
               p.description as description,
               text as embedding_text,
               COLLECT(DISTINCT s.name) as symptoms,
               COLLECT(DISTINCT i.name) as ingredients,
               COLLECT(DISTINCT c.name) as categories
        LIMIT $k
        """
        
        results = self.kg.query(search_query, {'k': k})
        
        # Calculate similarity scores (simplified)
        for result in results:
            if result.get('embedding_text'):
                # In production, you'd compare actual embeddings
                result['vector_score'] = 0.5  # Placeholder score
        
        return results
    
    def graph_search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """Search using graph structure and relationships"""
        
        return self.router.route_query(query)[:k]
    
    def text_search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """Full-text search across product names and descriptions"""
        
        text_query = """
        MATCH (p:Product)
        WHERE toLower(p.name) CONTAINS toLower($query)
           OR toLower(p.description) CONTAINS toLower($query)
        OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
        WHERE toLower(i.name) CONTAINS toLower($query)
        OPTIONAL MATCH (p)-[:RELIEVES]->(s:Symptom)
        WHERE toLower(s.name) CONTAINS toLower($query)
        WITH p, 
             COLLECT(DISTINCT i) as matching_ingredients,
             COLLECT(DISTINCT s) as matching_symptoms
        WHERE p IS NOT NULL OR SIZE(matching_ingredients) > 0 OR SIZE(matching_symptoms) > 0
        RETURN p.name as product,
               p.description as description,
               [i IN matching_ingredients | i.name] as matched_ingredients,
               [s IN matching_symptoms | s.name] as matched_symptoms
        LIMIT $k
        """
        
        return self.kg.query(text_query, {'query': query, 'k': k})
    
    def reciprocal_rank_fusion(self, *result_sets, k: int = 60) -> List[Dict[str, Any]]:
        """Fuse multiple result sets using RRF algorithm"""
        
        scores = {}
        result_data = {}
        
        for results in result_sets:
            for rank, result in enumerate(results):
                # Use product name as key
                doc_id = result.get('product', str(result))
                
                if doc_id not in scores:
                    scores[doc_id] = 0
                    result_data[doc_id] = result
                
                # RRF score calculation
                scores[doc_id] += 1 / (k + rank + 1)
        
        # Sort by score
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return results with scores
        final_results = []
        for doc_id, score in sorted_items:
            result = result_data[doc_id].copy()
            result['fusion_score'] = score
            final_results.append(result)
        
        return final_results
    
    def llm_rerank(self, query: str, results: List[Dict[str, Any]], k: int = 10) -> List[Dict[str, Any]]:
        """Re-rank results using LLM for relevance"""
        
        if not results:
            return []
        
        # Prepare context for reranking
        rerank_prompt = ChatPromptTemplate.from_template("""
        Pregunta del usuario: {query}
        
        Productos encontrados:
        {products}
        
        Ordena estos productos por relevancia para la pregunta del usuario.
        Considera:
        1. Coincidencia directa con síntomas mencionados
        2. Ingredientes activos apropiados
        3. Categoría del producto
        4. Contraindicaciones relevantes
        
        Devuelve los nombres de productos ordenados del más al menos relevante, separados por comas.
        """)
        
        # Format products for prompt
        product_descriptions = []
        for i, result in enumerate(results[:k]):
            desc = f"{i+1}. {result.get('product', 'Unknown')}"
            if result.get('ingredients'):
                desc += f" (Ingredientes: {', '.join(result['ingredients'][:3])})"
            if result.get('symptoms'):
                desc += f" (Para: {', '.join(result['symptoms'][:3])})"
            product_descriptions.append(desc)
        
        products_text = "\n".join(product_descriptions)
        
        # Get reranking from LLM
        response = self.llm.invoke(
            rerank_prompt.format(query=query, products=products_text)
        )
        
        # Parse response and reorder results
        ranked_products = [p.strip() for p in response.split(',')]
        
        # Create reranked list
        reranked = []
        seen = set()
        
        for product_name in ranked_products:
            for result in results:
                if result.get('product') in product_name and result['product'] not in seen:
                    reranked.append(result)
                    seen.add(result['product'])
                    break
        
        # Add any remaining results
        for result in results:
            if result.get('product') not in seen:
                reranked.append(result)
        
        return reranked[:k]
    
    def search(self, query: str, k: int = 10, use_reranking: bool = True) -> List[QueryResult]:
        """Main search method combining all strategies"""
        
        print(f"Searching for: {query}")
        
        # 1. Execute parallel searches
        vector_results = self.vector_search(query, k=k*2)
        graph_results = self.graph_search(query, k=k*2)
        text_results = self.text_search(query, k=k*2)
        
        print(f"Found: {len(vector_results)} vector, {len(graph_results)} graph, {len(text_results)} text results")
        
        # 2. Fuse results
        fused_results = self.reciprocal_rank_fusion(
            vector_results,
            graph_results,
            text_results
        )
        
        # 3. Optional LLM reranking
        if use_reranking and fused_results:
            final_results = self.llm_rerank(query, fused_results, k=k)
        else:
            final_results = fused_results[:k]
        
        # 4. Convert to QueryResult objects
        query_results = []
        for result in final_results:
            # Extract source information
            sources = result.get('sources', [])
            source_text = "Unknown"
            if sources:
                source_text = f"{sources[0].get('filename', 'Unknown')} (p. {sources[0].get('page', '?')})"
            
            query_results.append(QueryResult(
                content=result.get('product', 'Unknown'),
                source=source_text,
                confidence=result.get('fusion_score', 0.0),
                metadata=result
            ))
        
        return query_results


class GraphContextOptimizer:
    """Optimize context extraction from graph for LLM prompts"""
    
    def __init__(self, kg: Neo4jGraph, max_tokens: int = 2000):
        self.kg = kg
        self.max_tokens = max_tokens
    
    def get_optimized_context(self, query: str, initial_nodes: List[str]) -> str:
        """Extract optimized context from graph nodes"""
        
        context_query = """
        UNWIND $node_ids as node_id
        MATCH (p:Product {name: node_id})
        OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
        OPTIONAL MATCH (p)-[:RELIEVES]->(s:Symptom)
        OPTIONAL MATCH (p)-[:CONTRAINDICATED_FOR]->(c:Contraindication)
        OPTIONAL MATCH (p)-[:INTERACTS_WITH]->(inter:Product)
        OPTIONAL MATCH (p)-[:BELONGS_TO]->(cat:Category)
        OPTIONAL MATCH (d:Document)-[:MENTIONS]->(p)
        RETURN p.name as product,
               p.description as description,
               COLLECT(DISTINCT i.name) as ingredients,
               COLLECT(DISTINCT s.name) as symptoms,
               COLLECT(DISTINCT c.name) as contraindications,
               COLLECT(DISTINCT inter.name) as interactions,
               COLLECT(DISTINCT cat.name) as categories,
               COLLECT(DISTINCT {filename: d.filename, page: d.page}) as sources
        """
        
        results = self.kg.query(context_query, {'node_ids': initial_nodes})
        
        # Build context prioritizing important information
        context_parts = []
        
        for result in results:
            product_info = f"Producto: {result['product']}\n"
            
            if result.get('description'):
                product_info += f"Descripción: {result['description']}\n"
            
            if result.get('ingredients'):
                product_info += f"Ingredientes activos: {', '.join(result['ingredients'])}\n"
            
            if result.get('symptoms'):
                product_info += f"Indicado para: {', '.join(result['symptoms'])}\n"
            
            if result.get('contraindications'):
                product_info += f"Contraindicaciones: {', '.join(result['contraindications'])}\n"
            
            if result.get('interactions'):
                product_info += f"Interacciones: {', '.join(result['interactions'])}\n"
            
            if result.get('categories'):
                product_info += f"Categorías: {', '.join(result['categories'])}\n"
            
            if result.get('sources'):
                sources_text = ', '.join([f"{s['filename']} p.{s['page']}" for s in result['sources'][:2]])
                product_info += f"Fuentes: {sources_text}\n"
            
            context_parts.append(product_info)
        
        return "\n".join(context_parts)


def create_rag_chain(kg: Neo4jGraph, llm: ChatOllama, embeddings: HuggingFaceEmbeddings):
    """Create complete RAG chain with enhanced search"""
    
    # Initialize components
    hybrid_search = HybridGraphSearch(kg, embeddings, llm)
    context_optimizer = GraphContextOptimizer(kg)
    
    # Create response generation prompt
    response_prompt = ChatPromptTemplate.from_template("""
    Eres un asistente especializado en productos farmacéuticos y de salud.
    Usa la siguiente información para responder la pregunta del usuario.
    
    Contexto del grafo de conocimiento:
    {context}
    
    Pregunta: {question}
    
    Proporciona una respuesta completa y precisa basada en la información disponible.
    Si hay contraindicaciones o interacciones importantes, menciónalas.
    Incluye las fuentes de información cuando sea relevante.
    
    Respuesta:
    """)
    
    def process_query(question: str) -> str:
        """Process a query through the complete pipeline"""
        
        # 1. Search for relevant information
        search_results = hybrid_search.search(question, k=5)
        
        if not search_results:
            return "No encontré información relevante para tu consulta."
        
        # 2. Extract product names for context
        product_names = [r.content for r in search_results[:3]]
        
        # 3. Get optimized context
        context = context_optimizer.get_optimized_context(question, product_names)
        
        # 4. Generate response
        response = llm.invoke(
            response_prompt.format(context=context, question=question)
        )
        
        # 5. Add source citations
        sources = set()
        for result in search_results[:3]:
            if result.source != "Unknown":
                sources.add(result.source)
        
        if sources:
            response += f"\n\nFuentes consultadas: {', '.join(sources)}"
        
        return response
    
    return process_query


# Main execution
if __name__ == "__main__":
    print("Initializing Enhanced RAG Query System...")
    
    # Load environment variables
    NEO4J_URI = os.environ["NEO4J_URI"]
    NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
    NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
    
    # Initialize components
    print("Connecting to Neo4j...")
    kg = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
    )
    
    print("Initializing LLM...")
    llm = ChatOllama(model="qwen2.5:7b-instruct", temperature=0)
    
    print("Initializing embeddings...")
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="cambridgeltl/SapBERT-from-PubMedBERT-fulltext",
            model_kwargs={'device': 'cpu'}
        )
    except:
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
    
    # Create RAG chain
    rag_chain = create_rag_chain(kg, llm, embeddings)
    
    # Example queries
    print("\n" + "="*50)
    print("SISTEMA RAG MEJORADO LISTO")
    print("="*50)
    
    example_queries = [
        "¿Qué productos puedo tomar para el dolor de cabeza?",
        "¿Puedo tomar ibuprofeno y paracetamol juntos?",
        "¿Qué alternativas hay al diclofenaco?",
        "¿Cuáles son las contraindicaciones del naproxeno?",
        "Busca productos para la inflamación muscular"
    ]
    
    print("\nEjemplos de consultas disponibles:")
    for i, query in enumerate(example_queries, 1):
        print(f"{i}. {query}")
    
    print("\n" + "="*50)
    print("Sistema listo para consultas interactivas")
    print("Escribe 'salir' para terminar")
    print("="*50)
    
    # Interactive loop
    while True:
        user_query = input("\nTu consulta: ").strip()
        
        if user_query.lower() in ['salir', 'exit', 'quit']:
            print("¡Hasta luego!")
            break
        
        if not user_query:
            continue
        
        print("\nProcesando consulta...")
        response = rag_chain(user_query)
        print("\nRespuesta:")
        print(response)