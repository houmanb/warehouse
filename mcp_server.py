import asyncio
import os
from typing import List

import httpx
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

API_BASE_URL = os.getenv("API_BASE_URL", "http://fastapi-app:8000")

server = Server("warehouse-mcp")

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    return [
        # Customer Tools
        types.Tool(
            name="create_customer",
            description="Create a new customer",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer name"},
                    "email": {"type": "string", "description": "Customer email"},
                    "phone": {"type": "string", "description": "Customer phone number"},
                    "address": {"type": "string", "description": "Customer address"}
                },
                "required": ["name", "email"]
            }
        ),
        types.Tool(
            name="get_customer",
            description="Get a customer by ID",
            inputSchema={
                "type": "object",
                "properties": {"customer_id": {"type": "integer"}},
                "required": ["customer_id"]
            }
        ),
        types.Tool(
            name="list_customers",
            description="List all customers",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="update_customer",
            description="Update customer information",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"}
                },
                "required": ["customer_id"]
            }
        ),
        types.Tool(
            name="delete_customer",
            description="Delete a customer (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {"customer_id": {"type": "integer"}},
                "required": ["customer_id"]
            }
        ),
        
        # Category Tools
        types.Tool(
            name="create_category",
            description="Create a new category",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Category name"},
                    "description": {"type": "string", "description": "Category description"}
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="get_category",
            description="Get a category by ID",
            inputSchema={
                "type": "object",
                "properties": {"category_id": {"type": "integer"}},
                "required": ["category_id"]
            }
        ),
        types.Tool(
            name="list_categories",
            description="List all categories",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # Item Tools
        types.Tool(
            name="create_item",
            description="Create a new item",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Item name"},
                    "description": {"type": "string", "description": "Item description"},
                    "price": {"type": "number", "description": "Item price"},
                    "stock_quantity": {"type": "integer", "description": "Stock quantity"},
                    "category_id": {"type": "integer", "description": "Category ID"},
                    "sku": {"type": "string", "description": "Stock Keeping Unit"}
                },
                "required": ["name", "price", "stock_quantity", "category_id", "sku"]
            }
        ),
        types.Tool(
            name="get_item",
            description="Get an item by ID",
            inputSchema={
                "type": "object",
                "properties": {"item_id": {"type": "integer"}},
                "required": ["item_id"]
            }
        ),
        types.Tool(
            name="list_items",
            description="List all active items",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="update_item",
            description="Update item information",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "price": {"type": "number"},
                    "stock_quantity": {"type": "integer"},
                    "category_id": {"type": "integer"},
                    "sku": {"type": "string"}
                },
                "required": ["item_id"]
            }
        ),
        
        # Basket Tools
        types.Tool(
            name="add_to_basket",
            description="Add an item to customer's basket",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer ID"},
                    "item_id": {"type": "integer", "description": "Item ID"},
                    "quantity": {"type": "integer", "description": "Quantity to add"}
                },
                "required": ["customer_id", "item_id", "quantity"]
            }
        ),
        types.Tool(
            name="get_basket",
            description="Get customer's basket",
            inputSchema={
                "type": "object",
                "properties": {"customer_id": {"type": "integer"}},
                "required": ["customer_id"]
            }
        ),
        types.Tool(
            name="remove_from_basket",
            description="Remove an item from customer's basket",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"},
                    "item_id": {"type": "integer"}
                },
                "required": ["customer_id", "item_id"]
            }
        ),
        types.Tool(
            name="clear_basket",
            description="Clear all items from customer's basket",
            inputSchema={
                "type": "object",
                "properties": {"customer_id": {"type": "integer"}},
                "required": ["customer_id"]
            }
        ),
        
        # Enhanced Order Tools with Complete Timeline Support
        types.Tool(
            name="create_order",
            description="Create a new warehouse order with timestamp tracking",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Name of the customer"},
                    "items": {"type": "array", "items": {"type": "string"}, "description": "List of items"},
                    "notes": {"type": "string", "description": "Optional order notes"}
                },
                "required": ["customer_name", "items"]
            }
        ),
        types.Tool(
            name="get_order",
            description="Get a specific order by ID with full timestamp details",
            inputSchema={"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}
        ),
        types.Tool(
            name="list_orders", 
            description="List all orders with timestamp information",
            inputSchema={
                "type": "object", 
                "properties": {
                    "details": {"type": "boolean", "description": "Include full item details and timestamps"}
                }
            }
        ),
        types.Tool(
            name="update_order",
            description="Update an existing order and track status changes",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "customer_name": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                    "status": {"type": "string", "description": "Order status: pending, confirmed, picking, packed, shipped, delivered, cancelled"},
                    "notes": {"type": "string", "description": "Notes about the status change"}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="advance_order",
            description="Advance order to next status in fulfillment workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "notes": {"type": "string", "description": "Optional notes about the advancement"}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="get_order_timeline",
            description="Get detailed timeline of order status changes and fulfillment timestamps",
            inputSchema={
                "type": "object",
                "properties": {"order_id": {"type": "integer"}},
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="delete_order",
            description="Delete an order by ID",
            inputSchema={"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}
        ),
    ]

# Optional—avoid noisy "method not found" in your logs
@server.list_prompts()
async def handle_list_prompts() -> List[types.Prompt]:
    return []

@server.list_resources()
async def handle_list_resources() -> List[types.Resource]:
    return []

def format_timestamp(ts_str):
    """Format timestamp for display"""
    if not ts_str:
        return "Not set"
    try:
        # Parse ISO format and return a readable format
        from datetime import datetime
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return ts_str

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
            
            # Customer operations
            if name == "create_customer":
                payload = {
                    "name": arguments["name"],
                    "email": arguments["email"],
                    "phone": arguments.get("phone"),
                    "address": arguments.get("address")
                }
                resp = await client.post("/customers", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return [types.TextContent(type="text",
                    text=f"✅ Customer created\nID: {data['customer_id']}\nName: {data['name']}\nEmail: {data['email']}\nPhone: {data.get('phone', 'N/A')}\nAddress: {data.get('address', 'N/A')}")]

            elif name == "get_customer":
                cid = arguments["customer_id"]
                resp = await client.get(f"/customers/{cid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Customer {cid} not found")]
                resp.raise_for_status()
                d = resp.json()
                return [types.TextContent(type="text",
                    text=f"👤 Customer {d['customer_id']}\nName: {d['name']}\nEmail: {d['email']}\nPhone: {d.get('phone', 'N/A')}\nAddress: {d.get('address', 'N/A')}\nActive: {d['is_active']}")]

            elif name == "list_customers":
                resp = await client.get("/customers")
                resp.raise_for_status()
                customers = resp.json()
                if not customers:
                    return [types.TextContent(type="text", text="👥 No customers found")]
                
                lines = []
                for c in customers:
                    status = "✅" if c["is_active"] else "❌"
                    lines.append(f"{status} ID: {c['customer_id']} - {c['name']} ({c['email']})")
                return [types.TextContent(type="text", text=f"👥 All Customers ({len(customers)} total):\n\n" + "\n".join(lines))]

            elif name == "update_customer":
                cid = arguments["customer_id"]
                payload = {}
                for field in ["name", "email", "phone", "address"]:
                    if field in arguments:
                        payload[field] = arguments[field]
                
                resp = await client.patch(f"/customers/{cid}", json=payload)
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Customer {cid} not found")]
                resp.raise_for_status()
                d = resp.json()
                return [types.TextContent(type="text",
                    text=f"✅ Customer {cid} updated\nName: {d['name']}\nEmail: {d['email']}\nPhone: {d.get('phone', 'N/A')}\nAddress: {d.get('address', 'N/A')}")]

            elif name == "delete_customer":
                cid = arguments["customer_id"]
                resp = await client.delete(f"/customers/{cid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Customer {cid} not found")]
                resp.raise_for_status()
                return [types.TextContent(type="text", text=f"🗑️ Customer {cid} deleted (deactivated)")]

            # Category operations
            elif name == "create_category":
                payload = {
                    "name": arguments["name"],
                    "description": arguments.get("description")
                }
                resp = await client.post("/categories", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return [types.TextContent(type="text",
                    text=f"✅ Category created\nID: {data['category_id']}\nName: {data['name']}\nDescription: {data.get('description', 'N/A')}")]

            elif name == "get_category":
                cid = arguments["category_id"]
                resp = await client.get(f"/categories/{cid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Category {cid} not found")]
                resp.raise_for_status()
                d = resp.json()
                return [types.TextContent(type="text",
                    text=f"📂 Category {d['category_id']}\nName: {d['name']}\nDescription: {d.get('description', 'N/A')}")]

            elif name == "list_categories":
                resp = await client.get("/categories")
                resp.raise_for_status()
                categories = resp.json()
                if not categories:
                    return [types.TextContent(type="text", text="📂 No categories found")]
                
                lines = []
                for c in categories:
                    lines.append(f"📂 ID: {c['category_id']} - {c['name']}")
                return [types.TextContent(type="text", text=f"📂 All Categories ({len(categories)} total):\n\n" + "\n".join(lines))]

            # Item operations
            elif name == "create_item":
                payload = {
                    "name": arguments["name"],
                    "description": arguments.get("description"),
                    "price": arguments["price"],
                    "stock_quantity": arguments["stock_quantity"],
                    "category_id": arguments["category_id"],
                    "sku": arguments["sku"]
                }
                resp = await client.post("/items", json=payload)
                if resp.status_code == 400:
                    error_detail = resp.json().get("detail", "Bad request")
                    return [types.TextContent(type="text", text=f"❌ Error creating item: {error_detail}")]
                resp.raise_for_status()
                data = resp.json()
                return [types.TextContent(type="text",
                    text=f"✅ Item created\nID: {data['item_id']}\nName: {data['name']}\nSKU: {data['sku']}\nPrice: ${data['price']}\nStock: {data['stock_quantity']}\nCategory: {data['category_id']}")]

            elif name == "get_item":
                iid = arguments["item_id"]
                resp = await client.get(f"/items/{iid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Item {iid} not found")]
                resp.raise_for_status()
                d = resp.json()
                return [types.TextContent(type="text",
                    text=f"📦 Item {d['item_id']}\nName: {d['name']}\nSKU: {d['sku']}\nPrice: ${d['price']}\nStock: {d['stock_quantity']}\nCategory: {d['category_id']}\nDescription: {d.get('description', 'N/A')}")]

            elif name == "list_items":
                resp = await client.get("/items")
                resp.raise_for_status()
                items = resp.json()
                if not items:
                    return [types.TextContent(type="text", text="📦 No items found")]
                
                lines = []
                for i in items:
                    stock_emoji = "📦" if i["stock_quantity"] > 0 else "📭"
                    lines.append(f"{stock_emoji} {i['name']} (SKU: {i['sku']}) - ${i['price']} - Stock: {i['stock_quantity']}")
                return [types.TextContent(type="text", text=f"📦 All Items ({len(items)} total):\n\n" + "\n".join(lines))]

            elif name == "update_item":
                iid = arguments["item_id"]
                payload = {}
                for field in ["name", "description", "price", "stock_quantity", "category_id", "sku"]:
                    if field in arguments:
                        payload[field] = arguments[field]
                
                resp = await client.patch(f"/items/{iid}", json=payload)
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Item {iid} not found")]
                resp.raise_for_status()
                d = resp.json()
                return [types.TextContent(type="text",
                    text=f"✅ Item {iid} updated\nName: {d['name']}\nSKU: {d['sku']}\nPrice: ${d['price']}\nStock: {d['stock_quantity']}")]

            # Basket operations
            elif name == "add_to_basket":
                cid = arguments["customer_id"]
                payload = {
                    "item_id": arguments["item_id"],
                    "quantity": arguments["quantity"]
                }
                resp = await client.post(f"/baskets/{cid}/items", json=payload)
                if resp.status_code == 404:
                    error_detail = resp.json().get("detail", "Not found")
                    return [types.TextContent(type="text", text=f"❌ Error: {error_detail}")]
                resp.raise_for_status()
                return [types.TextContent(type="text", text=f"🛒 Item added to customer {cid}'s basket")]

            elif name == "get_basket":
                cid = arguments["customer_id"]
                resp = await client.get(f"/baskets/{cid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"🛒 Customer {cid} has no basket or basket is empty")]
                resp.raise_for_status()
                d = resp.json()
                
                if not d["items"]:
                    return [types.TextContent(type="text", text=f"🛒 Customer {cid}'s basket is empty")]
                
                lines = [f"🛒 Customer {cid}'s Basket:"]
                for item in d["items"]:
                    lines.append(f"  📦 {item['item_name']} - Qty: {item['quantity']} - ${item['unit_price']} each - Total: ${item['total_price']:.2f}")
                lines.append(f"\n💰 Total Amount: ${d['total_amount']:.2f}")
                return [types.TextContent(type="text", text="\n".join(lines))]

            elif name == "remove_from_basket":
                cid = arguments["customer_id"]
                iid = arguments["item_id"]
                resp = await client.delete(f"/baskets/{cid}/items/{iid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Item not found in customer {cid}'s basket")]
                resp.raise_for_status()
                return [types.TextContent(type="text", text=f"🗑️ Item removed from customer {cid}'s basket")]

            elif name == "clear_basket":
                cid = arguments["customer_id"]
                resp = await client.delete(f"/baskets/{cid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Customer {cid} has no basket")]
                resp.raise_for_status()
                return [types.TextContent(type="text", text=f"🧹 Customer {cid}'s basket cleared")]

            # Enhanced Order operations with complete timeline support
            elif name == "create_order":
                payload = {
                    "customer_name": arguments["customer_name"], 
                    "items": arguments["items"],
                    "notes": arguments.get("notes")
                }
                resp = await client.post("/orders", json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                # Enhanced response with comprehensive timestamp information
                lines = [
                    f"✅ Order created successfully",
                    f"📋 Order ID: {data['order_id']}",
                    f"👤 Customer: {data['customer_name']}",
                    f"📦 Items: {', '.join(data['items'])}",
                    f"📊 Status: {data['status']}",
                    f"🕐 Created: {format_timestamp(data['created_at'])}",
                    f"🕐 Placed: {format_timestamp(data.get('placed_at'))}"
                ]
                if data.get('notes'):
                    lines.append(f"📝 Notes: {data['notes']}")
                
                # Show initial status history
                if data.get('status_history'):
                    lines.append(f"\n📜 Status History: {len(data['status_history'])} entries")
                
                return [types.TextContent(type="text", text="\n".join(lines))]

            elif name == "get_order":
                oid = arguments["order_id"]
                resp = await client.get(f"/orders/{oid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Order {oid} not found")]
                resp.raise_for_status()
                d = resp.json()
                
                # Comprehensive order details with all timestamp information
                lines = [
                    f"📋 Order {d['order_id']} Details",
                    f"👤 Customer: {d['customer_name']}",
                    f"📦 Items: {', '.join(d['items'])}",
                    f"📊 Current Status: {d['status']}",
                    "",
                    "🕐 Fulfillment Timeline:"
                ]
                
                # Add fulfillment timestamps with better formatting
                timestamp_fields = [
                    ("placed_at", "📅 Order Placed"),
                    ("confirmed_at", "✅ Confirmed"),
                    ("picked_at", "🔍 Picked"),
                    ("packed_at", "📦 Packed"),
                    ("shipped_at", "🚚 Shipped"),
                    ("delivered_at", "🏠 Delivered"),
                    ("cancelled_at", "❌ Cancelled")
                ]
                
                for field, label in timestamp_fields:
                    if d.get(field):
                        lines.append(f"  {label}: {format_timestamp(d[field])}")
                
                if d.get('notes'):
                    lines.append(f"\n📝 Notes: {d['notes']}")
                
                # Add comprehensive status history
                if d.get('status_history'):
                    lines.append(f"\n📜 Status History ({len(d['status_history'])} changes):")
                    for i, history in enumerate(d['status_history'][-3:], 1):  # Show last 3 changes
                        lines.append(f"  {i}. {history['status']} - {format_timestamp(history['timestamp'])}")
                        if history.get('notes'):
                            lines.append(f"     📝 {history['notes']}")
                    if len(d['status_history']) > 3:
                        lines.append(f"     ... and {len(d['status_history']) - 3} more changes")
                
                return [types.TextContent(type="text", text="\n".join(lines))]

            elif name == "list_orders":
                resp = await client.get("/orders")
                resp.raise_for_status()
                rows = resp.json()
                if not rows:
                    return [types.TextContent(type="text", text="📊 No orders found")]
                
                show_details = arguments.get("details", False)
                
                if show_details:
                    # Detailed view with comprehensive timestamps
                    lines = [f"📊 All Orders ({len(rows)} total) - Detailed Timeline View:\n"]
                    for d in rows:
                        status_emoji = {
                            "pending": "⏳", "confirmed": "✅", "picking": "🔍", 
                            "packed": "📦", "shipped": "🚚", "delivered": "🏠", 
                            "cancelled": "❌"
                        }.get(d["status"], "❓")
                        
                        items_str = ', '.join(d['items']) if d.get('items') else 'No items'
                        created = format_timestamp(d.get('created_at', ''))
                        
                        lines.append(f"{status_emoji} Order {d['order_id']}: {d['customer_name']}")
                        lines.append(f"   📦 Items: {items_str}")
                        lines.append(f"   📊 Status: {d['status']}")
                        lines.append(f"   🕐 Created: {created}")
                        
                        # Show latest status change timestamp
                        latest_status_time = d.get(f"{d['status']}_at")
                        if latest_status_time:
                            lines.append(f"   🕐 {d['status'].title()}: {format_timestamp(latest_status_time)}")
                        
                        if d.get('notes'):
                            lines.append(f"   📝 Notes: {d['notes']}")
                        lines.append("")
                        
                    return [types.TextContent(type="text", text="\n".join(lines))]
                else:
                    # Summary view with status indicators
                    lines = []
                    for d in rows:
                        status_emoji = {
                            "pending": "⏳", "confirmed": "✅", "picking": "🔍", 
                            "packed": "📦", "shipped": "🚚", "delivered": "🏠", 
                            "cancelled": "❌"
                        }.get(d["status"], "❓")
                        
                        created_time = format_timestamp(d.get('created_at', ''))
                        lines.append(f"{status_emoji} Order {d['order_id']}: {d['customer_name']} - {len(d['items'])} items - {d['status']} ({created_time})")
                        
                    return [types.TextContent(type="text", text=f"📊 All Orders ({len(rows)} total):\n\n" + "\n".join(lines))]

            elif name == "update_order":
                oid = arguments["order_id"]
                payload = {}
                if "customer_name" in arguments: 
                    payload["customer_name"] = arguments["customer_name"]
                if "items" in arguments: 
                    payload["items"] = arguments["items"]
                if "status" in arguments: 
                    payload["status"] = arguments["status"]
                if "notes" in arguments:
                    payload["notes"] = arguments["notes"]
                
                resp = await client.patch(f"/orders/{oid}", json=payload)
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Order {oid} not found")]
                resp.raise_for_status()
                d = resp.json()
                
                lines = [
                    f"✅ Order {oid} updated successfully",
                    f"👤 Customer: {d['customer_name']}",
                    f"📦 Items: {', '.join(d['items'])}",
                    f"📊 Status: {d['status']}",
                    f"🕐 Updated: {format_timestamp(d['updated_at'])}"
                ]
                
                # Show status-specific timestamp if available
                status_timestamp_field = f"{d['status']}_at"
                if d.get(status_timestamp_field):
                    lines.append(f"🕐 {d['status'].title()}: {format_timestamp(d[status_timestamp_field])}")
                
                return [types.TextContent(type="text", text="\n".join(lines))]

            elif name == "advance_order":
                oid = arguments["order_id"]
                notes = arguments.get("notes")
                
                # Build request with optional notes
                params = {}
                if notes:
                    params["notes"] = notes
                
                resp = await client.post(f"/orders/{oid}/advance", params=params)
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Order {oid} not found")]
                if resp.status_code == 400:
                    error_detail = resp.json().get("detail", "Cannot advance order")
                    return [types.TextContent(type="text", text=f"❌ {error_detail}")]
                resp.raise_for_status()
                
                result = resp.json()
                order_data = result["order"]
                
                lines = [
                    f"🚀 {result['message']}",
                    f"📋 Order {oid} Details:",
                    f"👤 Customer: {order_data['customer_name']}",
                    f"📊 New Status: {order_data['status']}",
                    f"🕐 Updated: {format_timestamp(order_data['updated_at'])}"
                ]
                
                # Show status-specific timestamp
                status_timestamp_field = f"{order_data['status']}_at"
                if order_data.get(status_timestamp_field):
                    status_label = {
                        "confirmed_at": "✅ Confirmed",
                        "picked_at": "🔍 Picked", 
                        "packed_at": "📦 Packed",
                        "shipped_at": "🚚 Shipped",
                        "delivered_at": "🏠 Delivered"
                    }.get(status_timestamp_field, f"🕐 {order_data['status'].title()}")
                    lines.append(f"{status_label}: {format_timestamp(order_data[status_timestamp_field])}")
                
                return [types.TextContent(type="text", text="\n".join(lines))]

            elif name == "get_order_timeline":
                oid = arguments["order_id"]
                resp = await client.get(f"/orders/{oid}/timeline")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Order {oid} not found")]
                resp.raise_for_status()
                
                timeline = resp.json()
                
                lines = [
                    f"📅 Order {timeline['order_id']} Complete Timeline",
                    f"👤 Customer: {timeline['customer_name']}",
                    f"📊 Current Status: {timeline['current_status']}",
                    f"🕐 Created: {format_timestamp(timeline['created_at'])}",
                    "",
                    "🕐 Fulfillment Timeline:"
                ]
                
                # Show all fulfillment timestamps in order
                fulfillment = timeline['fulfillment_timestamps']
                timestamp_labels = [
                    ("placed_at", "📅 Order Placed"),
                    ("confirmed_at", "✅ Order Confirmed"),
                    ("picked_at", "🔍 Items Picked"),
                    ("packed_at", "📦 Items Packed"),
                    ("shipped_at", "🚚 Package Shipped"),
                    ("delivered_at", "🏠 Order Delivered"),
                    ("cancelled_at", "❌ Order Cancelled")
                ]
                
                completed_steps = 0
                for field, label in timestamp_labels:
                    if fulfillment.get(field):
                        lines.append(f"  {label}: {format_timestamp(fulfillment[field])}")
                        completed_steps += 1
                    elif field != "cancelled_at":  # Don't show "not set" for cancelled
                        lines.append(f"  {label}: Not completed")
                
                lines.append(f"\n📊 Progress: {completed_steps}/{len(timestamp_labels)-1} steps completed")
                
                # Show comprehensive status change history
                if timeline['status_changes']:
                    lines.append(f"\n📜 Complete Status Change History ({len(timeline['status_changes'])} changes):")
                    for i, change in enumerate(timeline['status_changes'], 1):
                        emoji = {
                            "pending": "⏳", "confirmed": "✅", "picking": "🔍",
                            "packed": "📦", "shipped": "🚚", "delivered": "🏠", 
                            "cancelled": "❌"
                        }.get(change['status'], "🔄")
                        
                        lines.append(f"  {i}. {emoji} {change['status'].upper()} - {format_timestamp(change['timestamp'])}")
                        if change.get('notes'):
                            lines.append(f"     💬 {change['notes']}")
                
                return [types.TextContent(type="text", text="\n".join(lines))]

            elif name == "delete_order":
                oid = arguments["order_id"]
                resp = await client.delete(f"/orders/{oid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Order {oid} not found")]
                resp.raise_for_status()
                return [types.TextContent(type="text", text=f"🗑️ Order {oid} deleted and marked as cancelled")]

            else:
                return [types.TextContent(type="text", text=f"❌ Unknown tool: {name}")]

    except httpx.HTTPError as e:
        return [types.TextContent(type="text", text=f"❌ HTTP error: {e}")]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="warehouse-mcp",
                server_version="2.1.0",
                capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={}),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())