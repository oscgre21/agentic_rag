# Sistemas RAG: Knowledge Graph + Vector Database

Este proyecto implementa tres sistemas complementarios de RAG (Retrieval-Augmented Generation) para productos de salud:

## 1. Sistema RAG con Vector Database (`markdown_rag_vectordb.py`)

### Características:
- **Base de datos vectorial local** usando Chroma
- **Embeddings locales** con Ollama (nomic-embed-text)
- **Búsqueda semántica** con MMR (Maximum Marginal Relevance)
- **Memoria conversacional** para mantener contexto
- **Citas de fuentes** con extractos relevantes

### Uso:

```bash
# Ejecutar sistema RAG vectorial
python kgraph_rag/markdown_rag_vectordb.py

# Comandos disponibles:
# - 'rebuild': Reconstruir base de datos
# - 'clear': Limpiar memoria
# - 'search <query>': Búsqueda directa
# - 'salir': Terminar
```

### Ejemplo de código:
```python
from markdown_rag_vectordb import MarkdownRAGSystem

# Inicializar sistema
rag = MarkdownRAGSystem()

# Construir índice (primera vez)
rag.build_and_index()

# Realizar consulta
respuesta = rag.query("¿Cuál es el límite de cobertura?")
print(respuesta)
```

## 2. Sistema Híbrido (`hybrid_rag_system.py`)

### Características:
- **Combina Knowledge Graph + Vector RAG**
- **Extracción automática de entidades**
- **Búsqueda estructurada y semántica**
- **Comparación de métodos**

### Arquitectura:
```
Pregunta → Extracción de Entidades
    ↓
    ├─→ Knowledge Graph (relaciones estructuradas)
    └─→ Vector Store (búsqueda semántica)
         ↓
    Respuesta Combinada + Fuentes
```

### Uso:

```bash
# Ejecutar sistema híbrido
python kgraph_rag/hybrid_rag_system.py

# Comando especial:
# - 'comparar': Ver resultados de cada método
```

### Ejemplo de código:
```python
from hybrid_rag_system import HybridRAGSystem

# Inicializar
hybrid = HybridRAGSystem(kg, vector_rag, llm)

# Consulta híbrida
respuesta = hybrid.hybrid_query("¿Qué productos contienen paracetamol?")

# Comparar métodos
hybrid.compare_methods("¿Cuáles son los efectos secundarios?")
```

## 3. Knowledge Graph con Schema (`health_product_schema.py`)

### Entidades definidas:
- `Product`: Productos farmacéuticos
- `ActiveIngredient`: Ingredientes activos
- `Disease`: Enfermedades
- `Symptom`: Síntomas
- `Manufacturer`: Fabricantes
- `SideEffect`: Efectos secundarios
- `Dosage`: Información de dosis

### Relaciones:
- `CONTAINS`: Producto contiene ingrediente
- `TREATS`: Producto trata enfermedad
- `RELIEVES`: Producto alivia síntoma
- `MAY_CAUSE`: Puede causar efecto secundario

## Comparación de Sistemas

| Característica | Knowledge Graph | Vector RAG | Sistema Híbrido |
|----------------|-----------------|------------|-----------------|
| **Fortaleza** | Relaciones explícitas | Búsqueda semántica | Combina ambos |
| **Tipo de consultas** | Estructuradas | Lenguaje natural | Ambas |
| **Precisión** | Alta para entidades | Alta para contexto | Muy alta |
| **Flexibilidad** | Media | Alta | Muy alta |
| **Fuentes** | Por entidad | Por chunk | Completas |

## Instalación y Configuración

### 1. Requisitos:
```bash
pip install -r requirements.txt
```

### 2. Modelos Ollama necesarios:
```bash
# LLM para generación
ollama pull qwen3:4b

# Embeddings para vectores
ollama pull nomic-embed-text
```

### 3. Variables de entorno (.env):
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
MARKDOWN_DIR=./markdown_output
CHROMA_PERSIST_DIR=./chroma_db
```

### 4. Preparar datos:
```bash
# Procesar PDFs a Knowledge Graph
python kgraph_rag/bmi_process_graph.py

# El sistema vectorial se construye automáticamente
# al ejecutar markdown_rag_vectordb.py
```

## Mejores Prácticas

### Para consultas sobre relaciones:
Use el **Knowledge Graph** o **Sistema Híbrido**:
- "¿Qué productos fabrican X laboratorio?"
- "¿Qué medicamentos interactúan con Y?"

### Para búsqueda de información general:
Use **Vector RAG** o **Sistema Híbrido**:
- "¿Cómo funciona la cobertura?"
- "Explica los beneficios del plan"

### Para máxima precisión:
Use siempre el **Sistema Híbrido** que combina:
- Estructura del Knowledge Graph
- Contexto completo del Vector RAG

## Solución de Problemas

### Error: "Vector store not initialized"
```bash
# Reconstruir base de datos
python -c "from markdown_rag_vectordb import build_rag_system; build_rag_system()"
```

### Error: Neo4j connection failed
```bash
# Verificar que Neo4j esté corriendo
docker-compose ps
docker-compose up -d
```

### Embeddings lentos
```bash
# Verificar que Ollama esté corriendo
ollama list
systemctl status ollama  # Linux
brew services list       # macOS
```

## Extensión del Sistema

### Agregar nuevas entidades al KG:
```python
# En health_product_schema.py
NODE_LABELS["NewEntity"] = "Descripción"
RELATIONSHIP_TYPES["NEW_REL"] = "Descripción"
```

### Mejorar búsqueda vectorial:
```python
# Ajustar parámetros en markdown_rag_vectordb.py
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 10,        # Más resultados
        "fetch_k": 20,  # Más candidatos
        "lambda_mult": 0.5  # Balance diversidad/relevancia
    }
)
```

## Performance

- **Knowledge Graph**: ~100ms por consulta
- **Vector RAG**: ~200-500ms (incluye embeddings)
- **Sistema Híbrido**: ~500-800ms (ambas búsquedas)

Para mejorar performance:
1. Usar índices en Neo4j
2. Reducir chunk_size en vector store
3. Cachear embeddings frecuentes
4. Usar GPU para Ollama si está disponible