from dotenv import load_dotenv
import os
from langchain_neo4j import Neo4jGraph
from langchain_community.document_loaders import WikipediaLoader
from langchain.text_splitter import TokenTextSplitter
from langchain_ollama import ChatOllama
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pdf_loader import PDFToMarkdownLoader, PDFMarkdownLoader

load_dotenv()

NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

# Using Ollama instead of OpenAI
print("Initializing Ollama chat model...")
#chat = ChatOllama(model="qwen2.5:7b-instruct", temperature=0)
chat = ChatOllama(model="qwen3:4b", temperature=0)

print("Connecting to Neo4j...")
kg = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
)

# Clear existing data (optional)
# print("Clearing existing data...")
# kg.query("MATCH (n) DETACH DELETE n")

# # Configuration for document source
# USE_PDF = os.environ.get("USE_PDF", "false").lower() == "true"
# PDF_DIR = os.environ.get("PDF_DIR", "./pdfs")
# MARKDOWN_DIR = os.environ.get("MARKDOWN_DIR", "./markdown_output")

# if USE_PDF:
#     # Load PDF documents
#     print(f"Loading PDF documents from {PDF_DIR}...")
#     pdf_loader = PDFMarkdownLoader(
#         pdf_dir=PDF_DIR,
#         markdown_dir=MARKDOWN_DIR,
#         glob_pattern="*.pdf"
#     )
#     try:
#         raw_documents = pdf_loader.load()
#         print(f"Loaded {len(raw_documents)} documents from PDF files")
#     except Exception as e:
#         print(f"Error loading PDFs: {str(e)}")
#         print("Falling back to Wikipedia data...")
#         raw_documents = WikipediaLoader(query="Roman Empire").load()
# else:
#     # Load Wikipedia data
#     print("Loading Wikipedia data about the Roman Empire...")
#     raw_documents = WikipediaLoader(query="Roman Empire").load()

# # Split documents
# text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=24)
# documents = text_splitter.split_documents(raw_documents[:3])
# print(f"Created {len(documents)} document chunks")

# # Convert to graph documents
# print("Converting documents to knowledge graph...")
# llm_transformer = LLMGraphTransformer(llm=chat)
# graph_documents = llm_transformer.convert_to_graph_documents(documents)

# # Store in Neo4j
# print("Storing graph documents in Neo4j...")
# kg.add_graph_documents(
#     graph_documents,
#     include_source=True,
#     baseEntityLabel=True,
# )

# print("Knowledge graph created successfully!")

# Simple Q&A function
def answer_question(question: str):
    # Extract key terms from the question for better search
    import re
    # Extract numbers and important keywords
    key_terms = []
    # Look for numbers
    numbers = re.findall(r'\b\d[\d,]*\b', question)
    key_terms.extend(numbers)
    # Add specific important terms
    important_words = ['límite', 'cobertura', 'anual', 'máximo', 'millones', '3000000', '3,000,000', 
                      'deducible', 'beneficio', 'red', 'proveedores', 'cobertura', 'trasplante', 
                      'autismo', 'congénito', 'hospitalización', 'ambulatorio']
    key_terms.extend([word for word in important_words if word.lower() in question.lower()])
    
    # More flexible query to find relevant information
    cypher_query = """
    // Search for nodes containing any of the key terms
    MATCH (n)
    WHERE any(term IN $key_terms WHERE 
        any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS toLower(term))
    )
    OR any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS 'cobertura')
    OR any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS 'límite')
    WITH n
    LIMIT 30
    
    // Get relationships and connected documents
    OPTIONAL MATCH (n)-[r]-(m)
    OPTIONAL MATCH (doc:Document)-[:MENTIONS]->(n)
    RETURN n, 
           collect(DISTINCT {rel: type(r), node: m}) as relationships,
           collect(DISTINCT doc) as documents
    """
    
    results = kg.query(cypher_query, {"question": question, "key_terms": key_terms})
    
    # Format the results and collect source information
    context = "Based on the knowledge graph:\n"
    sources = set()  # To track unique sources
    
    for result in results:
        if result.get('n'):
            node = result['n']
            context += f"\n- {node.get('id', node.get('name', 'Unknown'))}: {dict(node)}"
            
            # Add source information if available
            if result.get('documents'):
                for doc in result['documents']:
                    if doc and isinstance(doc, dict):
                        filename = doc.get('filename', 'Unknown file')
                        page = doc.get('page', 'Unknown page')
                        sources.add((filename, page))
            
            # Process relationships
            if result.get('relationships'):
                for rel_info in result['relationships']:
                    if rel_info and rel_info.get('node'):
                        rel_type = rel_info.get('rel', 'RELATED')
                        other_node = rel_info['node']
                        context += f"\n  -> {rel_type}: {other_node.get('id', other_node.get('name', 'Unknown'))}"
    
    # Use LLM to generate answer
    template = """Answer the question based only on the following context:
{context}

Question: {question}
Use natural language and be concise.
Answer:"""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | chat | StrOutputParser()
    
    answer = chain.invoke({"context": context, "question": question})
    
    # Remove <think></think> tags and their content
    import re
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
    # Clean up any extra whitespace left after removing tags
    answer = answer.strip()
    
    # Add source information to the answer
    if sources:
        answer += "\n\n📄 Fuentes:"
        for filename, page in sorted(sources):
            answer += f"\n- {filename}, página {page}"
    
    return answer

# Test questions
print("\n" + "="*50)
print("Testing the system with some questions:")
print("="*50)

questions = [
    "What is the coverage limit of IDEAL GUARANTEE?"
#    "¿Cuál es el límite máximo de cobertura anual y bajo qué circunstancias puede aumentar a $3,000,000?",
#    "¿Qué significa la reducción del 50% de beneficios cuando se reciben servicios fuera de la Red de Proveedores Plan Ideal en Estados Unidos?",
#    "¿Cuáles son las condiciones específicas de cobertura durante los primeros 30 días después de la Fecha de Inicio Original de la póliza?",
#    "¿Qué requisitos de notificación debe cumplir el asegurado antes de una hospitalización o servicios ambulatorios, y cuáles son las penalizaciones por incumplimiento?",
#    "¿Cuál es la diferencia en cobertura para trastornos congénitos diagnosticados antes versus después de los 18 años de edad?",
#    "¿Qué limitaciones específicas existen para el tratamiento de autismo y cuál es el proceso de autorización requerido?",
#    "¿En qué circunstancias se aplica un solo deducible por familia en lugar de deducibles individuales por asegurado?",
#    "¿Cuáles son las exclusiones principales relacionadas con deportes profesionales y condiciones preexistentes no declaradas?",
#    "¿Qué procedimiento de arbitraje vinculante debe seguirse para resolver disputas y dónde debe llevarse a cabo?",
#    "¿Cuáles son los límites específicos y condiciones para el beneficio de trasplante de órganos, incluyendo la cobertura para gastos del donante?"
]

for question in questions:
    print(f"\nQuestion: {question}")
    answer = answer_question(question)
    print(f"Answer: {answer}")