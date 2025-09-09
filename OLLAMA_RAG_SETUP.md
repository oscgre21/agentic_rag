# Knowledge Graph RAG con Ollama - Guía de Configuración

Esta guía te ayudará a configurar y ejecutar el sistema de Knowledge Graph RAG usando Ollama en lugar de OpenAI.

## Prerrequisitos

1. **Python 3.8+** instalado
2. **Docker** instalado y ejecutándose
3. **Ollama** instalado en tu sistema
4. **uv** (Python package manager) instalado

## Paso 1: Instalar Ollama

Si no tienes Ollama instalado:

```bash
# En macOS
brew install ollama

# En Linux
curl -fsSL https://ollama.com/install.sh | sh
```

## Paso 2: Descargar modelos necesarios

```bash
# Modelo principal para el procesamiento de texto
ollama pull qwen2.5:7b-instruct

# Modelo para embeddings
ollama pull nomic-embed-text
```

## Paso 3: Configurar Neo4j

1. Iniciar Neo4j con Docker Compose:
```bash
docker-compose up -d
```

2. Verificar que Neo4j esté ejecutándose:
```bash
docker-compose ps
```

3. Neo4j estará disponible en:
   - Browser: http://localhost:7474
   - Bolt: bolt://localhost:7687
   - Credenciales: neo4j/password123

## Paso 4: Instalar dependencias de Python

```bash
# Instalar todas las dependencias del proyecto
uv pip install -r requirements.txt

# Instalar dependencia adicional para Ollama
uv pip install langchain-ollama
```

## Paso 5: Configurar variables de entorno

Crear o verificar el archivo `.env` en la raíz del proyecto:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
AURA_INSTANCENAME=local-instance
```

## Paso 6: Ejecutar el script

### Opción A: Versión Simple (Recomendada para empezar)

```bash
python kgraph_rag/roman_emp_graph_rag_ollama_simple.py
```

Esta versión:
- Limpia la base de datos existente
- Carga datos de Wikipedia sobre el Imperio Romano
- Crea un knowledge graph
- Responde preguntas de ejemplo

### Opción B: Versión Completa (Con características avanzadas)

```bash
python kgraph_rag/roman_emp_graph_rag_ollama.py
```

**Nota**: Esta versión puede tener problemas de compatibilidad con algunas versiones de Neo4j debido a la creación de índices vectoriales.

## Paso 7: Verificar resultados

1. Abrir Neo4j Browser en http://localhost:7474
2. Conectar con las credenciales (neo4j/password123)
3. Ejecutar la siguiente consulta para ver el knowledge graph:

```cypher
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100
```

## Uso del sistema

### Ejemplo de uso programático

```python
from kgraph_rag.roman_emp_graph_rag_ollama_simple import answer_question

# Hacer una pregunta
question = "Who was Julius Caesar?"
answer = answer_question(question)
print(f"Q: {question}")
print(f"A: {answer}")
```

### Personalización

Para usar diferentes modelos de Ollama, modifica estas líneas en el script:

```python
# Modelo principal
chat = ChatOllama(model="qwen2.5:7b-instruct", temperature=0)

# Modelo de embeddings (solo en versión completa)
OllamaEmbeddings(model="nomic-embed-text")
```

## Solución de problemas

### Error: "ollama: command not found"
- Asegúrate de que Ollama esté instalado y en tu PATH

### Error: "model not found"
- Ejecuta `ollama list` para ver modelos disponibles
- Descarga el modelo necesario con `ollama pull <modelo>`

### Error de conexión a Neo4j
- Verifica que Docker esté ejecutándose
- Verifica que el contenedor Neo4j esté activo: `docker-compose ps`
- Revisa los logs: `docker-compose logs neo4j`

### Error de memoria
- Si tienes problemas de memoria, puedes usar modelos más pequeños:
  - `qwen2.5:3b-instruct` en lugar de `qwen2.5:7b-instruct`
  - `qwen3:0.6b` para pruebas rápidas

## Modelos recomendados según recursos

### Recursos limitados (< 8GB RAM)
- Chat: `qwen2.5:3b-instruct` o `gemma3:1b`
- Embeddings: `nomic-embed-text` (ya es ligero)

### Recursos medios (8-16GB RAM)
- Chat: `qwen2.5:7b-instruct` o `mistral-nemo:latest`
- Embeddings: `nomic-embed-text`

### Recursos altos (> 16GB RAM)
- Chat: `qwen2.5:14b-instruct` o `qwen2.5:32b-instruct`
- Embeddings: `nomic-embed-text`

## Siguientes pasos

1. **Explorar el knowledge graph**: Usa Neo4j Browser para visualizar las entidades y relaciones creadas
2. **Personalizar las preguntas**: Modifica el script para hacer diferentes tipos de preguntas
3. **Cambiar el dominio**: Reemplaza "Roman Empire" con otro tema de Wikipedia
4. **Optimizar el rendimiento**: Experimenta con diferentes modelos y configuraciones