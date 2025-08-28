#!/bin/bash

# CyberPanel Development Setup Script
# This script sets up CyberPanel in Docker development mode

set -euo pipefail

echo "🚀 Setting up CyberPanel Development Environment with Docker"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs media staticfiles

# Build and start the containers
echo "🏗️ Building and starting Docker containers..."
docker-compose -f docker-compose.dev.yml up --build -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py migrate

# Collect static files
echo "📦 Collecting static files..."
docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py collectstatic --noinput

# Create superuser (optional)
echo "👤 Do you want to create a Django superuser? (y/n)"
read -r create_superuser
if [[ $create_superuser =~ ^[Yy]$ ]]; then
    echo "Creating Django superuser..."
    docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py createsuperuser
fi

echo ""
echo "🎉 CyberPanel development environment is ready!"
echo ""
echo "🌐 Access points:"
echo "   - CyberPanel: http://localhost:8000"
echo "   - phpMyAdmin: http://localhost:8080"
echo "   - Database: localhost:3306"
echo ""
echo "📋 Useful commands:"
echo "   - Start: docker-compose -f docker-compose.dev.yml up -d"
echo "   - Stop: docker-compose -f docker-compose.dev.yml down"
echo "   - Logs: docker-compose -f docker-compose.dev.yml logs -f"
echo "   - Shell: docker-compose -f docker-compose.dev.yml exec cyberpanel bash"
echo "   - Django shell: docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py shell"
echo ""
echo "⚠️  Remember to change the SECRET_KEY in production!"
echo "⚠️  Remember to change database passwords in production!"
