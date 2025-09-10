#!/bin/bash

# Script para construir y ejecutar la imagen Docker de Agentic API

set -e

echo "🚀 Building Agentic API Docker image..."

# Build the Docker image
docker build -t agentic-api:latest .

echo "✅ Docker image built successfully!"
echo ""
echo "📋 Para ejecutar la aplicación:"
echo ""
echo "1. Con docker-compose (recomendado):"
echo "   docker-compose up -d"
echo ""
echo "2. Con docker run:"
echo "   docker run -d \\"
echo "     --name agentic-api \\"
echo "     -p 8000:8000 \\"
echo "     -v \$(pwd)/docs:/home/appuser/app/docs \\"
echo "     -e AGENTIC_DB_URL='postgresql+psycopg://ai:ai@host.docker.internal:5532/ai' \\"
echo "     -e OLLAMA_HOST='http://host.docker.internal:11434' \\"
echo "     --add-host host.docker.internal:host-gateway \\"
echo "     agentic-api:latest"
echo ""
echo "📚 Documentación disponible en:"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Health Check: http://localhost:8000/health"