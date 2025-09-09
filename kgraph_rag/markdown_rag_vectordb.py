from dotenv import load_dotenv
import os
from typing import List, Dict
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain.chains import RetrievalQA
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_core.output_parsers import StrOutputParser
import chromadb
# from chromadb.config import Settings  # Not needed for basic usage

load_dotenv()

# Configuration
MARKDOWN_DIR = os.environ.get("MARKDOWN_DIR", "./markdown_output")
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "health_products_rag"

# Using same Ollama configuration as bmi_graph_rag_consulta.py
print("Initializing Ollama models...")
llm = ChatOllama(model="qwen2.5:7b-instruct", temperature=0)

# Using Ollama embeddings (local)
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",  # Efficient local embedding model
    base_url="http://localhost:11434"
)

class MarkdownRAGSystem:
    """RAG system for markdown documents with local vector database"""
    
    def __init__(self, 
                 markdown_dir: str = MARKDOWN_DIR,
                 persist_dir: str = CHROMA_PERSIST_DIR,
                 collection_name: str = COLLECTION_NAME):
        self.markdown_dir = markdown_dir
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.vectorstore = None
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
    def load_documents(self) -> List:
        """Load markdown documents with metadata preservation"""
        print(f"Loading markdown documents from {self.markdown_dir}...")
        
        # Custom loader for markdown with metadata
        loader = DirectoryLoader(
            self.markdown_dir,
            glob="**/*.md",
            loader_cls=UnstructuredMarkdownLoader,
            loader_kwargs={"mode": "elements"},  # Preserve structure
            show_progress=True
        )
        
        documents = loader.load()
        
        # Enrich metadata
        for doc in documents:
            # Extract filename without extension
            filename = os.path.basename(doc.metadata.get("source", ""))
            doc.metadata["filename"] = filename
            doc.metadata["doc_type"] = "health_product"
            
            # Try to extract page info from content if available
            if "Page " in doc.page_content[:50]:
                import re
                page_match = re.search(r"Page (\d+)", doc.page_content[:50])
                if page_match:
                    doc.metadata["page"] = int(page_match.group(1))
        
        print(f"Loaded {len(documents)} document elements")
        return documents
    
    def split_documents(self, documents: List) -> List:
        """Split documents into optimal chunks for RAG"""
        print("Splitting documents into chunks...")
        
        # Optimized splitter for health product documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Smaller chunks for precise retrieval
            chunk_overlap=100,  # Good overlap for context
            length_function=len,
            separators=["\n\n", "\n", ".", ";", ",", " ", ""],
            keep_separator=True
        )
        
        chunks = text_splitter.split_documents(documents)
        
        # Add chunk index to metadata
        current_doc = None
        chunk_index = 0
        
        for chunk in chunks:
            if chunk.metadata.get("source") != current_doc:
                current_doc = chunk.metadata.get("source")
                chunk_index = 0
            
            chunk.metadata["chunk_index"] = chunk_index
            chunk_index += 1
        
        print(f"Created {len(chunks)} document chunks")
        return chunks
    
    def create_or_load_vectorstore(self, chunks: List = None):
        """Create new or load existing vector store"""
        
        if chunks:
            print("Creating new vector store...")
            
            # Filter complex metadata that Chroma can't handle
            filtered_chunks = filter_complex_metadata(chunks)
            
            # Create vector store with simplified settings
            self.vectorstore = Chroma.from_documents(
                documents=filtered_chunks,
                embedding=embeddings,
                collection_name=self.collection_name,
                persist_directory=self.persist_dir
            )
            
            print(f"Vector store created with {len(chunks)} chunks")
        else:
            print("Loading existing vector store...")
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=embeddings,
                persist_directory=self.persist_dir
            )
            
            # Verify collection exists
            try:
                collection = self.vectorstore._collection
                count = collection.count()
                print(f"Loaded vector store with {count} documents")
            except:
                print("Vector store loaded successfully")
    
    def build_and_index(self):
        """Build complete RAG pipeline from scratch"""
        documents = self.load_documents()
        chunks = self.split_documents(documents)
        self.create_or_load_vectorstore(chunks)
        print("RAG system built and indexed successfully!")
    
    def create_qa_chain(self):
        """Create QA chain with source citation"""
        
        # Custom prompt for health products
        qa_prompt = ChatPromptTemplate.from_template("""
        Eres un asistente experto en productos de salud. Usa el siguiente contexto para responder la pregunta.
        Si no sabes la respuesta, di que no tienes información suficiente. No inventes información.
        
        Contexto: {context}
        
        Historial de conversación: {chat_history}
        
        Pregunta: {question}
        
        Responde de forma clara y concisa, citando la información relevante del contexto.
        """)
        
        # Create conversational retrieval chain
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=self.vectorstore.as_retriever(
                search_type="mmr",  # Maximum marginal relevance for diversity
                search_kwargs={"k": 5, "fetch_k": 10}
            ),
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": qa_prompt},
            return_source_documents=True,
            verbose=True
        )
        
        return qa_chain
    
    def query(self, question: str, include_sources: bool = True) -> str:
        """Query the RAG system"""
        
        if not self.vectorstore:
            return "Error: Vector store not initialized. Run build_and_index() first."
        
        qa_chain = self.create_qa_chain()
        
        # Get response
        result = qa_chain.invoke({"question": question})
        
        answer = result["answer"]
        
        # Add sources if requested
        if include_sources and "source_documents" in result:
            sources = set()
            relevant_chunks = []
            
            for doc in result["source_documents"]:
                filename = doc.metadata.get("filename", "Unknown")
                page = doc.metadata.get("page", "N/A")
                chunk_index = doc.metadata.get("chunk_index", "N/A")
                sources.add((filename, page))
                
                # Collect relevant text snippets
                if len(doc.page_content) > 0:
                    snippet = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                    relevant_chunks.append({
                        "filename": filename,
                        "page": page,
                        "chunk": chunk_index,
                        "snippet": snippet.strip()
                    })
            
            # Add source citations
            answer += "\n\n📄 **Fuentes consultadas:**"
            for filename, page in sorted(sources):
                if page != "N/A":
                    answer += f"\n- {filename} (página {page})"
                else:
                    answer += f"\n- {filename}"
            
            # Add relevant excerpts
            if relevant_chunks:
                answer += "\n\n📝 **Extractos relevantes:**"
                for i, chunk in enumerate(relevant_chunks[:3], 1):  # Show top 3
                    answer += f"\n\n{i}. De {chunk['filename']}:"
                    answer += f"\n   \"{chunk['snippet']}\""
        
        return answer
    
    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        """Direct similarity search with scores"""
        
        if not self.vectorstore:
            return []
        
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": round(1 - score, 3)  # Convert distance to similarity
            })
        
        return formatted_results
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()
        print("Conversation memory cleared")

# Helper functions for easy use
def build_rag_system():
    """Build and index the RAG system"""
    rag = MarkdownRAGSystem()
    rag.build_and_index()
    return rag

def query_rag(question: str, rebuild: bool = False):
    """Quick query function"""
    rag = MarkdownRAGSystem()
    
    if rebuild:
        rag.build_and_index()
    else:
        rag.create_or_load_vectorstore()
    
    return rag.query(question)

if __name__ == "__main__":
    print("=== Sistema RAG con Vector Database Local ===\n")
    
    # Initialize system
    rag_system = MarkdownRAGSystem()
    
    # Check if we need to build or just load
    if not os.path.exists(CHROMA_PERSIST_DIR):
        print("Building vector database from scratch...")
        rag_system.build_and_index()
    else:
        print("Loading existing vector database...")
        rag_system.create_or_load_vectorstore()
    
    # Interactive query loop
    print("\n✅ Sistema listo para consultas")
    print("Comandos especiales:")
    print("- 'rebuild': Reconstruir la base de datos vectorial")
    print("- 'clear': Limpiar memoria de conversación")
    print("- 'search <query>': Búsqueda directa por similitud")
    print("- 'salir': Terminar el programa\n")
    
    while True:
        question = input("\n💬 Pregunta: ").strip()
        
        if question.lower() == 'salir':
            break
        elif question.lower() == 'rebuild':
            rag_system.build_and_index()
            print("✅ Base de datos reconstruida")
        elif question.lower() == 'clear':
            rag_system.clear_memory()
        elif question.lower().startswith('search '):
            search_query = question[7:]
            results = rag_system.similarity_search(search_query, k=3)
            print("\n🔍 Resultados de búsqueda:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Similitud: {result['similarity_score']}")
                print(f"   Archivo: {result['metadata'].get('filename', 'Unknown')}")
                print(f"   Contenido: {result['content'][:150]}...")
        elif question:
            print("\n🤔 Procesando...")
            answer = rag_system.query(question)
            print(f"\n📚 Respuesta:\n{answer}")