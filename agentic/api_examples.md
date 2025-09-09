# Ejemplos de uso de la API de Knowledge Base

## 1. Health Check
```bash
curl http://localhost:8000/health
```

## 2. Consulta Simple (sin historial)
```bash
curl -X POST "http://localhost:8000/chat/simple?message=¿Qué es el Core TA Rider?"
```

## 3. Consulta con Historial Completo

### Primera consulta (sin historial previo)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Qué productos de seguro están disponibles?",
    "messages": [],
    "search_knowledge": true,
    "stream": false
  }'
```

### Segunda consulta (con historial)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Dame más detalles sobre el primero",
    "messages": [
      {
        "role": "user",
        "content": "¿Qué productos de seguro están disponibles?"
      },
      {
        "role": "assistant",
        "content": "Según los documentos disponibles, tenemos dos productos principales: Core TA Rider e Ideal Guarantee Jr..."
      }
    ],
    "session_id": "uuid-de-la-sesion-anterior",
    "search_knowledge": true,
    "stream": false
  }'
```

## 4. Ejemplo con JavaScript/Fetch

```javascript
// Función para hacer consultas con historial
async function chatWithHistory() {
    let messages = [];
    let sessionId = null;
    
    // Primera consulta
    const response1 = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: "¿Cuáles son las coberturas del Core TA Rider?",
            messages: messages,
            search_knowledge: true,
            stream: false
        })
    });
    
    const data1 = await response1.json();
    sessionId = data1.session_id;
    messages = data1.messages;
    
    console.log("Respuesta 1:", data1.response);
    
    // Segunda consulta con contexto
    const response2 = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: "¿Cuál es el monto máximo de cobertura?",
            messages: messages,
            session_id: sessionId,
            search_knowledge: true,
            stream: false
        })
    });
    
    const data2 = await response2.json();
    console.log("Respuesta 2 (con contexto):", data2.response);
    
    return data2;
}
```

## 5. Ejemplo con Python requests

```python
import requests
import json

def chat_with_context():
    api_url = "http://localhost:8000/chat"
    
    # Historial de conversación
    messages = []
    session_id = None
    
    # Primera pregunta
    request_1 = {
        "message": "¿Qué es Ideal Guarantee Jr?",
        "messages": messages,
        "search_knowledge": True,
        "stream": False
    }
    
    response_1 = requests.post(api_url, json=request_1)
    data_1 = response_1.json()
    
    # Guardar sesión y mensajes
    session_id = data_1["session_id"]
    messages = data_1["messages"]
    
    print(f"Pregunta 1: {request_1['message']}")
    print(f"Respuesta 1: {data_1['response'][:200]}...")
    print(f"Session ID: {session_id}")
    
    # Segunda pregunta con contexto
    request_2 = {
        "message": "¿Cuáles son los beneficios principales?",
        "messages": messages,
        "session_id": session_id,
        "search_knowledge": True,
        "stream": False
    }
    
    response_2 = requests.post(api_url, json=request_2)
    data_2 = response_2.json()
    
    print(f"\nPregunta 2: {request_2['message']}")
    print(f"Respuesta 2: {data_2['response'][:200]}...")
    print(f"Total mensajes en historial: {len(data_2['messages'])}")
    
    # Tercera pregunta continuando la conversación
    request_3 = {
        "message": "¿Hay algún período de espera?",
        "messages": data_2["messages"],
        "session_id": session_id,
        "search_knowledge": True,
        "stream": False
    }
    
    response_3 = requests.post(api_url, json=request_3)
    data_3 = response_3.json()
    
    print(f"\nPregunta 3: {request_3['message']}")
    print(f"Respuesta 3: {data_3['response'][:200]}...")
    
    return data_3

if __name__ == "__main__":
    result = chat_with_context()
```

## 6. Listar Documentos
```bash
curl http://localhost:8000/documents
```

## 7. Listar Sesiones Activas
```bash
curl http://localhost:8000/sessions
```

## 8. Limpiar una Sesión
```bash
curl -X DELETE http://localhost:8000/session/{session_id}
```

## 9. Recargar Knowledge Base
```bash
curl -X POST http://localhost:8000/reload-knowledge
```

## 10. Ejemplo de Response Completo con Referencias

Cuando el agente responde, automáticamente extrae las referencias de documentos:

**Request:**
```json
{
  "message": "¿Cuáles son las coberturas del Core TA Rider?",
  "search_knowledge": true,
  "format_response": true
}
```

**Response:**
```json
{
  "response": "## 📋 Coberturas del Core TA Rider\n\n### ✅ Coberturas Principales\n\n**1. Muerte Accidental**\n- Beneficio por fallecimiento debido a accidente\n- Monto máximo: $500,000\n- Aplica mundialmente\n\n**2. Desmembramiento**\n- Pérdida de extremidades: 50% del beneficio\n- Pérdida de visión: 100% por ambos ojos\n\n### ⚠️ Exclusiones Importantes\n\n- Suicidio o lesiones autoinfligidas\n- Participación en actividades ilegales\n- Deportes extremos profesionales\n\n### 💡 Puntos Clave\n\n- **Sin exámenes médicos** para montos estándar\n- Primas desde **$15 mensuales**\n- Cobertura inmediata tras aprobación",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_references": [
    {
      "document_name": "Core_TA_Rider.pdf",
      "pages": [3, 5, 8, 12, 15],
      "relevance_score": null
    }
  ],
  "sources": [],
  "messages": [
    {
      "role": "user",
      "content": "¿Cuáles son las coberturas del Core TA Rider?",
      "timestamp": "2024-01-15T10:30:00"
    },
    {
      "role": "assistant",
      "content": "## 📋 Coberturas del Core TA Rider...",
      "timestamp": "2024-01-15T10:30:05"
    }
  ],
  "metadata": {
    "model": "qwen2.5:7b-instruct",
    "knowledge_search": true,
    "timestamp": "2024-01-15T10:30:05",
    "formatted": true,
    "original_length": 850,
    "formatted_length": 920,
    "references_found": 1
  }
}
```

**Nota:** El sistema automáticamente:
1. Extrae las referencias de documentos mencionadas en la respuesta
2. Las separa en un array estructurado `document_references`
3. Limpia la respuesta principal de las referencias
4. Aplica formateo profesional a la respuesta

## Estructura del DTO ChatRequest

```json
{
  "message": "string",           // Mensaje actual del usuario
  "messages": [                  // Historial de conversación
    {
      "role": "user|assistant",  // Rol del mensaje
      "content": "string",        // Contenido del mensaje
      "timestamp": "datetime",   // Timestamp opcional
      "metadata": {}             // Metadata adicional opcional
    }
  ],
  "session_id": "string",        // ID de sesión para continuidad
  "search_knowledge": true,      // Si buscar en knowledge base
  "stream": false               // Si hacer streaming de respuesta
}
```

## Estructura del DTO ChatResponse

```json
{
  "response": "string",          // Respuesta del asistente (sin referencias)
  "session_id": "string",        // ID de sesión
  "sources": [],                 // Fuentes utilizadas
  "document_references": [       // Referencias extraídas de documentos
    {
      "document_name": "Core_TA_Rider.pdf",
      "pages": [3, 5, 12],
      "relevance_score": null
    },
    {
      "document_name": "Ideal_Guarantee_Jr.pdf",
      "pages": [1, 7],
      "relevance_score": null
    }
  ],
  "messages": [                  // Historial actualizado
    {
      "role": "string",
      "content": "string",
      "timestamp": "datetime",
      "metadata": {}
    }
  ],
  "metadata": {                  // Metadata de la respuesta
    "model": "string",
    "knowledge_search": true,
    "timestamp": "datetime",
    "formatted": true,
    "original_length": 1500,
    "formatted_length": 1800,
    "references_found": 2
  }
}
```

## Notas Importantes

1. **Manejo de Sesiones**: El `session_id` se genera automáticamente en la primera consulta si no se proporciona
2. **Historial**: El historial de mensajes se mantiene y debe enviarse en cada consulta para mantener contexto
3. **Búsqueda en Knowledge Base**: Se puede activar/desactivar con `search_knowledge`
4. **Límite de Contexto**: El sistema usa los últimos 10 mensajes del historial para contexto
5. **Persistencia**: Las sesiones se mantienen en memoria mientras el servidor esté activo