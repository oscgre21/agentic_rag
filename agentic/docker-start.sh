#!/bin/bash

# Docker Quick Start Script for Agentic API
# This script helps you quickly start the Agentic API with Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Agentic API Docker Launcher${NC}"
echo "================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Docker is installed
if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose is installed
if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose.${NC}"
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env file from template...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env file created. You can edit it to customize configuration.${NC}"
    else
        echo -e "${YELLOW}⚠️ .env.example not found. Using default configuration.${NC}"
    fi
fi

# Create docs directory if it doesn't exist
if [ ! -d "docs" ]; then
    echo -e "${YELLOW}📁 Creating docs directory for PDF files...${NC}"
    mkdir -p docs
    echo -e "${GREEN}✅ docs/ directory created${NC}"
fi

# Parse command line arguments
ACTION=${1:-up}
DETACHED=""
BUILD=""

case "$ACTION" in
    start|up)
        echo -e "${GREEN}🔧 Starting Agentic API services...${NC}"
        DETACHED="-d"
        ;;
    stop|down)
        echo -e "${YELLOW}🛑 Stopping Agentic API services...${NC}"
        docker-compose down
        echo -e "${GREEN}✅ Services stopped${NC}"
        exit 0
        ;;
    restart)
        echo -e "${YELLOW}🔄 Restarting Agentic API services...${NC}"
        docker-compose down
        DETACHED="-d"
        ;;
    logs)
        echo -e "${GREEN}📋 Showing logs...${NC}"
        docker-compose logs -f ${2:-}
        exit 0
        ;;
    status|ps)
        echo -e "${GREEN}📊 Service status:${NC}"
        docker-compose ps
        exit 0
        ;;
    build)
        echo -e "${GREEN}🔨 Building images...${NC}"
        BUILD="--build"
        DETACHED="-d"
        ;;
    clean)
        echo -e "${RED}⚠️ WARNING: This will delete all data!${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            echo -e "${GREEN}✅ All containers and volumes removed${NC}"
        fi
        exit 0
        ;;
    pull)
        echo -e "${GREEN}⬇️ Pulling latest images...${NC}"
        docker-compose pull
        echo -e "${GREEN}✅ Images updated${NC}"
        exit 0
        ;;
    test)
        echo -e "${GREEN}🧪 Testing API health...${NC}"
        sleep 5
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ API is healthy!${NC}"
            curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo
        else
            echo -e "${RED}❌ API health check failed${NC}"
            echo "Check logs with: ./docker-start.sh logs api"
        fi
        exit 0
        ;;
    help|--help|-h)
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  start, up     Start all services (default)"
        echo "  stop, down    Stop all services"
        echo "  restart       Restart all services"
        echo "  logs [name]   Show logs (optionally for specific service)"
        echo "  status, ps    Show service status"
        echo "  build         Build and start services"
        echo "  clean         Stop and remove all containers and volumes"
        echo "  pull          Pull latest images"
        echo "  test          Test API health"
        echo "  help          Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0              # Start services"
        echo "  $0 logs api     # Show API logs"
        echo "  $0 restart      # Restart all services"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $ACTION${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

# Start services
echo -e "${YELLOW}🐳 Starting Docker Compose...${NC}"
if docker-compose up $DETACHED $BUILD; then
    if [ -n "$DETACHED" ]; then
        echo -e "${GREEN}✅ Services started successfully!${NC}"
        echo ""
        echo "📍 Service URLs:"
        echo "   - API: http://localhost:8000"
        echo "   - API Health: http://localhost:8000/health"
        echo "   - API Docs: http://localhost:8000/docs"
        echo "   - Ollama: http://localhost:11434"
        echo "   - PostgreSQL: localhost:5532"
        echo ""
        echo "📝 Quick commands:"
        echo "   - View logs: ./docker-start.sh logs"
        echo "   - Stop services: ./docker-start.sh stop"
        echo "   - Test API: ./docker-start.sh test"
        echo ""
        echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
        
        # Wait for services
        MAX_ATTEMPTS=30
        ATTEMPT=0
        while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
            if curl -f http://localhost:8000/health >/dev/null 2>&1; then
                echo -e "${GREEN}✅ API is ready!${NC}"
                break
            fi
            echo -n "."
            sleep 2
            ATTEMPT=$((ATTEMPT + 1))
        done
        
        if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            echo -e "\n${YELLOW}⚠️ API is taking longer to start. Check logs: ./docker-start.sh logs api${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Failed to start services${NC}"
    echo "Check logs for errors: docker-compose logs"
    exit 1
fi