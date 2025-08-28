#!/bin/bash
# CyberPanel Docker Compose Helper Script
# This script provides convenient commands for managing CyberPanel with Docker Compose

set -e

COMPOSE_FILE="docker-compose.dev.yml"

case "$1" in
    "up")
        echo "🚀 Starting CyberPanel with Docker Compose..."
        docker-compose -f $COMPOSE_FILE up --build
        ;;
    "up-d")
        echo "🚀 Starting CyberPanel in detached mode..."
        docker-compose -f $COMPOSE_FILE up --build -d
        ;;
    "down")
        echo "🛑 Stopping CyberPanel..."
        docker-compose -f $COMPOSE_FILE down
        ;;
    "restart")
        echo "🔄 Restarting CyberPanel..."
        docker-compose -f $COMPOSE_FILE restart
        ;;
    "logs")
        echo "📋 Showing CyberPanel logs..."
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    "build")
        echo "🔨 Building CyberPanel Docker image..."
        docker-compose -f $COMPOSE_FILE build --no-cache
        ;;
    "shell")
        echo "🐚 Opening shell in CyberPanel container..."
        docker-compose -f $COMPOSE_FILE exec cyberpanel bash
        ;;
    "db-shell")
        echo "🗄️ Opening MySQL shell..."
        docker-compose -f $COMPOSE_FILE exec db mysql -u cyberpanel -p cyberpanel
        ;;
    "clean")
        echo "🧹 Cleaning up Docker resources..."
        docker-compose -f $COMPOSE_FILE down -v --remove-orphans
        docker system prune -f
        ;;
    "status")
        echo "📊 Docker Compose status:"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    *)
        echo "CyberPanel Docker Compose Helper"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  up       - Start CyberPanel (attached mode)"
        echo "  up-d     - Start CyberPanel (detached mode)"
        echo "  down     - Stop CyberPanel"
        echo "  restart  - Restart CyberPanel"
        echo "  logs     - Show logs"
        echo "  build    - Rebuild Docker image"
        echo "  shell    - Open shell in CyberPanel container"
        echo "  db-shell - Open MySQL shell"
        echo "  clean    - Clean up Docker resources"
        echo "  status   - Show container status"
        echo ""
        echo "Examples:"
        echo "  $0 up-d     # Start in background"
        echo "  $0 logs     # View logs"
        echo "  $0 shell    # Access container"
        ;;
esac
