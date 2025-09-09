from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFKnowledgeBase
from phi.storage.agent.postgres import PgAgentStorage
from phi.vectordb.pgvector import PgVector, SearchType
from phi.playground import Playground, serve_playground_app
from pathlib import Path

# 1. Traditional RAG
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# Cargar todos los PDFs de la carpeta docs
pdf_path = Path("docs")
pdf_files = list(pdf_path.glob("*.pdf"))

print(f"Encontrados {len(pdf_files)} archivos PDF en docs/")
for pdf in pdf_files:
    print(f"  - {pdf.name}")

knowledge_base = PDFKnowledgeBase(
    path="docs",  # Cargar todos los PDFs de la carpeta docs
    vector_db=PgVector(
        table_name="insurance_docs_ollama",  # Nueva tabla para documentos de seguros
        db_url=db_url,
        search_type=SearchType.hybrid,
        embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
    ),
)
# Cargar solo si es necesario (primera vez o actualizaciones)
# Comentar esta línea después de la primera carga exitosa
knowledge_base.load(upsert=True)
# agent = Agent(
#     model=Ollama(id="qwen2.5:7b-instruct"),
#     knowledge=knowledge_base,
#     add_context=True,
#     search_knowledge=False,
#     markdown=True,
# )
# agent.print_response(
#     "Hi, i want to make a 3 course meal. Can you recommend some recipes. "
#     "I'd like to start with a soup, then im thinking a thai curry for the main course "
#     "and finish with a dessert",
#     stream=True
# )

# 2. Agentic RAG
agent = Agent(
    model=Ollama(id="qwen2.5:7b-instruct"),
    knowledge=knowledge_base,
    search_knowledge=True,
    show_tool_calls=True,
    markdown=True,
)
agent.print_response(
    "¿Cuáles son las principales coberturas y beneficios de los productos de seguro? "
    "Dame un resumen de las características más importantes.",
    stream=True
)

# 3. UI
rag_agent = Agent(
    name="RAG Agent",
    agent_id="rag-agent",
    model=Ollama(id="qwen2.5:7b-instruct"),
    knowledge=knowledge_base,
    search_knowledge=True,
    read_chat_history=True,
    storage=PgAgentStorage(table_name="insurance_agent_sessions_ollama", db_url=db_url),
    instructions=[
        "Siempre busca primero en tu base de conocimientos y úsala si está disponible.",
        "Comparte el número de página o el nombre del documento de donde obtuviste la información.",
        "Si se mencionan beneficios o coberturas, inclúyelos detalladamente en la respuesta.",
        "Importante: Usa tablas cuando sea posible para comparar productos o beneficios.",
        "Responde en español y sé claro con los términos de seguros.",
    ],
    markdown=True,
)
app = Playground(agents=[rag_agent]).get_app()
if __name__ == "__main__":
    # knowledge_base.load(upsert=True)  # Ya cargado anteriormente
    serve_playground_app(app)