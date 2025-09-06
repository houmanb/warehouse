# Warehouse Management System with MCP Integration

A comprehensive warehouse and inventory management system built with FastAPI, Redis, and Docker. Features a Model Context Protocol (MCP) server for AI-driven conversational interfaces to all warehouse operations.

## Architecture

- **FastAPI Backend** (`app.py`): REST API with comprehensive business logic
- **Redis Database**: High-performance data storage with hash-based entity management  
- **MCP Server** (`mcp_server.py`): JSON-RPC interface for AI assistant integration
- **Docker Containerization**: Multi-service deployment with orchestration

## Features

### Complete Business Entity Management
- **Customer Management**: Full lifecycle with contact information and soft delete
- **Category Hierarchy**: Product organization and classification
- **Inventory Control**: SKU tracking, pricing, stock levels with validation
- **Shopping Baskets**: Persistent cart functionality with automatic quantity management
- **Order Processing**: Status tracking and customer assignment

### Advanced Functionality
- **Automatic Data Initialization**: Sample categories and products on startup
- **Constraint Validation**: Email uniqueness, SKU validation, category references
- **Soft Delete Patterns**: Customer deactivation without data loss
- **Quantity Aggregation**: Smart basket updates for existing items
- **Error Handling**: Comprehensive HTTP status codes and validation messages

## Installation

### Quick Start
```bash
# Complete system initialization
./init.sh
```

### Manual Setup
```bash
# Build Docker images
./build.sh

# Start all services
docker compose -p warehouse up -d

# View logs
docker compose -p warehouse logs -f

# Stop services
docker compose -p warehouse down
```

## API Reference

### Customer Operations
```
POST   /customers              - Create customer
GET    /customers/{id}         - Get customer by ID
GET    /customers              - List all customers
PATCH  /customers/{id}         - Update customer
DELETE /customers/{id}         - Soft delete customer
```

### Category Operations
```
POST   /categories             - Create category
GET    /categories/{id}        - Get category by ID
GET    /categories             - List all categories
```

### Item Operations
```
POST   /items                  - Create item
GET    /items/{id}             - Get item by ID
GET    /items                  - List active items
PATCH  /items/{id}             - Update item
```

### Basket Operations
```
POST   /baskets/{customer_id}/items        - Add item to basket
GET    /baskets/{customer_id}              - Get basket contents
DELETE /baskets/{customer_id}/items/{id}   - Remove item from basket
DELETE /baskets/{customer_id}              - Clear entire basket
```

### Order Operations
```
POST   /orders                 - Create order
GET    /orders/{id}            - Get order by ID
GET    /orders                 - List all orders
PATCH  /orders/{id}            - Update order
DELETE /orders/{id}            - Delete order
```

## MCP Server Integration

The MCP server provides conversational AI interfaces to all warehouse operations:

### Customer Functions
- `create_customer(name, email, phone?, address?)`
- `get_customer(customer_id)`
- `list_customers()`
- `update_customer(customer_id, ...)`
- `delete_customer(customer_id)`

### Inventory Functions
- `create_category(name, description?)`
- `get_category(category_id)`
- `list_categories()`
- `create_item(name, price, stock_quantity, category_id, sku, description?)`
- `get_item(item_id)`
- `list_items()`
- `update_item(item_id, ...)`

### Shopping Functions
- `add_to_basket(customer_id, item_id, quantity)`
- `get_basket(customer_id)`
- `remove_from_basket(customer_id, item_id)`
- `clear_basket(customer_id)`

### Order Functions
- `create_order(customer_name, items[])`
- `get_order(order_id)`
- `list_orders(details?)`
- `update_order(order_id, ...)`
- `delete_order(order_id)`

## Usage Examples

### Natural Language Operations
```
"Create a customer named Alice Smith with email alice@company.com"
"Add 50 wireless headphones to Electronics category, SKU WH-2024, price $79.99"
"Add 2 headphones to Alice's basket"
"Show me Alice's current basket total"
"Create an order for Alice with her current basket items"
```

### Shopping Workflow
1. **Create Customer**: Register new customer with contact details
2. **Browse Catalog**: List available items by category
3. **Add to Basket**: Build shopping cart with quantity management
4. **Review Basket**: View itemized totals and pricing
5. **Place Order**: Convert basket to order or create direct order
6. **Track Status**: Monitor order processing states

## Data Model

### Customer Entity
```json
{
  "customer_id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "555-0123",
  "address": "123 Main St",
  "created_at": "2024-01-01T00:00:00",
  "is_active": true
}
```

### Item Entity
```json
{
  "item_id": 1,
  "name": "Wireless Headphones",
  "description": "Premium wireless headphones",
  "price": 99.99,
  "stock_quantity": 50,
  "category_id": 1,
  "sku": "WH-001",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00"
}
```

### Basket Entity
```json
{
  "basket_id": 1,
  "customer_id": 1,
  "items": [
    {
      "item_id": 1,
      "item_name": "Wireless Headphones",
      "quantity": 2,
      "unit_price": 99.99,
      "total_price": 199.98
    }
  ],
  "total_amount": 199.98,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T01:00:00"
}
```

## Sample Data

The system initializes with:
- **4 Categories**: Electronics, Clothing, Books, Home & Garden
- **6 Sample Items**: Laptop, Smartphone, T-Shirt, Jeans, Python Programming Book, Garden Hose
- **Complete SKU assignments** and realistic pricing

## Configuration

### Environment Variables
```
REDIS_HOST=redis          # Redis server hostname
REDIS_PORT=6379           # Redis server port
API_BASE_URL=http://fastapi-app:8000  # MCP server API endpoint
```

### Service Endpoints
- **FastAPI Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Redis**: localhost:6379

## Business Logic

### Basket Management
- **Quantity Aggregation**: Adding existing items increases quantity
- **Automatic Totaling**: Real-time price calculations with item-level totals
- **Persistence**: Basket state maintained across sessions
- **Validation**: Customer and item existence checks

### Inventory Control
- **SKU Uniqueness**: Prevents duplicate stock codes
- **Category Validation**: Items must reference valid categories
- **Stock Tracking**: Quantity management with update capabilities
- **Soft Item Deletion**: Maintains data integrity

### Order Processing
- **Status Management**: Pending, shipped, cancelled states
- **Customer Association**: Link orders to customer records
- **Item Lists**: Flexible item specification and modification
- **Audit Trail**: Order modification tracking

## Error Handling

The system provides comprehensive error responses:
- **404 Not Found**: Missing entities with descriptive messages
- **400 Bad Request**: Validation failures and constraint violations
- **500 Internal Error**: System failures with logging

## Testing

Run the comprehensive test suite:
```bash
python test_api.py
```

Tests cover:
- All CRUD operations across entities
- Basket workflow scenarios
- Error conditions and edge cases
- Data validation and constraints

## Integration Benefits

- **Conversational AI Control**: Natural language warehouse management
- **Enterprise Integration**: REST API for system connectivity
- **Scalable Architecture**: Docker-based horizontal scaling
- **Data Persistence**: Redis durability and performance
- **Type Safety**: Pydantic model validation
- **Comprehensive Logging**: Operational monitoring and debugging

## License

MIT License - see LICENSE file for details

---

*A practical demonstration of enterprise warehouse management with AI-driven conversational interfaces through MCP protocol integration.*