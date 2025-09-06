#!/bin/bash

# Warehouse System Startup Script

set -e

echo "🏪 Warehouse Agent Simulation System"
echo "==================================="

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build     - Build all Docker images"
    echo "  start     - Start the complete system with visualization"
    echo "  headless  - Start system with headless simulation"
    echo "  stop      - Stop all services"
    echo "  clean     - Stop services and remove containers"
    echo "  logs      - Show logs from all services"
    echo "  status    - Show status of all services"
    echo ""
    echo "After starting, services are available at:"
    echo "  - FastAPI App: http://localhost:8000"
    echo "  - Mesa Visualization: http://localhost:8521"
    echo "  - Redis: localhost:6379"
}

# Build all Docker images
build_images() {
    echo "🏗️  Building Docker images..."
    
    echo "📦 Building FastAPI app..."
    docker build --no-cache --pull -t warehouse-fastapi-app:latest -f Dockerfile.fastapi .
    
    echo "🔗 Building MCP server..."
    docker build --no-cache --pull -t warehouse-mcp:latest -f Dockerfile.mcp .
    
    echo "🤖 Building Mesa agent simulation..."
    docker build --no-cache --pull -t warehouse-mesa:latest -f Dockerfile.mesa .
    
    echo "✅ All images built successfully!"
    echo ""
    echo "🚀 To start the complete warehouse system:"
    echo "   $0"
    echo ""
    echo "📊 Services will be available at:"
    echo "   - FastAPI App: http://localhost:8000"
    echo "   - Mesa Visualization: http://localhost:8521"
    echo "   - Redis: localhost:6379"
}

# Start complete system
start_system() {
    echo "🚀 Starting warehouse system with visualization..."
    docker-compose up -d redis fastapi-app mcp mesa-simulation
    echo ""
    echo "✅ System started! Services available at:"
    echo "   📊 Mesa Visualization: http://localhost:8521"
    echo "   🔗 FastAPI App: http://localhost:8000"
    echo "   🗃️  Redis: localhost:6379"
    echo ""
    echo "📋 To view logs: ./start-warehouse.sh logs"
    echo "🛑 To stop: ./start-warehouse.sh stop"
}

# Start with headless simulation
start_headless() {
    echo "🤖 Starting warehouse system with headless simulation..."
    docker-compose --profile headless up -d
    echo ""
    echo "✅ System started with headless simulation!"
    echo "   🔗 FastAPI App: http://localhost:8000"
    echo "   🤖 Mesa agents running in background"
}

# Stop services
stop_services() {
    echo "🛑 Stopping warehouse services..."
    docker-compose down
    echo "✅ All services stopped"
}

# Clean up
clean_system() {
    echo "🧹 Cleaning up warehouse system..."
    docker-compose down -v --remove-orphans
    echo "✅ System cleaned (containers and volumes removed)"
}

# Show logs
show_logs() {
    echo "📋 Showing service logs..."
    docker-compose logs -f
}

# Show status
show_status() {
    echo "📊 Service Status:"
    docker-compose ps
    echo ""
    echo "🔍 Health Checks:"
    
    # Test FastAPI
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ FastAPI App: Healthy"
    else
        echo "❌ FastAPI App: Not responding"
    fi
    
    # Test Mesa visualization
    if curl -s http://localhost:8521 > /dev/null 2>&1; then
        echo "✅ Mesa Visualization: Running"
    else
        echo "❌ Mesa Visualization: Not responding"
    fi
    
    # Test Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis: Connected"
    else
        echo "❌ Redis: Not responding"
    fi
}

# Main command handling
case "$1" in
    ""|init)
        init_system
        ;;
    build)
        build_images
        ;;
    start)
        start_system
        ;;
    basic)
        start_basic
        ;;
    headless)
        start_headless
        ;;
    stop)
        stop_services
        ;;
    clean)
        clean_system
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    *)
        show_help
        ;;
esac