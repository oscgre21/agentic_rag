from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document

class HealthProductSchema:
    """Schema definitions for health product knowledge graph"""
    
    # Node types for health products
    NODE_LABELS = {
        "Product": "Producto de salud o medicamento",
        "ActiveIngredient": "Ingrediente activo o principio activo",
        "Manufacturer": "Fabricante o laboratorio",
        "Disease": "Enfermedad o condición médica",
        "Symptom": "Síntoma o manifestación clínica",
        "Dosage": "Dosis y forma de administración",
        "SideEffect": "Efecto secundario o reacción adversa",
        "Contraindication": "Contraindicación",
        "Interaction": "Interacción con otros medicamentos",
        "Presentation": "Presentación del producto (tabletas, jarabe, etc.)",
        "TherapeuticClass": "Clase terapéutica o categoría"
    }
    
    # Relationship types
    RELATIONSHIP_TYPES = {
        "CONTAINS": "Producto contiene ingrediente",
        "MANUFACTURED_BY": "Producto fabricado por empresa",
        "TREATS": "Producto trata enfermedad",
        "RELIEVES": "Producto alivia síntoma",
        "HAS_DOSAGE": "Producto tiene dosis específica",
        "MAY_CAUSE": "Producto puede causar efecto secundario",
        "CONTRAINDICATED_FOR": "Producto contraindicado para condición",
        "INTERACTS_WITH": "Producto interactúa con otro",
        "AVAILABLE_AS": "Producto disponible en presentación",
        "BELONGS_TO": "Producto pertenece a clase terapéutica"
    }

    @staticmethod
    def get_extraction_prompt():
        """Prompt específico para extraer información de productos de salud"""
        return """
        Extrae la siguiente información de productos de salud del texto:
        
        1. Productos/Medicamentos: nombre comercial, nombre genérico
        2. Ingredientes activos: principios activos y concentración
        3. Fabricantes: laboratorio o empresa farmacéutica
        4. Indicaciones: enfermedades o condiciones que trata
        5. Síntomas: manifestaciones que alivia
        6. Dosis: cantidad y frecuencia de administración
        7. Efectos secundarios: reacciones adversas posibles
        8. Contraindicaciones: situaciones donde no debe usarse
        9. Interacciones: con otros medicamentos o alimentos
        10. Presentaciones: formas farmacéuticas disponibles
        11. Clase terapéutica: categoría del medicamento
        
        Crea relaciones claras entre estas entidades.
        Incluye propiedades relevantes como concentración, frecuencia, gravedad, etc.
        """

class HealthProductGraphTransformer(LLMGraphTransformer):
    """Custom transformer for health product documents"""
    
    def __init__(self, llm):
        # Create custom prompt for health products
        prompt = ChatPromptTemplate.from_template(
            HealthProductSchema.get_extraction_prompt() + 
            "\n\nTexto a procesar:\n{input_text}"
        )
        
        super().__init__(
            llm=llm,
            prompt=prompt,
            allowed_nodes=list(HealthProductSchema.NODE_LABELS.keys()),
            allowed_relationships=list(HealthProductSchema.RELATIONSHIP_TYPES.keys())
        )
    
    def process_health_documents(self, documents: List[Document]) -> List:
        """Process documents with health product specific logic"""
        graph_documents = []
        
        for doc in documents:
            # Extract with health-specific prompt
            graph_doc = self.convert_to_graph_documents([doc])[0]
            
            # Enrich with domain-specific properties
            for node in graph_doc.nodes:
                # Add domain-specific properties based on node type
                if node.type == "Product":
                    node.properties = node.properties or {}
                    node.properties["domain"] = "health"
                    node.properties["regulated"] = True
                    
                elif node.type == "ActiveIngredient":
                    node.properties = node.properties or {}
                    # Normalize concentration units if present
                    if "concentration" in node.properties:
                        node.properties["concentration_normalized"] = \
                            self._normalize_concentration(node.properties["concentration"])
                
                elif node.type == "Disease":
                    node.properties = node.properties or {}
                    node.properties["icd_code"] = None  # Placeholder for ICD codes
            
            graph_documents.append(graph_doc)
        
        return graph_documents
    
    def _normalize_concentration(self, concentration: str) -> dict:
        """Normalize concentration values to standard units"""
        # Simple example - expand based on your needs
        import re
        
        patterns = {
            "mg": r"(\d+(?:\.\d+)?)\s*mg",
            "g": r"(\d+(?:\.\d+)?)\s*g",
            "ml": r"(\d+(?:\.\d+)?)\s*ml",
            "percentage": r"(\d+(?:\.\d+)?)\s*%"
        }
        
        for unit, pattern in patterns.items():
            match = re.search(pattern, concentration.lower())
            if match:
                return {
                    "value": float(match.group(1)),
                    "unit": unit,
                    "original": concentration
                }
        
        return {"original": concentration}

# Cypher queries específicas para productos de salud
HEALTH_QUERIES = {
    "find_by_symptom": """
    MATCH (s:Symptom {name: $symptom})<-[:RELIEVES]-(p:Product)
    OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
    OPTIONAL MATCH (p)-[:MANUFACTURED_BY]->(m:Manufacturer)
    RETURN p.name as producto, 
           collect(DISTINCT i.name) as ingredientes,
           m.name as fabricante,
           p.source_filename as documento,
           p.source_page as pagina
    """,
    
    "find_interactions": """
    MATCH (p1:Product {name: $product1})-[:INTERACTS_WITH]->(p2:Product)
    RETURN p2.name as interactua_con, 
           p2.source_filename as documento
    """,
    
    "find_by_active_ingredient": """
    MATCH (i:ActiveIngredient {name: $ingredient})<-[:CONTAINS]-(p:Product)
    OPTIONAL MATCH (p)-[:TREATS]->(d:Disease)
    RETURN p.name as producto, 
           collect(DISTINCT d.name) as trata_enfermedades,
           p.source_filename as documento
    """,
    
    "product_full_info": """
    MATCH (p:Product {name: $product_name})
    OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
    OPTIONAL MATCH (p)-[:TREATS]->(d:Disease)
    OPTIONAL MATCH (p)-[:MAY_CAUSE]->(se:SideEffect)
    OPTIONAL MATCH (p)-[:CONTRAINDICATED_FOR]->(c:Contraindication)
    OPTIONAL MATCH (p)-[:HAS_DOSAGE]->(dos:Dosage)
    OPTIONAL MATCH (p)-[:AVAILABLE_AS]->(pres:Presentation)
    RETURN p as producto,
           collect(DISTINCT i) as ingredientes,
           collect(DISTINCT d) as enfermedades,
           collect(DISTINCT se) as efectos_secundarios,
           collect(DISTINCT c) as contraindicaciones,
           collect(DISTINCT dos) as dosis,
           collect(DISTINCT pres) as presentaciones,
           p.source_filename as documento_fuente
    """
}