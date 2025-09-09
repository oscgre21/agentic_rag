# Chat History Management

## Overview

The Agentic API supports conversation history to maintain context across multiple messages in a chat session. This allows the agent to reference previous questions and answers, providing more coherent and contextual responses.

## How It Works

### 1. Message Structure

Each message in the history must have:
- `role`: Either "user" or "assistant"
- `content`: The message text

```json
{
  "role": "user",
  "content": "What insurance products do you offer?"
}
```

### 2. Sending History with Requests

Include the conversation history in the `messages` array when making a chat request:

```json
{
  "message": "Which one is best for families?",
  "session_id": "unique-session-id",
  "messages": [
    {
      "role": "user",
      "content": "What insurance products do you offer?"
    },
    {
      "role": "assistant",
      "content": "We offer life insurance, health insurance, and home insurance..."
    }
  ],
  "search_knowledge": true,
  "format_response": true
}
```

### 3. Session Management

- Each `session_id` maintains its own conversation context
- Sessions are isolated from each other
- The agent remembers the conversation history within a session
- If no `session_id` is provided, a new one is generated automatically

## Implementation Details

### Agent Memory

The `get_or_create_agent` function now:
1. Accepts an optional `messages` parameter with the conversation history
2. Converts each `Message` object to a `PhiMessage` for the agent
3. Updates the agent's internal message history
4. Maintains separate histories for different sessions

### Code Flow

```python
# The function signature has been updated to:
def get_or_create_agent(session_id: str = None, messages: List[Message] = None) -> tuple[Agent, str]:
    # ... create or get agent ...
    
    # If messages are provided, update the agent's history
    if messages:
        for msg in messages:
            phi_msg = PhiMessage(
                role=msg.role,
                content=msg.content
            )
            # Add to agent's message history
            agent.messages.append(phi_msg)
```

## Example Usage

### Python Example

```python
import httpx
import asyncio

async def chat_with_history():
    async with httpx.AsyncClient() as client:
        session_id = "my-session-123"
        
        # First message
        response1 = await client.post(
            "http://localhost:8000/chat",
            json={
                "message": "What types of insurance do you offer?",
                "session_id": session_id,
                "messages": []
            }
        )
        first_response = response1.json()["response"]
        
        # Second message with history
        response2 = await client.post(
            "http://localhost:8000/chat",
            json={
                "message": "Tell me more about the life insurance",
                "session_id": session_id,
                "messages": [
                    {"role": "user", "content": "What types of insurance do you offer?"},
                    {"role": "assistant", "content": first_response}
                ]
            }
        )
        
        # The agent will have context from the previous exchange

asyncio.run(chat_with_history())
```

### cURL Example

```bash
# First message
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What insurance do you offer?",
    "session_id": "session-123",
    "messages": []
  }'

# Second message with history
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which is best for families?",
    "session_id": "session-123",
    "messages": [
      {"role": "user", "content": "What insurance do you offer?"},
      {"role": "assistant", "content": "We offer life, health, and home insurance..."}
    ]
  }'
```

## Best Practices

1. **Maintain Order**: Always send messages in chronological order
2. **Include Full History**: For best context, include all previous messages in the session
3. **Limit History Size**: For very long conversations, consider limiting to the last 10-20 messages
4. **Session IDs**: Use consistent session IDs to maintain conversation continuity
5. **Role Accuracy**: Ensure "role" is correctly set to "user" or "assistant"

## Benefits

- **Contextual Responses**: The agent can reference previous questions and answers
- **Natural Conversations**: Enables follow-up questions without repeating context
- **Session Isolation**: Multiple users can have independent conversations
- **Persistent Context**: Context is maintained as long as the session is active

## Testing

Use the provided test script to verify history functionality:

```bash
python test_chat_history.py
```

This script tests:
- Sending messages without history
- Sending messages with history
- Context preservation across messages
- Session isolation between different session IDs