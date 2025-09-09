from dotenv import load_dotenv
import os
from langchain_neo4j import Neo4jGraph
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import GraphCypherQAChain
from health_product_schema import HEALTH_QUERIES

load_dotenv()

# Neo4j connection
kg = Neo4jGraph(
    url=os.environ["NEO4J_URI"],
    username=os.environ["NEO4J_USERNAME"],
    password=os.environ["NEO4J_PASSWORD"],
)

# LLM for query generation
llm = ChatOllama(model="qwen2.5:7b-instruct", temperature=0)

class HealthProductQueryEngine:
    """Query engine específico para productos de salud"""
    
    def __init__(self, graph: Neo4jGraph, llm):
        self.graph = graph
        self.llm = llm
        
        # Prompt específico para generar queries de productos de salud
        self.cypher_prompt = ChatPromptTemplate.from_template("""
        Eres un experto en bases de datos de grafos para productos de salud.
        El grafo contiene los siguientes tipos de nodos:
        - Product: Productos farmacéuticos o de salud
        - ActiveIngredient: Ingredientes activos
        - Disease: Enfermedades que tratan
        - Symptom: Síntomas que alivian
        - SideEffect: Efectos secundarios
        - Manufacturer: Fabricantes
        - Dosage: Información de dosis
        - Contraindication: Contraindicaciones
        
        Y las siguientes relaciones:
        - CONTAINS: producto contiene ingrediente
        - TREATS: producto trata enfermedad
        - RELIEVES: producto alivia síntoma
        - MAY_CAUSE: producto puede causar efecto
        - MANUFACTURED_BY: producto fabricado por
        - CONTRAINDICATED_FOR: contraindicaciones
        
        IMPORTANTE: Cada nodo tiene propiedades source_filename y source_page que indican de qué documento proviene.
        
        Genera una consulta Cypher para responder: {question}
        
        Siempre incluye la fuente del documento en el RETURN.
        """)
        
        # Chain para generar Cypher
        self.cypher_chain = (
            self.cypher_prompt 
            | self.llm 
            | StrOutputParser()
        )
        
        # Chain completo Q&A
        self.qa_chain = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            cypher_prompt=self.cypher_prompt,
            verbose=True,
            return_intermediate_steps=True
        )
    
    def query_by_symptom(self, symptom: str):
        """Buscar productos por síntoma"""
        result = self.graph.query(
            HEALTH_QUERIES["find_by_symptom"],
            {"symptom": symptom}
        )
        return self._format_results(result, f"Productos que alivian '{symptom}':")
    
    def query_by_ingredient(self, ingredient: str):
        """Buscar productos por ingrediente activo"""
        result = self.graph.query(
            HEALTH_QUERIES["find_by_active_ingredient"],
            {"ingredient": ingredient}
        )
        return self._format_results(result, f"Productos con '{ingredient}':")
    
    def check_interactions(self, product_name: str):
        """Verificar interacciones de un producto"""
        result = self.graph.query(
            HEALTH_QUERIES["find_interactions"],
            {"product1": product_name}
        )
        return self._format_results(result, f"Interacciones de '{product_name}':")
    
    def get_product_info(self, product_name: str):
        """Obtener información completa de un producto"""
        result = self.graph.query(
            HEALTH_QUERIES["product_full_info"],
            {"product_name": product_name}
        )
        
        if not result:
            return f"No se encontró información para '{product_name}'"
        
        info = result[0]
        output = f"\n=== Información de {product_name} ===\n"
        output += f"Fuente: {info.get('documento_fuente', 'No especificada')}\n\n"
        
        if info.get('ingredientes'):
            output += "Ingredientes activos:\n"
            for ing in info['ingredientes']:
                output += f"  - {ing.get('name', 'Sin nombre')}\n"
        
        if info.get('enfermedades'):
            output += "\nTrata:\n"
            for enf in info['enfermedades']:
                output += f"  - {enf.get('name', 'Sin nombre')}\n"
        
        if info.get('efectos_secundarios'):
            output += "\nEfectos secundarios:\n"
            for ef in info['efectos_secundarios']:
                output += f"  - {ef.get('name', 'Sin nombre')}\n"
        
        return output
    
    def natural_query(self, question: str):
        """Consulta en lenguaje natural"""
        try:
            result = self.qa_chain.invoke({"query": question})
            
            # Extraer información de la respuesta
            answer = result.get('result', 'No se pudo procesar la consulta')
            
            # Incluir consulta Cypher generada si está disponible
            if 'intermediate_steps' in result:
                cypher_query = result['intermediate_steps'][0].get('query', '')
                if cypher_query:
                    answer += f"\n\n[Consulta generada: {cypher_query}]"
            
            return answer
        except Exception as e:
            return f"Error al procesar consulta: {str(e)}"
    
    def _format_results(self, results, header):
        """Formatear resultados de consulta"""
        if not results:
            return f"{header}\nNo se encontraron resultados."
        
        output = f"\n{header}\n"
        for i, r in enumerate(results, 1):
            output += f"\n{i}. {r.get('producto', 'Sin nombre')}"
            if r.get('fabricante'):
                output += f" - Fabricante: {r['fabricante']}"
            if r.get('ingredientes'):
                output += f"\n   Ingredientes: {', '.join(r['ingredientes'])}"
            if r.get('documento'):
                output += f"\n   Fuente: {r['documento']}"
                if r.get('pagina'):
                    output += f" (página {r['pagina']})"
            output += "\n"
        
        return output

# Función de utilidad para consultas rápidas
def query_health_products(question: str):
    """Función rápida para consultar productos de salud"""
    engine = HealthProductQueryEngine(kg, llm)
    return engine.natural_query(question)

if __name__ == "__main__":
    # Ejemplo de uso
    engine = HealthProductQueryEngine(kg, llm)
    
    print("=== Sistema de Consulta de Productos de Salud ===\n")
    
    # Ejemplos de consultas
    examples = [
        "¿Qué productos contienen paracetamol?",
        "¿Qué medicamentos tratan la hipertensión?",
        "¿Cuáles son los efectos secundarios del ibuprofeno?",
        "¿Qué productos alivian el dolor de cabeza?"
    ]
    
    print("Ejemplos de consultas:")
    for i, ex in enumerate(examples, 1):
        print(f"{i}. {ex}")
    
    print("\nIngrese 'salir' para terminar.\n")
    
    while True:
        question = input("\nPregunta: ").strip()
        if question.lower() == 'salir':
            break
        
        if not question:
            continue
        
        # Procesar consulta
        response = engine.natural_query(question)
        print(response)