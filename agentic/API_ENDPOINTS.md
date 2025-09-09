# API Endpoints Documentation

## File Management

### Upload PDF Document
**POST** `/upload-pdf`

Upload a PDF document to the knowledge base.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: PDF file

**Response:**
```json
{
  "filename": "document.pdf",
  "size": 1024000,
  "message": "Archivo 'document.pdf' subido exitosamente",
  "knowledge_base_updated": true,
  "total_documents": 5
}
```

**Error Responses:**
- `400` - Invalid file type (not PDF)
- `400` - File too large (exceeds AGENTIC_MAX_FILE_SIZE)
- `400` - Empty file
- `500` - Processing error

**Notes:**
- Files are saved to the `docs/` directory
- Timestamps are added to filenames to avoid collisions
- Knowledge base is automatically reloaded after upload
- Semantic cache is cleared to ensure fresh queries

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/upload-pdf" \
  -H "accept: application/json" \
  -F "file=@/path/to/document.pdf"
```

**Example using Python:**
```python
import httpx

async with httpx.AsyncClient() as client:
    with open("document.pdf", "rb") as f:
        files = {"file": ("document.pdf", f, "application/pdf")}
        response = await client.post(
            "http://localhost:8000/upload-pdf",
            files=files
        )
    print(response.json())
```

---

### Delete Document
**DELETE** `/documents/{filename}`

Delete a PDF document from the knowledge base.

**Request:**
- Method: `DELETE`
- Path Parameter: `filename` - Name of the file to delete

**Response:**
```json
{
  "message": "Archivo 'document.pdf' eliminado exitosamente",
  "remaining_documents": 4
}
```

**Error Responses:**
- `404` - File not found
- `400` - Not a PDF file
- `500` - Deletion error

**Notes:**
- Only PDF files can be deleted
- Knowledge base is automatically reloaded after deletion
- Semantic cache is cleared
- Active agent sessions are cleared

**Example using curl:**
```bash
curl -X DELETE "http://localhost:8000/documents/document.pdf"
```

---

### List Documents
**GET** `/documents`

List all PDF documents in the knowledge base.

**Response:**
```json
{
  "documents": [
    {
      "name": "document1.pdf",
      "path": "docs/document1.pdf",
      "size": 1024000
    },
    {
      "name": "document2.pdf",
      "path": "docs/document2.pdf",
      "size": 2048000
    }
  ],
  "total": 2
}
```

---

### Reload Knowledge Base
**POST** `/reload-knowledge`

Manually reload the knowledge base with current documents.

**Response:**
```json
{
  "message": "Knowledge base recargado exitosamente",
  "documents_loaded": 5
}
```

**Notes:**
- Useful after manually adding files to the `docs/` directory
- Clears all active agent sessions

---

## Chat Operations

### Send Chat Message
**POST** `/chat`

Send a message to the RAG system.

**Request:**
```json
{
  "message": "¿Cuáles son los beneficios del seguro?",
  "session_id": "optional-session-id",
  "search_knowledge": true,
  "format_response": true
}
```

**Response:**
```json
{
  "response": "Los beneficios del seguro incluyen...",
  "session_id": "generated-session-id",
  "sources": [],
  "document_references": [
    {
      "document_name": "insurance.pdf",
      "pages": [1, 5, 10]
    }
  ],
  "messages": []
}
```

---

## Cache Management

### Get Cache Statistics
**GET** `/cache/stats`

Get semantic cache statistics.

**Response:**
```json
{
  "enabled": true,
  "total_queries": 100,
  "hits": 45,
  "misses": 55,
  "hit_rate": "45.00%",
  "threshold": 0.88,
  "ttl_hours": 24,
  "max_entries": 1000
}
```

---

### Clear Cache
**POST** `/cache/clear`

Clear the semantic cache.

**Response:**
```json
{
  "message": "Caché semántico limpiado exitosamente",
  "previous_stats": {
    "total_queries": 100,
    "hits": 45,
    "misses": 55
  }
}
```

---

## System Information

### Health Check
**GET** `/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "model": "qwen3:4b",
  "embedder": "nomic-embed-text",
  "knowledge_base_loaded": true,
  "documents_count": 5
}
```

---

### List Active Sessions
**GET** `/sessions`

List all active chat sessions.

**Response:**
```json
{
  "active_sessions": [
    "session-id-1",
    "session-id-2"
  ],
  "count": 2
}
```

---

## Configuration

All endpoints respect the following environment variables:

- `AGENTIC_MAX_FILE_SIZE` - Maximum upload file size (default: 10MB)
- `AGENTIC_CACHE_ENABLED` - Enable/disable semantic cache
- `AGENTIC_MODEL_ID` - Ollama model for chat
- `AGENTIC_RESPONSE_MODEL` - Ollama model for formatting
- `AGENTIC_EMBEDDER_MODEL` - Ollama model for embeddings

See `ENV_CONFIG.md` for complete configuration options.