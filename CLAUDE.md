# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a knowledge graph-based RAG (Retrieval-Augmented Generation) system using Neo4j and LangChain. The project demonstrates multiple approaches to building and querying knowledge graphs for AI applications across different domains (general knowledge, Roman Empire, healthcare).

## Common Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start Neo4j database
docker-compose up -d

# Check Neo4j is running (should be accessible at http://localhost:7474)
docker-compose ps
```

### Running Examples
```bash
# Simple knowledge graph example
python simple_kg/kg_simple.py

# Roman Empire RAG (interactive use)
python -c "from kgraph_rag.roman_emp_graph_rag import chain; print(chain.invoke({'question': 'Who was the first Roman emperor?'}))"

# Healthcare queries
python healthcare/health_care_kg.py
python healthcare/health_care_langchain.py
```

### Environment Setup
Create a `.env` file with:
```
NEO4J_URI=your_neo4j_uri
NEO4J_USERNAME=your_neo4j_username  
NEO4J_PASSWORD=your_neo4j_password
AURA_INSTANCENAME=your_aura_instance_name
OPENAI_API_KEY=your_openai_api_key
```

## Architecture and Structure

### Core Components
1. **Knowledge Graph Layer** (Neo4j)
   - Graph database for structured data storage
   - Supports entity relationships and properties
   - Enables complex Cypher queries

2. **RAG Pipeline** (LangChain)
   - Entity extraction from text using LLMs
   - Hybrid retrieval combining:
     - Structured queries (Cypher)
     - Vector similarity search
     - Full-text search
   - Context-aware response generation

3. **Domain Implementations**
   - `simple_kg/`: Basic Neo4j operations demonstration
   - `kgraph_rag/`: Advanced RAG with Wikipedia data
   - `healthcare/`: Healthcare-specific knowledge graph
   - `prep_text_for_rag/`: Text preprocessing utilities

### Key Design Patterns
- **Hybrid Retrieval**: Combines multiple search strategies for better context
- **Entity-Relationship Mapping**: Uses LLMs to extract structured data from unstructured text
- **Conversation Memory**: Maintains context across interactions in RAG chains
- **Vector Embeddings**: Uses OpenAI embeddings for semantic search capabilities

### Database Schema Patterns
- Nodes represent entities (Person, Disease, etc.)
- Relationships define connections (BORN_IN, HAS_SYMPTOM, etc.)
- Properties store attributes on both nodes and relationships
- Full-text indexes for fuzzy search capabilities

## Development Notes

### Neo4j Connection
- Local development uses Docker-based Neo4j (ports 7474/7687)
- Production can use Neo4j Aura cloud instances
- Credentials are loaded from environment variables
- Connection pooling is handled by the neo4j-python driver

### LangChain Integration
- Uses structured output parsing for entity extraction
- Custom prompts for domain-specific queries
- Memory management for conversation continuity
- Error handling for LLM failures and rate limits

### Common Patterns When Adding Features
1. For new domain knowledge graphs:
   - Create new directory under project root
   - Implement entity extraction prompts
   - Define graph schema (nodes and relationships)
   - Build retrieval chains with appropriate prompts

2. For query enhancements:
   - Modify Cypher generation templates
   - Add new retrieval strategies to hybrid search
   - Update response formatting in chains

3. For data ingestion:
   - Use LLM-based entity extraction
   - Batch operations for performance
   - Handle duplicates with MERGE operations