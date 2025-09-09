from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.embedder.ollama import OllamaEmbedder
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.storage.agent.postgres import PgAgentStorage
from phi.vectordb.pgvector import PgVector, SearchType
from phi.playground import Playground, serve_playground_app
import os
from pathlib import Path

# 1. Setup
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# Archivo de control para saber si ya se cargó
LOAD_FLAG_FILE = Path(".knowledge_base_loaded")

# Configuración del knowledge base
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(
        table_name="recipes_ollama",
        db_url=db_url,
        search_type=SearchType.hybrid,
        embedder=OllamaEmbedder(model="nomic-embed-text", dimensions=768),
    ),
)

# Cargar solo si no se ha cargado antes o si se fuerza la recarga
def load_knowledge_base(force_reload=False):
    if force_reload or not LOAD_FLAG_FILE.exists():
        print("Loading knowledge base...")
        knowledge_base.load(upsert=True)
        LOAD_FLAG_FILE.touch()
        print("Knowledge base loaded successfully!")
    else:
        print("Knowledge base already loaded. Using existing data.")

# Cargar con opción de forzar recarga desde variable de entorno
force_reload = os.getenv("FORCE_RELOAD", "false").lower() == "true"
load_knowledge_base(force_reload=force_reload)

# 2. Agentic RAG
agent = Agent(
    model=Ollama(id="qwen2.5:7b-instruct"),
    knowledge=knowledge_base,
    search_knowledge=True,
    show_tool_calls=True,
    markdown=True,
)

# Ejemplo de uso
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        # 3. UI
        rag_agent = Agent(
            name="RAG Agent",
            agent_id="rag-agent",
            model=Ollama(id="qwen2.5:7b-instruct"),
            knowledge=knowledge_base,
            search_knowledge=True,
            read_chat_history=True,
            storage=PgAgentStorage(table_name="rag_agent_sessions_ollama", db_url=db_url),
            instructions=[
                "Always search your knowledge base first and use it if available.",
                "Share the page number or source URL of the information you used in your response.",
                "If health benefits are mentioned, include them in the response.",
                "Important: Use tables where possible.",
            ],
            markdown=True,
        )
        app = Playground(agents=[rag_agent]).get_app()
        serve_playground_app(app)
    else:
        # Modo interactivo
        agent.print_response(
            "Hi, i want to make a 3 course meal. Can you recommend some recipes. "
            "I'd like to start with a soup, then im thinking a thai curry for the main course "
            "and finish with a dessert",
            stream=True
        )