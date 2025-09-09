#!/bin/bash

# Script para construir y verificar la imagen Docker de Agentic API

echo "🔨 Construyendo imagen Docker de Agentic API..."

# Construir la imagen
docker build -t agentic-api:latest .

if [ $? -eq 0 ]; then
    echo "✅ Imagen construida exitosamente"
    
    echo "📦 Verificando instalación de pypdf en la imagen..."
    docker run --rm agentic-api:latest python -c "import pypdf; print(f'✅ pypdf version: {pypdf.__version__}')"
    
    echo "📦 Verificando otras librerías PDF..."
    docker run --rm agentic-api:latest python -c "import pdfplumber, PyPDF2; print('✅ pdfplumber y PyPDF2 instalados correctamente')"
    
    echo "📋 Información de la imagen:"
    docker images agentic-api:latest
else
    echo "❌ Error al construir la imagen"
    exit 1
fi