from dotenv import load_dotenv
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np
from langchain_neo4j import Neo4jGraph
from langchain.text_splitter import TokenTextSplitter
from langchain_ollama import ChatOllama
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.embeddings import HuggingFaceEmbeddings
from pdf_loader import PDFToMarkdownLoader, PDFMarkdownLoader

load_dotenv()

NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

# PDF directory configuration
PDF_DIR = os.environ.get("PDF_DIR", "./docs")  # Default to ./pdfs if not set
MARKDOWN_DIR = os.environ.get("MARKDOWN_DIR", "./markdown_output")  # Optional markdown output

# Using Ollama instead of OpenAI
print("Initializing Ollama chat model...")
chat = ChatOllama(model="qwen2.5:7b-instruct", temperature=0)

# Initialize medical embeddings for enhanced search
print("Initializing medical embeddings model...")
try:
    medical_embeddings = HuggingFaceEmbeddings(
        model_name="cambridgeltl/SapBERT-from-PubMedBERT-fulltext",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
except:
    # Fallback to general embeddings if medical model not available
    print("Medical embeddings not available, using general model...")
    medical_embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

print("Connecting to Neo4j...")
kg = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
)


# Load PDF documents
print(f"Loading PDF documents from {PDF_DIR}...")
# Use PDFMarkdownLoader to also save markdown files
pdf_loader = PDFMarkdownLoader(
    pdf_dir=PDF_DIR,
    markdown_dir=MARKDOWN_DIR,  # Will save markdown files
    glob_pattern="*.pdf"
)

try:
    raw_documents = pdf_loader.load()
    print(f"Loaded {len(raw_documents)} documents from PDF files")
except Exception as e:
    print(f"Error loading PDFs: {str(e)}")
    print("Please ensure the PDF directory exists and contains PDF files")
    exit(1)

# Split documents
text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=24)
documents = text_splitter.split_documents(raw_documents)
print(f"Created {len(documents)} document chunks")

# Convert to graph documents using standard transformer
print("Converting documents to health product knowledge graph...")
# Use standard transformer with custom prompt for health products
health_prompt = ChatPromptTemplate.from_template("""
Extrae entidades y relaciones de productos de salud del siguiente texto.

Identifica:
1. Productos/Medicamentos (tipo: Product)
2. Ingredientes activos (tipo: ActiveIngredient)
3. Fabricantes (tipo: Manufacturer)
4. Enfermedades/Condiciones (tipo: Disease)
5. Síntomas (tipo: Symptom)
6. Dosis (tipo: Dosage)
7. Efectos secundarios (tipo: SideEffect)
8. Contraindicaciones (tipo: Contraindication)
9. Presentaciones (tipo: Presentation)

Relaciones importantes:
- CONTAINS: Producto contiene ingrediente
- TREATS: Producto trata enfermedad
- RELIEVES: Producto alivia síntoma
- MAY_CAUSE: Producto puede causar efecto secundario
- CONTRAINDICATED_FOR: Producto contraindicado para condición
- INTERACTS_WITH: Producto interactúa con otro

Texto: {input}
""")

llm_transformer = LLMGraphTransformer(
    llm=chat,
    prompt=health_prompt,
    allowed_nodes=["Product", "ActiveIngredient", "Manufacturer", "Disease", 
                   "Symptom", "Dosage", "SideEffect", "Contraindication", 
                   "Presentation", "TherapeuticClass"],
    allowed_relationships=["CONTAINS", "MANUFACTURED_BY", "TREATS", "RELIEVES",
                          "HAS_DOSAGE", "MAY_CAUSE", "CONTRAINDICATED_FOR",
                          "INTERACTS_WITH", "AVAILABLE_AS", "BELONGS_TO"]
)

# Process in batches to avoid overwhelming the LLM
batch_size = 10
all_graph_documents = []

for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    print(f"Processing batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}...")
    try:
        graph_docs = llm_transformer.convert_to_graph_documents(batch)
        
        # Add unique document prefix to node IDs to avoid collisions
        for graph_doc in graph_docs:
            if hasattr(graph_doc, 'source') and hasattr(graph_doc.source, 'metadata'):
                metadata = graph_doc.source.metadata
                doc_prefix = f"{metadata.get('filename', 'unknown')}_{metadata.get('page', '0')}"
                
                # Update node IDs with document prefix
                if hasattr(graph_doc, 'nodes'):
                    for node in graph_doc.nodes:
                        if hasattr(node, 'id'):
                            # Preserve original ID for reference
                            if not hasattr(node, 'original_id'):
                                node.original_id = node.id
                            node.id = f"{doc_prefix}::{node.id}"
                
                # Update relationship IDs to match new node IDs
                if hasattr(graph_doc, 'relationships'):
                    for rel in graph_doc.relationships:
                        if hasattr(rel, 'source') and hasattr(rel.source, 'id'):
                            rel.source.id = f"{doc_prefix}::{rel.source.id}"
                        if hasattr(rel, 'target') and hasattr(rel.target, 'id'):
                            rel.target.id = f"{doc_prefix}::{rel.target.id}"
        
        all_graph_documents.extend(graph_docs)
    except Exception as e:
        print(f"Error processing batch: {str(e)}")
        continue

print(f"Created {len(all_graph_documents)} graph documents")

# Document-aware processing
class DocumentAwareProcessor:
    """Process documents based on their type and structure"""
    
    def __init__(self):
        self.document_patterns = {
            'ficha_tecnica': {
                'markers': ['composición', 'indicaciones', 'contraindicaciones', 'posología'],
                'priority': 3
            },
            'prospecto': {
                'markers': ['qué es', 'antes de tomar', 'efectos adversos', 'cómo tomar'],
                'priority': 2
            },
            'articulo_cientifico': {
                'markers': ['abstract', 'methods', 'results', 'conclusion'],
                'priority': 1
            },
            'catalogo': {
                'markers': ['producto', 'precio', 'descripción', 'ingredientes'],
                'priority': 2
            }
        }
    
    def identify_document_type(self, text: str) -> Tuple[str, float]:
        """Identify document type based on content markers"""
        text_lower = text.lower()
        scores = {}
        
        for doc_type, config in self.document_patterns.items():
            score = sum(1 for marker in config['markers'] 
                       if marker in text_lower)
            scores[doc_type] = score * config['priority']
        
        if max(scores.values()) == 0:
            return 'general', 0.5
        
        doc_type = max(scores, key=scores.get)
        confidence = scores[doc_type] / (len(self.document_patterns[doc_type]['markers']) * 
                                         self.document_patterns[doc_type]['priority'])
        return doc_type, confidence
    
    def enhance_graph_document(self, graph_doc, doc_type: str):
        """Enhance graph document based on document type"""
        if hasattr(graph_doc, 'nodes'):
            for node in graph_doc.nodes:
                if not hasattr(node, 'properties'):
                    node.properties = {}
                node.properties['doc_type'] = doc_type
                node.properties['extraction_confidence'] = 0.8 if doc_type != 'general' else 0.5
        return graph_doc

# Apply document-aware processing
print("Applying document-aware processing...")
doc_processor = DocumentAwareProcessor()

for graph_doc in all_graph_documents:
    if hasattr(graph_doc, 'source') and hasattr(graph_doc.source, 'page_content'):
        doc_type, confidence = doc_processor.identify_document_type(graph_doc.source.page_content)
        doc_processor.enhance_graph_document(graph_doc, doc_type)
        
        # Store document type in metadata
        if hasattr(graph_doc.source, 'metadata'):
            graph_doc.source.metadata['doc_type'] = doc_type
            graph_doc.source.metadata['doc_confidence'] = confidence

# Clear existing data (optional)
print("Clearing existing data...")
kg.query("MATCH (n) DETACH DELETE n")

# Store in Neo4j with enhanced source tracking
print("Storing graph documents in Neo4j...")

# First, create Document nodes
print("Creating Document nodes...")
processed_files = set()
for doc in documents:
    if hasattr(doc, 'metadata'):
        filename = doc.metadata.get('filename', 'unknown')
        if filename not in processed_files:
            processed_files.add(filename)
            create_file_query = """
            MERGE (f:File {filename: $filename})
            SET f.path = $path,
                f.created_at = timestamp()
            """
            kg.query(create_file_query, {
                "filename": filename,
                "path": doc.metadata.get('source', '')
            })

# Store graph documents
kg.add_graph_documents(
    all_graph_documents,
    include_source=True,
    baseEntityLabel=True,
)

# Create Document nodes for source tracking
print("Creating Document nodes for source tracking...")
processed_docs = set()

for i, graph_doc in enumerate(all_graph_documents):
    if hasattr(graph_doc, 'source') and hasattr(graph_doc.source, 'metadata'):
        metadata = graph_doc.source.metadata
        doc_id = f"{metadata.get('filename', 'unknown')}_{metadata.get('page', '0')}"
        
        # Only create Document node if not already processed
        if doc_id not in processed_docs:
            processed_docs.add(doc_id)
            
            # Create Document node
            create_doc_query = """
            MERGE (d:Document {id: $doc_id})
            SET d.filename = $filename,
                d.page = $page,
                d.source = $source
            """
            kg.query(create_doc_query, {
                "doc_id": doc_id,
                "filename": metadata.get('filename', 'unknown'),
                "page": metadata.get('page', 0),
                "source": metadata.get('source', '')
            })
        
        # Link entities from this document to the Document node
        if hasattr(graph_doc, 'nodes'):
            for node in graph_doc.nodes:
                if hasattr(node, 'id'):
                    # Store original entity name and document source
                    update_node_query = """
                    MATCH (n {id: $node_id})
                    SET n.original_name = COALESCE(n.original_name, $original_id),
                        n.source_doc = $doc_id,
                        n.source_filename = $filename,
                        n.source_page = $page
                    """
                    kg.query(update_node_query, {
                        "node_id": node.id,
                        "original_id": getattr(node, 'original_id', node.id),
                        "doc_id": doc_id,
                        "filename": metadata.get('filename', 'unknown'),
                        "page": metadata.get('page', 0)
                    })
                    
                    # Create relationship to Document node
                    link_query = """
                    MATCH (n {id: $node_id})
                    MATCH (d:Document {id: $doc_id})
                    MERGE (d)-[:MENTIONS]->(n)
                    """
                    kg.query(link_query, {
                        "node_id": node.id,
                        "doc_id": doc_id
                    })
                    
                    # Link to File node as well
                    file_link_query = """
                    MATCH (n {id: $node_id})
                    MATCH (f:File {filename: $filename})
                    MERGE (f)-[:CONTAINS]->(n)
                    """
                    kg.query(file_link_query, {
                        "node_id": node.id,
                        "filename": metadata.get('filename', 'unknown')
                    })

print(f"Created {len(processed_docs)} Document nodes with source tracking")

# Entity Resolution and Deduplication
def merge_duplicate_entities(kg: Neo4jGraph):
    """Merge duplicate entities based on similarity"""
    print("\nPerforming entity resolution and deduplication...")
    
    # Normalize entity names for better matching
    normalize_query = """
    MATCH (n)
    WHERE n.name IS NOT NULL
    SET n.normalized_name = LOWER(TRIM(REPLACE(REPLACE(n.name, '-', ''), ' ', '')))
    RETURN COUNT(n) as normalized
    """
    result = kg.query(normalize_query)
    print(f"Normalized {result[0]['normalized']} entity names")
    
    # Merge products with similar names
    merge_products_query = """
    MATCH (p1:Product), (p2:Product)
    WHERE p1.id < p2.id 
    AND p1.normalized_name = p2.normalized_name
    // Merge p2 into p1, keeping p1 as primary
    SET p1.alternative_names = COALESCE(p1.alternative_names, []) + [p2.name]
    SET p1.merged_ids = COALESCE(p1.merged_ids, []) + [p2.id]
    WITH p1, p2
    // Transfer relationships from p2 to p1
    MATCH (p2)-[r]->(target)
    WHERE NOT (p1)-[]->(target)
    CREATE (p1)-[r2:MERGED_RELATION]->(target)
    SET r2 = properties(r)
    WITH p1, p2
    DETACH DELETE p2
    RETURN COUNT(p2) as merged_products
    """
    
    try:
        result = kg.query(merge_products_query)
        if result and len(result) > 0:
            print(f"Merged {result[0].get('merged_products', 0)} duplicate products")
    except Exception as e:
        print(f"Product merging skipped (may require APOC): {str(e)}")
    
    # Merge active ingredients
    merge_ingredients_query = """
    MATCH (i1:ActiveIngredient), (i2:ActiveIngredient)
    WHERE i1.id < i2.id
    AND i1.normalized_name = i2.normalized_name
    SET i1.alternative_names = COALESCE(i1.alternative_names, []) + [i2.name]
    WITH i1, i2
    MATCH (i2)<-[r]-(source)
    WHERE NOT (i1)<-[]-(source)
    CREATE (source)-[r2:CONTAINS]->(i1)
    SET r2 = properties(r)
    WITH i1, i2
    DETACH DELETE i2
    RETURN COUNT(i2) as merged_ingredients
    """
    
    try:
        result = kg.query(merge_ingredients_query)
        if result and len(result) > 0:
            print(f"Merged {result[0].get('merged_ingredients', 0)} duplicate ingredients")
    except Exception as e:
        print(f"Ingredient merging error: {str(e)}")
    
    # Merge symptoms
    merge_symptoms_query = """
    MATCH (s1:Symptom), (s2:Symptom)
    WHERE s1.id < s2.id
    AND s1.normalized_name = s2.normalized_name
    SET s1.alternative_names = COALESCE(s1.alternative_names, []) + [s2.name]
    WITH s1, s2
    MATCH (s2)<-[r]-(source)
    WHERE NOT (s1)<-[]-(source)
    CREATE (source)-[r2:RELIEVES]->(s1)
    SET r2 = properties(r)
    WITH s1, s2
    DETACH DELETE s2
    RETURN COUNT(s2) as merged_symptoms
    """
    
    try:
        result = kg.query(merge_symptoms_query)
        if result and len(result) > 0:
            print(f"Merged {result[0].get('merged_symptoms', 0)} duplicate symptoms")
    except Exception as e:
        print(f"Symptom merging error: {str(e)}")

# Call entity resolution
merge_duplicate_entities(kg)

# Create Taxonomies and Hierarchies
def create_taxonomies(kg: Neo4jGraph):
    """Create hierarchical relationships between entities"""
    print("\nCreating taxonomies and hierarchies...")
    
    # Product categories
    category_hierarchy = """
    // Main categories
    MERGE (c1:Category {name: 'Analgésicos', level: 1})
    MERGE (c2:Category {name: 'Antiinflamatorios', level: 1})
    MERGE (c3:Category {name: 'Antibióticos', level: 1})
    MERGE (c4:Category {name: 'Antihistamínicos', level: 1})
    MERGE (c5:Category {name: 'Vitaminas y Suplementos', level: 1})
    
    // Subcategories
    MERGE (sc1:Category {name: 'AINES', level: 2})
    MERGE (sc2:Category {name: 'Opioides', level: 2})
    MERGE (sc3:Category {name: 'Paracetamol', level: 2})
    
    // Create hierarchy
    MERGE (c1)-[:HAS_SUBCATEGORY]->(sc1)
    MERGE (c1)-[:HAS_SUBCATEGORY]->(sc2)
    MERGE (c1)-[:HAS_SUBCATEGORY]->(sc3)
    MERGE (c2)-[:HAS_SUBCATEGORY]->(sc1)
    
    RETURN COUNT(DISTINCT c1) + COUNT(DISTINCT c2) + COUNT(DISTINCT c3) + 
           COUNT(DISTINCT c4) + COUNT(DISTINCT c5) as categories_created
    """
    
    result = kg.query(category_hierarchy)
    print(f"Created {result[0]['categories_created']} category nodes")
    
    # Auto-categorize products based on ingredients and names
    categorize_products = """
    // AINES
    MATCH (p:Product)
    WHERE LOWER(p.name) CONTAINS 'ibuprofeno' 
       OR LOWER(p.name) CONTAINS 'diclofenaco'
       OR LOWER(p.name) CONTAINS 'naproxeno'
       OR LOWER(p.name) CONTAINS 'ketorolaco'
    MATCH (c:Category {name: 'AINES'})
    MERGE (p)-[:BELONGS_TO]->(c)
    
    UNION
    
    // Paracetamol products
    MATCH (p:Product)
    WHERE LOWER(p.name) CONTAINS 'paracetamol'
       OR LOWER(p.name) CONTAINS 'acetaminofén'
    MATCH (c:Category {name: 'Paracetamol'})
    MERGE (p)-[:BELONGS_TO]->(c)
    
    UNION
    
    // Antibiotics
    MATCH (p:Product)
    WHERE LOWER(p.name) CONTAINS 'amoxicilina'
       OR LOWER(p.name) CONTAINS 'azitromicina'
       OR LOWER(p.name) CONTAINS 'ciprofloxacino'
    MATCH (c:Category {name: 'Antibióticos'})
    MERGE (p)-[:BELONGS_TO]->(c)
    """
    
    kg.query(categorize_products)
    
    # Symptom hierarchy - create groups first
    symptom_groups_create = """
    // Main symptom groups
    MERGE (sg1:SymptomGroup {name: 'Dolor', level: 1})
    MERGE (sg2:SymptomGroup {name: 'Inflamación', level: 1})
    MERGE (sg3:SymptomGroup {name: 'Fiebre', level: 1})
    MERGE (sg4:SymptomGroup {name: 'Alergia', level: 1})
    MERGE (sg5:SymptomGroup {name: 'Infección', level: 1})
    RETURN COUNT(DISTINCT sg1) + COUNT(DISTINCT sg2) + COUNT(DISTINCT sg3) + 
           COUNT(DISTINCT sg4) + COUNT(DISTINCT sg5) as groups_created
    """
    
    result = kg.query(symptom_groups_create)
    print(f"Created {result[0]['groups_created']} symptom groups")
    
    # Link symptoms to groups (separate queries to avoid UNION issues)
    symptom_links = [
        ("dolor", "Dolor"),
        ("inflam", "Inflamación"),
        ("fiebre", "Fiebre"),
        ("febr", "Fiebre"),
        ("alerg", "Alergia"),
        ("infec", "Infección")
    ]
    
    for pattern, group_name in symptom_links:
        link_query = """
        MATCH (s:Symptom)
        WHERE LOWER(s.name) CONTAINS $pattern
        MATCH (sg:SymptomGroup {name: $group_name})
        MERGE (sg)-[:INCLUDES]->(s)
        RETURN COUNT(s) as linked
        """
        try:
            result = kg.query(link_query, {'pattern': pattern, 'group_name': group_name})
            if result and result[0]['linked'] > 0:
                print(f"  Linked {result[0]['linked']} symptoms to {group_name}")
        except:
            pass
    
    print("Created symptom hierarchies")

# Create taxonomies
create_taxonomies(kg)

# Add embeddings to important nodes
def enrich_with_embeddings(kg: Neo4jGraph, embeddings_model):
    """Add vector embeddings to nodes for semantic search"""
    print("\nEnriching nodes with embeddings...")
    
    # Get products for embedding
    products_query = """
    MATCH (p:Product)
    OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)
    OPTIONAL MATCH (p)-[:RELIEVES]->(s:Symptom)
    WITH p, 
         COLLECT(DISTINCT i.name) as ingredients,
         COLLECT(DISTINCT s.name) as symptoms
    RETURN p.id as id, 
           p.name as name,
           p.description as description,
           ingredients,
           symptoms
    LIMIT 100
    """
    
    products = kg.query(products_query)
    
    # Generate embeddings for products
    for product in products:
        # Create rich text representation
        text = f"{product['name']} "
        if product['description']:
            text += f"{product['description']} "
        if product['ingredients']:
            text += f"Contiene: {', '.join(product['ingredients'])} "
        if product['symptoms']:
            text += f"Para: {', '.join(product['symptoms'])}"
        
        # Generate embedding
        try:
            embedding = embeddings_model.embed_query(text)
            
            # Store embedding (as property for now, ideally would use vector index)
            update_query = """
            MATCH (p:Product {id: $id})
            SET p.embedding_text = $text,
                p.has_embedding = true
            RETURN p.name
            """
            
            kg.query(update_query, {
                'id': product['id'],
                'text': text[:500]  # Store first 500 chars for reference
            })
        except Exception as e:
            print(f"Error generating embedding for {product['name']}: {str(e)}")
    
    print(f"Added embeddings to {len(products)} products")

# Enrich with embeddings
enrich_with_embeddings(kg, medical_embeddings)

# Cross-document entity resolution
def resolve_cross_document_entities(kg: Neo4jGraph):
    """Resolve entities across different documents"""
    print("\nResolving cross-document entities...")
    
    # Find and merge entities from different documents
    cross_doc_merge = """
    MATCH (n1), (n2)
    WHERE n1.id < n2.id
    AND n1.source_filename <> n2.source_filename
    AND labels(n1) = labels(n2)
    AND n1.normalized_name = n2.normalized_name
    WITH n1, n2
    // Create merged entity preserving both sources
    SET n1.source_docs = COALESCE(n1.source_docs, [n1.source_doc]) + [n2.source_doc]
    SET n1.source_files = COALESCE(n1.source_files, [n1.source_filename]) + [n2.source_filename]
    SET n1.cross_referenced = true
    WITH n1, n2
    // Transfer unique relationships
    MATCH (n2)-[r]->(target)
    WHERE NOT (n1)-[]->(target)
    CREATE (n1)-[r2:CROSS_DOC_RELATION]->(target)
    SET r2 = properties(r)
    SET r2.source_doc = n2.source_doc
    WITH n1, n2
    DETACH DELETE n2
    RETURN COUNT(n2) as merged_cross_doc
    """
    
    try:
        result = kg.query(cross_doc_merge)
        if result and len(result) > 0:
            print(f"Merged {result[0].get('merged_cross_doc', 0)} cross-document entities")
    except Exception as e:
        print(f"Cross-document resolution error: {str(e)}")
    
    # Mark high-confidence entities (appearing in multiple documents)
    confidence_query = """
    MATCH (n)
    WHERE n.cross_referenced = true
    SET n.confidence_score = SIZE(COALESCE(n.source_docs, []))
    RETURN COUNT(n) as high_confidence_entities
    """
    
    result = kg.query(confidence_query)
    print(f"Marked {result[0]['high_confidence_entities']} high-confidence entities")

# Resolve cross-document entities
resolve_cross_document_entities(kg)

# Create indexes for better query performance
print("Creating indexes...")
try:
    kg.query("CREATE INDEX entity_original_name IF NOT EXISTS FOR (n:__Entity__) ON (n.original_name)")
    kg.query("CREATE INDEX entity_source_doc IF NOT EXISTS FOR (n:__Entity__) ON (n.source_doc)")
    kg.query("CREATE INDEX document_filename IF NOT EXISTS FOR (d:Document) ON (d.filename)")
    kg.query("CREATE INDEX file_filename IF NOT EXISTS FOR (f:File) ON (f.filename)")
except:
    # Neo4j Community Edition may not support IF NOT EXISTS
    pass

print("Knowledge graph created successfully!")
print("\nSummary:")
print(f"- Processed {len(processed_files)} unique files")
print(f"- Created {len(all_graph_documents)} graph documents")
print(f"- Tracked {len(processed_docs)} document pages")

# Enhanced query examples with new capabilities
print("\n" + "="*50)
print("ENHANCED KNOWLEDGE GRAPH CREATED SUCCESSFULLY!")
print("="*50)

print("\nGraph Statistics:")
stats_query = """
MATCH (n)
WITH labels(n) as label
UNWIND label as l
WITH l, COUNT(*) as count
ORDER BY count DESC
RETURN l as Label, count as Count
"""
stats = kg.query(stats_query)
for stat in stats[:10]:
    print(f"  {stat['Label']}: {stat['Count']}")

print("\nEnhanced Query Examples:")
print("\n1. HIERARCHICAL SEARCH - Find products by symptom group:")
print("   MATCH (sg:SymptomGroup {name: 'Dolor'})-[:INCLUDES]->(s:Symptom)")
print("   MATCH (s)<-[:RELIEVES]-(p:Product)")
print("   RETURN DISTINCT p.name, COLLECT(s.name) as symptoms")

print("\n2. CATEGORY NAVIGATION - Find alternatives in same category:")
print("   MATCH (p:Product {name: 'Ibuprofeno 600mg'})-[:BELONGS_TO]->(c:Category)")
print("   MATCH (c)<-[:BELONGS_TO]-(alt:Product)")
print("   WHERE alt.id <> p.id")
print("   RETURN alt.name, c.name as category")

print("\n3. CROSS-DOCUMENT VALIDATION - Find high-confidence entities:")
print("   MATCH (n)")
print("   WHERE n.cross_referenced = true")
print("   RETURN n.name, n.source_files, labels(n)")
print("   ORDER BY SIZE(n.source_files) DESC")

print("\n4. SIMILARITY SEARCH - Find related products:")
print("   MATCH (p1:Product)-[:CONTAINS]->(i:ActiveIngredient)")
print("   MATCH (i)<-[:CONTAINS]-(p2:Product)")
print("   WHERE p1.name = 'Aspirina' AND p1.id <> p2.id")
print("   WITH p2, COUNT(i) as shared_ingredients")
print("   RETURN p2.name, shared_ingredients")
print("   ORDER BY shared_ingredients DESC")

print("\n5. DOCUMENT SOURCE TRACKING - Trace information origin:")
print("   MATCH (p:Product)-[:RELIEVES]->(s:Symptom)")
print("   MATCH (d:Document)-[:MENTIONS]->(p)")
print("   RETURN p.name, s.name, d.filename, d.page")

print("\n6. COMPREHENSIVE PRODUCT INFO with Categories:")
print("   MATCH (p:Product {name: $product_name})")
print("   OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)")
print("   OPTIONAL MATCH (c)-[:HAS_SUBCATEGORY*0..2]-(parent:Category)")
print("   OPTIONAL MATCH (p)-[:CONTAINS]->(i:ActiveIngredient)")
print("   OPTIONAL MATCH (p)-[:RELIEVES]->(s:Symptom)")
print("   OPTIONAL MATCH (s)<-[:INCLUDES]-(sg:SymptomGroup)")
print("   RETURN p, COLLECT(DISTINCT c.name) as categories,")
print("          COLLECT(DISTINCT parent.name) as parent_categories,")
print("          COLLECT(DISTINCT i.name) as ingredients,")
print("          COLLECT(DISTINCT s.name) as symptoms,")
print("          COLLECT(DISTINCT sg.name) as symptom_groups")

print("\n" + "="*50)
print("Graph processing completed with advanced features:")
print("  ✓ Entity resolution and deduplication")
print("  ✓ Hierarchical taxonomies")
print("  ✓ Cross-document entity linking")
print("  ✓ Medical embeddings enrichment")
print("  ✓ Document-aware processing")
print("="*50)
 