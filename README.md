# Enhanced Warehouse Management System with Order Timeline Tracking

A comprehensive warehouse and inventory management system built with FastAPI, Redis, and Docker. Features advanced order tracking with complete timestamp audit trails and fulfillment workflow management through a Model Context Protocol (MCP) server for AI-driven conversational interfaces.

## 🆕 New Features: Order Timeline Tracking

### Advanced Order Management
- **Complete Timestamp Tracking**: Every order state change is recorded with precise timestamps
- **Fulfillment Workflow**: Automated progression through order statuses (pending → confirmed → picking → packed → shipped → delivered)
- **Status History**: Full audit trail of all status changes with optional notes
- **Workflow Automation**: Simple advancement through predefined fulfillment stages
- **Timeline API**: Dedicated endpoints for viewing complete order timelines

### Order Status Workflow
```
📅 Pending → ✅ Confirmed → 🔍 Picking → 📦 Packed → 🚚 Shipped → ✅ Delivered
                                                              ↓
                                                         ❌ Cancelled (any stage)
```

Each status change automatically records:
- **Timestamp**: Precise ISO 8601 datetime
- **Status Change**: From/to status tracking
- **Notes**: Optional context about the change
- **Fulfillment Milestone**: Specific workflow timestamps

## Architecture

- **FastAPI Backend** (`app.py`): Enhanced REST API with timestamp tracking
- **Redis Database**: High-performance data storage with order history management  
- **MCP Server** (`mcp_server.py`): AI-friendly JSON-RPC interface with timeline support
- **Docker Containerization**: Multi-service deployment with orchestration

## Enhanced API Reference

### Order Operations with Timestamps

#### Create Order (Enhanced)
```http
POST /orders
Content-Type: application/json

{
  "customer_name": "John Doe",
  "items": ["Laptop", "Mouse", "Keyboard"],
  "notes": "Urgent order - customer requested expedited processing"
}
```

**Response includes:**
- `created_at`: Order creation timestamp
- `placed_at`: When order was initially placed
- `status_history`: Array of status changes
- All fulfillment workflow timestamps

#### Get Order Timeline
```http
GET /orders/{order_id}/timeline
```

**Returns comprehensive timeline:**
```json
{
  "order_id": 123,
  "customer_name": "John Doe",
  "current_status": "shipped",
  "created_at": "2024-01-01T10:00:00Z",
  "status_changes": [
    {
      "status": "pending",
      "timestamp": "2024-01-01T10:00:00Z",
      "notes": "Order created"
    },
    {
      "status": "confirmed",
      "timestamp": "2024-01-01T10:15:00Z",
      "notes": "Order confirmed by warehouse team"
    }
  ],
  "fulfillment_timestamps": {
    "placed_at": "2024-01-01T10:00:00Z",
    "confirmed_at": "2024-01-01T10:15:00Z",
    "picked_at": "2024-01-01T11:30:00Z",
    "packed_at": "2024-01-01T12:00:00Z",
    "shipped_at": "2024-01-01T14:00:00Z",
    "delivered_at": null,
    "cancelled_at": null
  }
}
```

#### Advance Order Workflow
```http
POST /orders/{order_id}/advance?notes=Items%20picked%20from%20shelf%20A-1
```

Automatically advances order to next status:
- `pending` → `confirmed`
- `confirmed` → `picking`
- `picking` → `packed`
- `packed` → `shipped`
- `shipped` → `delivered`

#### Update Order Status (Manual)
```http
PATCH /orders/{order_id}
Content-Type: application/json

{
  "status": "shipped",
  "notes": "Package shipped via FedEx, tracking: 1234567890"
}
```

Manually set status with automatic timestamp tracking.

### Enhanced Order Model

```python
class OrderOut(BaseModel):
    order_id: int
    customer_name: str
    items: List[str]
    status: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str
    status_history: List[OrderStatusHistory]
    # Fulfillment workflow timestamps
    placed_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    picked_at: Optional[str] = None
    packed_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    cancelled_at: Optional[str] = None

class OrderStatusHistory(BaseModel):
    status: str
    timestamp: str
    notes: Optional[str] = None
```

## Enhanced MCP Server Integration

### New Order Timeline Functions

#### Advanced Order Management
- `create_order(customer_name, items[], notes?)` - Create with notes tracking
- `get_order(order_id)` - Get with complete timeline details
- `advance_order(order_id, notes?)` - Advance through workflow
- `get_order_timeline(order_id)` - Get detailed timeline view
- `update_order(order_id, status?, notes?, ...)` - Update with change tracking

### Natural Language Examples

```
"Create an urgent order for Alice with laptop and mouse"
"Show me the complete timeline for order 123"
"Advance order 456 to the next stage with note 'items picked'"
"What's the delivery status of order 789?"
"Mark order 234 as shipped with tracking number ABC123"
"List all orders shipped today with full details"
```

## Installation & Quick Start

### Complete System Setup
```bash
# Initialize enhanced system
./init.sh

# Or manual setup
./build.sh
docker compose -p warehouse up -d
```

### Test Enhanced Functionality
```bash
# Run comprehensive test suite including timeline tests
python test_api.py
```

## Enhanced Usage Examples

### Complete Order Workflow
```python
import requests

base_url = "http://localhost:8000"

# 1. Create order with notes
order_data = {
    "customer_name": "Alice Smith",
    "items": ["Laptop", "Wireless Mouse"],
    "notes": "Customer requested expedited processing"
}
response = requests.post(f"{base_url}/orders", json=order_data)
order_id = response.json()["order_id"]

# 2. Advance through workflow stages
stages = [
    ("Order confirmed by warehouse", "confirmed"),
    ("Items picked from inventory", "picking"),
    ("Items packed for shipping", "packed"),
    ("Package shipped via FedEx", "shipped")
]

for note, expected_status in stages:
    response = requests.post(
        f"{base_url}/orders/{order_id}/advance",
        params={"notes": note}
    )
    print(f"Advanced to: {response.json()['message']}")

# 3. Get complete timeline
response = requests.get(f"{base_url}/orders/{order_id}/timeline")
timeline = response.json()

print(f"Order {order_id} Timeline:")
for change in timeline['status_changes']:
    print(f"  {change['status']}: {change['timestamp']}")
    if change['notes']:
        print(f"    Note: {change['notes']}")
```

### Timeline Analysis
```python
# Get all orders with timestamps
response = requests.get(f"{base_url}/orders")
orders = response.json()

# Find orders shipped today
from datetime import datetime, date
today = date.today()

shipped_today = []
for order in orders:
    if order.get('shipped_at'):
        ship_date = datetime.fromisoformat(order['shipped_at']).date()
        if ship_date == today:
            shipped_today.append(order)

print(f"Orders shipped today: {len(shipped_today)}")
```

## Data Persistence & Storage

### Order Timeline Storage in Redis

```
# Order data
order:123 -> hash {order_id, customer_name, status, created_at, updated_at, ...timestamps}

# Status history (ordered list)
order_history:123 -> list [
  {"status": "pending", "timestamp": "...", "notes": "..."},
  {"status": "confirmed", "timestamp": "...", "notes": "..."}
]

# Order index
orders -> set {123, 124, 125, ...}
```

## Operational Benefits

### Enhanced Visibility
- **Real-time Tracking**: Know exactly where every order stands
- **Performance Metrics**: Measure time between workflow stages
- **Audit Compliance**: Complete change history for accountability
- **Customer Communication**: Precise delivery estimates based on workflow position

### Process Optimization
- **Bottleneck Identification**: Find slow stages in fulfillment
- **SLA Monitoring**: Track against service level agreements
- **Workflow Efficiency**: Optimize based on historical timing data
- **Predictive Analytics**: Forecast delivery times using past patterns

## API Response Examples

### Enhanced Order Creation Response
```json
{
  "order_id": 123,
  "customer_name": "Alice Smith",
  "items": ["Laptop", "Wireless Mouse"],
  "status": "pending",
  "notes": "Customer requested expedited processing",
  "created_at": "2024-01-01T10:00:00.000Z",
  "updated_at": "2024-01-01T10:00:00.000Z",
  "placed_at": "2024-01-01T10:00:00.000Z",
  "status_history": [
    {
      "status": "pending",
      "timestamp": "2024-01-01T10:00:00.000Z",
      "notes": "Order created"
    }
  ],
  "confirmed_at": null,
  "picked_at": null,
  "packed_at": null,
  "shipped_at": null,
  "delivered_at": null,
  "cancelled_at": null
}
```

### Order Advancement Response
```json
{
  "message": "Order advanced to confirmed",
  "order": {
    "order_id": 123,
    "customer_name": "Alice Smith",
    "items": ["Laptop", "Wireless Mouse"],
    "status": "confirmed",
    "notes": "Customer requested expedited processing",
    "created_at": "2024-01-01T10:00:00.000Z",
    "updated_at": "2024-01-01T10:15:00.000Z",
    "placed_at": "2024-01-01T10:00:00.000Z",
    "confirmed_at": "2024-01-01T10:15:00.000Z",
    "status_history": [
      {
        "status": "pending",
        "timestamp": "2024-01-01T10:00:00.000Z",
        "notes": "Order created"
      },
      {
        "status": "confirmed",
        "timestamp": "2024-01-01T10:15:00.000Z",
        "notes": "Order confirmed by warehouse team"
      }
    ]
  }
}
```

## Testing & Validation

### Comprehensive Test Suite
The enhanced test suite (`test_api.py`) includes:

- **Timeline Accuracy**: Verify timestamps are recorded correctly
- **Workflow Progression**: Test automatic status advancement
- **History Tracking**: Validate status change audit trail
- **Edge Cases**: Test error conditions and boundary cases
- **Performance**: Measure API response times with timeline data

### Key Test Scenarios
1. **Order Lifecycle**: Create → Advance → Complete → Analyze
2. **Concurrent Orders**: Multiple orders progressing simultaneously  
3. **Status Rollbacks**: Manual status changes and their tracking
4. **Timeline Queries**: Retrieve and analyze historical data
5. **Error Handling**: Invalid transitions and missing orders

## Configuration

### Environment Variables
```bash
REDIS_HOST=redis              # Redis server hostname
REDIS_PORT=6379               # Redis server port  
API_BASE_URL=http://fastapi-app:8000  # MCP server API endpoint
```

### Service Endpoints
- **FastAPI Application**: http://localhost:8000
- **Enhanced API Documentation**: http://localhost:8000/docs
- **Order Timeline API**: http://localhost:8000/orders/{id}/timeline
- **Health Check**: http://localhost:8000/health

## Migration from Previous Version

### Upgrading Existing Orders
The system automatically handles existing orders:
- **Legacy orders** get `created_at` timestamps backfilled
- **Status history** is initialized with current status
- **Workflow timestamps** start tracking from first status change
- **No data loss** during upgrade process

### Backward Compatibility
- All existing API endpoints remain functional
- Previous order format is still supported
- Enhanced fields are optional in responses
- MCP server maintains existing function signatures

## License

MIT License - see LICENSE file for details

---

*An enterprise-grade warehouse management system with comprehensive order tracking, AI-driven conversational interfaces, and complete audit trails for modern logistics operations.*

# 🚀 Complete Deployment Guide: Enhanced Warehouse System with Order Timeline Tracking

## 📋 **Files to Update**

You need to replace these files in your project directory:

### 1. **Replace `app.py`**
Use the "Complete Enhanced app.py" artifact above - this includes:
- ✅ Enhanced order models with timestamps
- ✅ Status history tracking 
- ✅ Fulfillment workflow timestamps
- ✅ New `/orders/{id}/advance` endpoint
- ✅ New `/orders/{id}/timeline` endpoint
- ✅ All existing endpoints (customers, categories, items, baskets)

### 2. **Replace `mcp_server.py`**
Use the "Enhanced MCP Server with Order Timeline Support" artifact above - this includes:
- ✅ Complete timeline support in MCP responses
- ✅ Enhanced order advancement with notes
- ✅ Detailed order timeline queries  
- ✅ Rich timestamp formatting
- ✅ Comprehensive status change tracking

## 🔄 **Deployment Steps**

### **Step 1: Update Files**
```bash
# Backup your current files (optional but recommended)
cp app.py app.py.backup
cp mcp_server.py mcp_server.py.backup

# Replace with the enhanced versions from the artifacts above
# Copy the complete content from the artifacts into your files
```

### **Step 2: Deploy Enhanced System**
```bash
# Stop current system
docker compose -p warehouse down

# Clean up old containers and images 
docker rm -f $(docker ps -aq --filter "name=warehouse") 2>/dev/null || true
docker rmi warehouse-fastapi-app:latest warehouse-mcp:latest 2>/dev/null || true

# Build new images with enhanced code
docker build --no-cache -t warehouse-fastapi-app:latest -f Dockerfile.fastapi .
docker build --no-cache -t warehouse-mcp:latest -f Dockerfile.mcp .

# Start enhanced system
docker compose -p warehouse up -d

# Wait for startup
sleep 15
```

### **Step 3: Verify Deployment**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test categories endpoint (this was failing before)
curl http://localhost:8000/categories

# Test enhanced order creation
curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Timeline Test Customer",
    "items": ["Test Product A", "Test Product B"],
    "notes": "Testing enhanced order timeline functionality"
  }'

# Get the order ID from the response and test timeline
# Replace {ORDER_ID} with actual ID from previous response
curl "http://localhost:8000/orders/{ORDER_ID}/timeline"

# Test order advancement  
curl -X POST "http://localhost:8000/orders/{ORDER_ID}/advance" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Testing workflow advancement"}'
```

## 🧪 **Testing Enhanced Features**

### **Test Order Workflow Progression**
```bash
# Create test order
ORDER_RESPONSE=$(curl -s -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Workflow Test Customer",
    "items": ["Laptop", "Mouse", "Keyboard"],
    "notes": "Testing complete workflow progression"
  }')

# Extract order ID
ORDER_ID=$(echo "$ORDER_RESPONSE" | jq -r '.order_id')
echo "Created order: $ORDER_ID"

# Test progression through all stages
echo "Advancing to confirmed..."
curl -s -X POST "http://localhost:8000/orders/$ORDER_ID/advance" \
  -d "notes=Order confirmed by warehouse team"

echo "Advancing to picking..."
curl -s -X POST "http://localhost:8000/orders/$ORDER_ID/advance" \
  -d "notes=Items being picked from inventory"

echo "Advancing to packed..."
curl -s -X POST "http://localhost:8000/orders/$ORDER_ID/advance" \
  -d "notes=Items packed and ready for shipping"

echo "Advancing to shipped..."
curl -s -X POST "http://localhost:8000/orders/$ORDER_ID/advance" \
  -d "notes=Package shipped via FedEx"

# View complete timeline
echo "Final timeline:"
curl -s "http://localhost:8000/orders/$ORDER_ID/timeline" | jq .
```

### **Test MCP Integration**
If you have the MCP server configured, test these commands:
```
"Create an order for Alice with laptop and mouse, note it's urgent"
"Show me the timeline for order 1"
"Advance order 1 to the next stage"
"What's the status of all orders with details?"
"Get the complete timeline for order 1"
```

## 📊 **New API Endpoints Available**

### **Enhanced Order Endpoints**

#### Create Order with Notes
```http
POST /orders
{
  "customer_name": "John Doe",
  "items": ["Laptop", "Mouse"],
  "notes": "Customer requested expedited processing"
}
```

#### Get Order with Timeline
```http
GET /orders/{id}
# Returns complete order with all timestamps and status history
```

#### Get Order Timeline
```http
GET /orders/{id}/timeline
# Returns detailed timeline view with fulfillment timestamps
```

#### Advance Order Workflow
```http
POST /orders/{id}/advance?notes=Items%20picked%20from%20inventory
# Automatically advances to next status in workflow
```

#### Manual Status Update
```http
PATCH /orders/{id}
{
  "status": "shipped",
  "notes": "Package shipped via FedEx, tracking: 123456"
}
```

## 🎯 **Expected Behavior After Update**

### **Fixed Issues**
- ✅ **404 errors on `/categories` endpoint** - Now properly implemented
- ✅ **Missing order timeline functionality** - Complete timeline tracking
- ✅ **No status change history** - Full audit trail with notes
- ✅ **Manual workflow management** - Automated progression available

### **New Capabilities**
- 🕐 **Complete timestamp tracking** for every order state change
- 📜 **Status change history** with optional notes for context
- 🚀 **Automated workflow progression** through fulfillment stages
- 📊 **Timeline analysis** for performance monitoring
- 💬 **Enhanced MCP responses** with rich timestamp information

### **Workflow Progression**
```
📅 Pending (placed_at)
    ↓ advance_order()
✅ Confirmed (confirmed_at)  
    ↓ advance_order()
🔍 Picking (picked_at)
    ↓ advance_order()
📦 Packed (packed_at)
    ↓ advance_order()
🚚 Shipped (shipped_at)
    ↓ advance_order()
🏠 Delivered (delivered_at)
```

### **Sample Timeline Response**
```json
{
  "order_id": 123,
  "customer_name": "Alice Smith",
  "current_status": "shipped",
  "created_at": "2024-01-01T10:00:00Z",
  "status_changes": [
    {
      "status": "pending",
      "timestamp": "2024-01-01T10:00:00Z",
      "notes": "Order created"
    },
    {
      "status": "confirmed", 
      "timestamp": "2024-01-01T10:15:00Z",
      "notes": "Order confirmed by warehouse team"
    },
    {
      "status": "shipped",
      "timestamp": "2024-01-01T14:00:00Z", 
      "notes": "Package shipped via FedEx"
    }
  ],
  "fulfillment_timestamps": {
    "placed_at": "2024-01-01T10:00:00Z",
    "confirmed_at": "2024-01-01T10:15:00Z", 
    "picked_at": "2024-01-01T11:30:00Z",
    "packed_at": "2024-01-01T12:00:00Z",
    "shipped_at": "2024-01-01T14:00:00Z",
    "delivered_at": null,
    "cancelled_at": null
  }
}
```

## 🔧 **Troubleshooting**

### **If Categories Still Return 404**
```bash
# Check if sample data initialized
curl http://localhost:8000/categories

# If empty, restart containers to trigger initialization
docker compose -p warehouse restart

# Check logs for any errors
docker compose -p warehouse logs fastapi-app
```

### **If Timeline Endpoints Don't Work**
```bash
# Verify the enhanced app.py is deployed
docker compose -p warehouse logs fastapi-app | grep "Enhanced Warehouse API"

# Should see: "Enhanced Warehouse API version 2.1.0"
```

### **If MCP Server Issues**
```bash
# Check MCP server logs
docker compose -p warehouse logs mcp

# Restart MCP container specifically
docker compose -p warehouse restart mcp
```

## 🎉 **Success Indicators**

You'll know the deployment worked when:

- ✅ `GET /categories` returns sample categories (not 404)
- ✅ `POST /orders` creates orders with timestamps
- ✅ `GET /orders/{id}/timeline` returns detailed timeline
- ✅ `POST /orders/{id}/advance` progresses workflow
- ✅ MCP server responds with enhanced timeline information
- ✅ API documentation shows version 2.1.0 at `/docs`

## 📈 **Performance & Benefits**

The enhanced system provides:

- **Operational Visibility**: Real-time order status tracking
- **Process Analytics**: Measure time between fulfillment stages  
- **Audit Compliance**: Complete change history for accountability
- **Customer Service**: Precise status updates and delivery estimates
- **AI Integration**: Rich conversational interfaces via MCP

Your warehouse system is now enterprise-ready with comprehensive order timeline tracking and automated workflow management!
