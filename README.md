# Warehouse Management System

A state machine-based warehouse management system built with FastAPI, Redis, and Docker. Features order processing workflows, role-based permissions, and AI assistant integration through Model Context Protocol (MCP).

## Architecture

- **FastAPI Backend** (`app.py`): REST API with state machine order processing
- **Redis Database**: High-performance data storage and task queuing
- **MCP Server** (`mcp_server.py`): AI-friendly JSON-RPC interface
- **Python Client** (`warehouse_client.py`): Programmatic API access
- **Docker Containerization**: Multi-service deployment

## Order Workflow

Orders progress through a state machine with role-based transitions:

```
📋 Pending → ✅ Confirmed → 🔍 Picking → 📦 Packed → 🚚 Shipped → ✅ Delivered
                                                         ↓
                                                    ❌ Cancelled (any stage)
                                                         ↓  
                                                    🔄 Returned (from delivered)
```

### Role Permissions

**Customer Role:**
- Create orders
- Cancel orders (from pending, confirmed, picking, packed states)
- Return delivered orders

**Fulfillment Role:**
- Confirm pending orders
- Progress orders through workflow (picking → packed → shipped → delivered)
- Halt/resume orders for exceptions

## Quick Start

### Start Core Services

```bash
# Start warehouse API and Redis
docker compose up -d redis warehouse-api

# Verify services are running
curl http://localhost:8000/health
```

### Run Tests

```bash
# Run all tests
docker compose --profile test up all-tests

# Run specific test suites

# HTTP API tests
docker compose --profile test up workflow-tests

# Python client tests
docker compose --profile test up client-tests     

# Quick health check
docker compose --profile test up smoke-tests       
```

### Start AI Integration

```bash
# Start MCP server for Claude/AI integration
docker compose up -d mcp-server

# Check MCP server health
curl http://localhost:8000/health
```

### Optional: Start Simulation

```bash
# Start Mesa agent simulation with visualization
docker compose --profile simulation up mesa-simulation

# Access simulation dashboard
open http://localhost:8521
```

## API Endpoints

### Core Operations

```http
GET  /health                           # API health check
GET  /state-machine/info               # State machine configuration
POST /orders                           # Create order
GET  /orders/{order_id}                # Get order details  
GET  /orders                           # List orders
POST /orders/{order_id}/transition     # Request state transition
```

### Queue Management

```http
POST /queue/claim?agent_id=...         # Claim next task
POST /queue/complete                   # Complete claimed task
POST /queue/release?agent_id=...       # Release task back to queue
GET  /queue/status                     # Get queue status
```

### Role-Based Access

All requests require the `X-AGENT-ROLE` header:

```bash
# Customer requests
curl -H "X-AGENT-ROLE: customer" http://localhost:8000/orders

# Fulfillment requests  
curl -H "X-AGENT-ROLE: fulfillment" http://localhost:8000/orders
```

## Usage Examples

### Create and Process Order

```bash
# Customer creates order
curl -X POST "http://localhost:8000/orders" \
  -H "X-AGENT-ROLE: customer" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "items": ["Laptop", "Mouse", "Keyboard"],
    "notes": "Urgent order"
  }'

# Fulfillment confirms order
curl -X POST "http://localhost:8000/orders/{ORDER_ID}/transition" \
  -H "X-AGENT-ROLE: fulfillment" \
  -H "Content-Type: application/json" \
  -d '{
    "transition": "confirm",
    "agent_id": "fulfillment-001",
    "notes": "Order confirmed by warehouse"
  }'

# Process the queued task
curl -X POST "http://localhost:8000/queue/claim?agent_id=fulfillment-001" \
  -H "X-AGENT-ROLE: fulfillment"

curl -X POST "http://localhost:8000/queue/complete" \
  -H "X-AGENT-ROLE: fulfillment" \
  -d "task_id=TASK_ID&agent_id=fulfillment-001"
```

### Using Python Client

```python
from warehouse_client import create_customer_client, create_fulfillment_client

# Customer workflow
customer = create_customer_client("http://localhost:8000")
order = customer.create_order("Alice Smith", ["Widget A", "Widget B"], "Test order")
order_id = order["order_id"]

# Fulfillment workflow
fulfillment = create_fulfillment_client("http://localhost:8000")
fulfillment.confirm_order(order_id, "Processing order")

# Process task automatically
result = fulfillment.process_next_task("agent-001")
print(f"Order now in state: {result['result']['new_state']}")
```

## Development Commands

### Service Management

```bash
# Start core services
docker compose up -d redis warehouse-api

# Start all services including simulation and MCP
docker compose --profile simulation up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f warehouse-api
```

### Testing

```bash
# Run workflow tests (HTTP API)
docker compose --profile test up workflow-tests

# Run client library tests
docker compose --profile test up client-tests

# Run all tests together
docker compose --profile test up all-tests

# Quick smoke test
docker compose --profile test up smoke-tests

# Continuous testing during development
docker compose --profile test up -d all-tests
docker compose logs -f all-tests
```

### Building and Cleanup

```bash
# Rebuild all images
docker compose build --no-cache

# Clean restart
docker compose down -v
docker compose up -d redis warehouse-api

# Remove all containers and volumes
docker compose down -v --remove-orphans
```

## Service Endpoints

- **Warehouse API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **MCP Server**: http://localhost:8001 (when enabled)
- **Mesa Simulation**: http://localhost:8521 (when enabled)
- **Redis**: localhost:6379

## Project Structure

```
warehouse-project/
├── app.py                     # FastAPI backend with state machine
├── warehouse_client.py        # Python client library
├── mcp_server.py             # AI assistant integration
├── requirements-fastapi.txt   # Main app dependencies
├── requirements-mcp.txt      # MCP server dependencies
├── docker-compose.yml        # Service orchestration
├── test_warehouse_workflow.py # HTTP API tests
├── Dockerfile.fastapi        # Main app container
├── Dockerfile.mcp           # MCP server container
└── README.md                # This file
```

## Configuration

### Environment Variables

```bash
# Redis configuration
REDIS_HOST=redis
REDIS_PORT=6379

# MCP server configuration  
API_BASE_URL=http://warehouse-api:8000
AGENT_ROLE=fulfillment
CONTAINER_MODE=true

# Simulation configuration (optional)
WAREHOUSE_URL=http://warehouse-api:8000
NUM_CUSTOMERS=20
NUM_FULFILLMENT_AGENTS=10
SIMULATION_SPEED_FACTOR=0.05
```

## AI Integration

The system includes an MCP (Model Context Protocol) server that allows AI assistants like Claude to interact with the warehouse system through natural language:

```
"Create an order for John with laptop and mouse"
"Show me all pending orders"  
"Advance order 123 to the next stage"
"What's the status of order 456?"
"Process the next fulfillment task"
```

## Testing Strategy

The project includes comprehensive tests:

- **Workflow Tests** (`test_warehouse_workflow.py`): Direct HTTP API testing with role validation
- **Client Tests** (`test_warehouse_client.py`): Python client library testing with convenience methods
- **Integration Tests**: End-to-end workflows from order creation to delivery
- **Error Handling**: Permission validation, invalid transitions, edge cases

## Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check if ports are available
lsof -i :8000
lsof -i :6379

# Check service health
docker compose ps
curl http://localhost:8000/health
```

**Tests failing:**
```bash
# Ensure services are healthy before testing
docker compose up -d redis warehouse-api
docker compose ps  # All should show "healthy"

# Run tests with verbose output
docker compose --profile test up workflow-tests
```

**Permission errors:**
- Ensure all requests include the correct `X-AGENT-ROLE` header
- Check that the role has permission for the requested transition
- Verify order is in the correct state for the transition

### Development Tips

- Use `docker compose logs -f SERVICE_NAME` to debug issues
- The API documentation at `/docs` shows all available endpoints
- Check queue status with `GET /queue/status` to see pending tasks
- Use the Python client for easier programmatic access

## License

MIT License - see LICENSE file for details

---

*A state machine-based warehouse management system with AI integration for modern logistics operations.*
