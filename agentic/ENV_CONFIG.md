# Environment Variables Configuration

The Agentic API can be configured using environment variables. All variables are optional and have sensible defaults.

## Automatic Loading from .env File

The API automatically loads environment variables from a `.env` file in the same directory as `agentic_api.py`. This is the recommended way to configure the API.

### Setup
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration:
   ```env
   AGENTIC_DB_URL=postgresql+psycopg://user:pass@host:port/dbname
   AGENTIC_MODEL_ID=qwen3:4b
   ```

3. Run the API - it will automatically load the `.env` file:
   ```bash
   python agentic_api.py
   ```

**Note:** The `.env` file is automatically loaded thanks to `python-dotenv`. No additional code is needed.

## Available Environment Variables

### Database Configuration
- `AGENTIC_DB_URL`: PostgreSQL connection URL
  - Default: `postgresql+psycopg://ai:ai@localhost:5532/ai`
  - Example: `postgresql+psycopg://user:pass@host:port/dbname`

### Model Configuration
- `AGENTIC_MODEL_ID`: Ollama model for chat responses
  - Default: `qwen3:4b`
  - Examples: `llama2:13b`, `qwen2.5:14b-instruct`, `mistral:7b`

- `AGENTIC_EMBEDDER_MODEL`: Ollama model for generating embeddings
  - Default: `nomic-embed-text`
  - Examples: `nomic-embed-text`, `all-minilm:latest`

- `AGENTIC_RESPONSE_MODEL`: Ollama model for formatting responses
  - Default: `qwen2.5:7b-instruct`
  - Examples: `qwen2.5:7b-instruct`, `llama2:13b`, `mistral:7b`

### Semantic Cache Configuration
- `AGENTIC_CACHE_ENABLED`: Enable/disable semantic caching
  - Default: `true`
  - Values: `true` or `false`

- `AGENTIC_CACHE_SIMILARITY_THRESHOLD`: Similarity threshold for cache hits (0.0-1.0)
  - Default: `0.88`
  - Higher values = stricter matching
  - Recommended range: 0.85-0.95

- `AGENTIC_CACHE_TTL_HOURS`: Time to live for cache entries in hours
  - Default: `24`
  - Example: `48` for 2 days

- `AGENTIC_CACHE_MAX_ENTRIES`: Maximum number of cache entries
  - Default: `1000`
  - Older entries are removed when limit is reached

### Response Formatting
- `AGENTIC_FORMATTING_PROMPT`: Custom prompt for formatting responses
  - Default: Built-in insurance-focused formatting prompt
  - Can be customized for different domains or styles
  - Supports multiline strings when set from a file

### File Upload Configuration
- `AGENTIC_MAX_FILE_SIZE`: Maximum file size for PDF uploads in bytes
  - Default: `10485760` (10MB)
  - Example: `52428800` for 50MB

### Logging Configuration
- `AGENTIC_LOG_LEVEL`: Logging level for the API and agent
  - Default: `INFO`
  - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - `DEBUG` shows:
    - Message history details
    - Agent tool calls
    - Context sent to agent
    - Sources consulted
    - Cache operations details
  - `INFO` shows:
    - Configuration loaded
    - Query processing
    - Response generation
    - Cache hits/misses

## Usage Examples

### Using export (Linux/Mac)
```bash
export AGENTIC_MODEL_ID=llama2:13b
export AGENTIC_CACHE_ENABLED=false
export AGENTIC_CACHE_SIMILARITY_THRESHOLD=0.95
export AGENTIC_RESPONSE_MODEL=mistral:7b
python agentic_api.py
```

### Setting a custom formatting prompt
```bash
# From a file
export AGENTIC_FORMATTING_PROMPT="$(cat custom_prompt.txt)"

# Inline (use single quotes to preserve newlines)
export AGENTIC_FORMATTING_PROMPT='You are a helpful assistant.
Format the response clearly:
{response}
Question: {question}'
```

### Priority Order

Environment variables are loaded in this order (highest priority first):
1. System environment variables (export AGENTIC_...)
2. Variables from `.env` file
3. Default values in the code

**Important:** The `.env` file is automatically loaded by the API, so you don't need to add any code to use it.

### Docker Compose
```yaml
services:
  api:
    image: agentic-api
    environment:
      - AGENTIC_DB_URL=postgresql+psycopg://ai:ai@postgres:5432/ai
      - AGENTIC_MODEL_ID=qwen3:4b
      - AGENTIC_CACHE_ENABLED=true
```

## Testing Configuration

Run the test script to verify your configuration:
```bash
python test_env_config.py
```

This will:
1. Test with custom environment variables
2. Verify correct type conversion (bool, int, float)
3. Test default values when no variables are set
4. Display current configuration