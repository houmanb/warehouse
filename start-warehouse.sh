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
    echo "  (no args)  - Initialize complete system (like old init.sh)"
    echo "  build      - Build all Docker images"
    echo "  start      - Start system with Mesa visualization"
    echo "  basic      - Start basic system only (no Mesa agents)"
    echo "  headless   - Start system with headless simulation"
    echo "  stop       - Stop all services"
    echo "  clean      - Stop services and remove containers"
    echo "  logs       - Show logs from all services"
    echo "  status     - Show status of all services"
    echo ""
    echo "After starting, services are available at:"
    echo "  📊 API Documentation: http://localhost:8000/docs"
    echo "  🏥 Health Check: http://localhost:8000/health"
    echo "  📊 Mesa Visualization: http://localhost:8521 (when enabled)"
    echo "  🗃️  Redis: localhost:6379"
}

# Build all Docker images
build_images() {
    echo "🏗️  Building Docker images..."
    
    # echo "📦 Building FastAPI app..."
    # docker build --no-cache -t warehouse-fastapi-app:latest -f Dockerfile.fastapi .
    
    # echo "🔗 Building MCP server..."
    # docker build --no-cache -t warehouse-mcp:latest -f Dockerfile.mcp .
    
    # echo "🤖 Building Mesa agent simulation..."
    # docker build --no-cache -t warehouse-mesa:latest -f Dockerfile.mesa .

    echo "📦 Building FastAPI app..."
    docker build -t warehouse-fastapi-app:latest -f Dockerfile.fastapi .
    
    echo "🔗 Building MCP server..."
    docker build -t warehouse-mcp:latest -f Dockerfile.mcp .
    
    echo "🤖 Building Mesa agent simulation..."
    docker build -t warehouse-mesa:latest -f Dockerfile.mesa .


    # Verify Mesa version
    echo "🔍 Verifying Mesa version..."
    MESA_VERSION=$(docker run --rm warehouse-mesa:latest pip show mesa | grep Version | awk '{print $2}')
    if [[ "$MESA_VERSION" == 3.* ]]; then
        echo "✅ Mesa version $MESA_VERSION (3.x) installed"
    else
        echo "❌ Expected Mesa version >=3.1.0, but found $MESA_VERSION"
        exit 1
    fi
    
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

# Initialize complete system (default behavior - replaces old init.sh)
init_system() {
    echo "🏗️  Initializing Enhanced Warehouse System..."
    
    # Stop and clean up existing containers
    echo "🧹 Cleaning up existing containers..."
    docker compose -p warehouse down -v || true
    
    # Clean up any remaining containers (check if they exist first)
    for container in redis warehouse-fastapi-app warehouse-mcp warehouse-mesa; do
        if docker ps -a --format "table {{.Names}}" | grep -q "^${container}$"; then
            echo "Removing container: ${container}"
            docker rm -f "${container}"
        fi
    done
    
    # Build new images
    echo "🔨 Building Docker images..."
    build_images
    
    # Start services with Mesa visualization
    echo "🚀 Starting services..."
    docker compose -p warehouse up -d redis fastapi-app mcp mesa-simulation
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to start..."
    sleep 15
    
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
    echo "🤖 Mesa Visualization: http://localhost:8521"
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
    echo "  - 5 customer agents placing orders"
    echo "  - 2 fulfillment agents processing orders"
    echo ""
    echo "🔧 To view logs: $0 logs"
    echo "🛑 To stop: $0 stop"
    echo "📊 To view agent simulation: http://localhost:8521"
}

# Start basic system only (no Mesa agents)
start_basic() {
    echo "🚀 Starting basic warehouse system (no agents)..."
    docker compose -p warehouse up -d redis fastapi-app mcp
    echo ""
    echo "✅ Basic system started! Services available at:"
    echo "   🔗 FastAPI App: http://localhost:8000"
    echo "   📊 API Docs: http://localhost:8000/docs"
    echo "   🗃️  Redis: localhost:6379"
}

# Start complete system
start_system() {
    echo "🚀 Starting warehouse system with visualization..."
    docker compose -p warehouse up -d redis fastapi-app mcp mesa-simulation
    echo ""
    echo "✅ System started! Services available at:"
    echo "   📊 Mesa Visualization: http://localhost:8521"
    echo "   🔗 FastAPI App: http://localhost:8000"
    echo "   🗃️  Redis: localhost:6379"
    echo ""
    echo "📋 To view logs: $0 logs"
    echo "🛑 To stop: $0 stop"
}

# Start with headless simulation
start_headless() {
    echo "🤖 Starting warehouse system with headless simulation..."
    docker compose -p warehouse --profile headless up -d
    echo ""
    echo "✅ System started with headless simulation!"
    echo "   🔗 FastAPI App: http://localhost:8000"
    echo "   🤖 Mesa agents running in background"
}

# Stop services
stop_services() {
    echo "🛑 Stopping warehouse services..."
    docker compose -p warehouse down
    echo "✅ All services stopped"
}

# Clean up
clean_system() {
    echo "🧹 Cleaning up warehouse system..."
    docker compose -p warehouse down -v --remove-orphans
    
    # Clean up any remaining containers (check if they exist first)
    for container in redis warehouse-fastapi-app warehouse-mcp warehouse-mesa; do
        if docker ps -a --format "table {{.Names}}" | grep -q "^${container}$"; then
            echo "Removing container: ${container}"
            docker rm -f "${container}"
        fi
    done
    
    echo "✅ System cleaned (containers and volumes removed)"
}

# Show logs
show_logs() {
    echo "📋 Showing service logs..."
    docker compose -p warehouse logs -f
}

# Show status
show_status() {
    echo "📊 Service Status:"
    docker compose -p warehouse ps
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
    if docker compose -p warehouse exec -T redis redis-cli ping > /dev/null 2>&1; then
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