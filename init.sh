#!/bin/bash

echo "🏗️  Initializing Enhanced Warehouse System..."

# Stop and clean up existing containers
echo "🧹 Cleaning up existing containers..."
docker compose -p warehouse down -v || true
docker rm -f redis warehouse-fastapi-app warehouse-mcp || true

# Build new images
echo "🔨 Building Docker images..."
docker build -t warehouse-fastapi-app:latest -f Dockerfile.fastapi .
docker build -t warehouse-mcp:latest -f Dockerfile.mcp .

# Start services
echo "🚀 Starting services..."
docker compose -p warehouse up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if FastAPI is responding
echo "🔍 Checking service health..."
curl -f http://localhost:8000/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ FastAPI service is healthy"
else
    echo "❌ FastAPI service is not responding"
    exit 1
fi

echo "🎉 Enhanced Warehouse System is ready!"
echo "📊 API Documentation: http://localhost:8000/docs"
echo "🏥 Health Check: http://localhost:8000/health"
echo ""
echo "Available endpoints:"
echo "  👥 Customers: /customers"
echo "  📂 Categories: /categories" 
echo "  📦 Items: /items"
echo "  🛒 Baskets: /baskets"
echo "  📋 Orders: /orders"
echo ""
echo "Sample data has been initialized with:"
echo "  - 4 categories (Electronics, Clothing, Books, Home & Garden)"
echo "  - 6 sample items"
echo ""
echo "🔧 To view logs: docker compose -p warehouse logs -f"
echo "🛑 To stop: docker compose -p warehouse down"