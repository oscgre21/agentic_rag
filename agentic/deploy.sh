#!/bin/bash

# Script de despliegue para Agentic API con verificación de dependencias PDF

echo "🚀 Iniciando despliegue de Agentic API..."

# Detener contenedores existentes
echo "🛑 Deteniendo contenedores existentes..."
docker-compose down

# Reconstruir la imagen
echo "🔨 Reconstruyendo imagen Docker..."
docker-compose build --no-cache

# Verificar que pypdf está instalado en la imagen
echo "🔍 Verificando instalación de librerías PDF..."
docker-compose run --rm api python -c "
import sys
try:
    import pypdf
    import pdfplumber
    import PyPDF2
    print('✅ Todas las librerías PDF están instaladas correctamente')
    print(f'   - pypdf version: {pypdf.__version__}')
    sys.exit(0)
except ImportError as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Las librerías PDF no están instaladas correctamente"
    exit 1
fi

# Iniciar los servicios
echo "🚀 Iniciando servicios..."
docker-compose up -d

# Esperar a que el servicio esté listo
echo "⏳ Esperando a que el servicio esté listo..."
sleep 5

# Verificar el estado de salud
echo "🏥 Verificando estado de salud de la API..."
curl -f http://localhost:8000/health || {
    echo "❌ La API no está respondiendo correctamente"
    echo "📋 Logs del contenedor:"
    docker-compose logs --tail=50 api
    exit 1
}

echo ""
echo "✅ Despliegue completado exitosamente!"
echo "📍 API disponible en: http://localhost:8000"
echo "📚 Documentación en: http://localhost:8000/docs"
echo ""
echo "📋 Comandos útiles:"
echo "   - Ver logs: docker-compose logs -f api"
echo "   - Detener: docker-compose down"
echo "   - Reiniciar: docker-compose restart api"