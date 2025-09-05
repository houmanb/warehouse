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
        
        # Order Tools (existing)
        types.Tool(
            name="create_order",
            description="Create a new warehouse order",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Name of the customer"},
                    "items": {"type": "array", "items": {"type": "string"}, "description": "List of items"}
                },
                "required": ["customer_name", "items"]
            }
        ),
        types.Tool(
            name="get_order",
            description="Get a specific order by ID",
            inputSchema={"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}
        ),
        types.Tool(
            name="list_orders", 
            description="List all orders. Use 'details=true' parameter to get full item details.",
            inputSchema={
                "type": "object", 
                "properties": {
                    "details": {"type": "boolean", "description": "Include full item details instead of just counts"}
                }
            }
        ),
        types.Tool(
            name="update_order",
            description="Update an existing order",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "customer_name": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                    "status": {"type": "string"}
                },
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

            # Original order operations
            elif name == "create_order":
                payload = {"customer_name": arguments["customer_name"], "items": arguments["items"]}
                resp = await client.post("/orders", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return [types.TextContent(type="text",
                    text=f"✅ Order created\nID: {data['order_id']}\nCustomer: {data['customer_name']}\nItems: {', '.join(data['items'])}\nStatus: {data['status']}")]

            elif name == "get_order":
                oid = arguments["order_id"]
                resp = await client.get(f"/orders/{oid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Order {oid} not found")]
                resp.raise_for_status()
                d = resp.json()
                return [types.TextContent(type="text",
                    text=f"📋 Order {d['order_id']}\nCustomer: {d['customer_name']}\nItems: {', '.join(d['items'])}\nStatus: {d['status']}")]

            elif name == "list_orders":
                resp = await client.get("/orders")
                resp.raise_for_status()
                rows = resp.json()
                if not rows:
                    return [types.TextContent(type="text", text="🔭 No orders found")]
                
                # Check if detailed view is requested
                show_details = arguments.get("details", False)
                
                if show_details:
                    # Return detailed format with item names
                    lines = []
                    for d in rows:
                        status_emoji = {"pending": "⏳", "shipped": "🚚", "cancelled": "❌"}.get(d["status"], "❓")
                        items_str = ', '.join(d['items']) if d.get('items') else 'No items'
                        lines.append(f"{status_emoji} Order {d['order_id']}: {d['customer_name']} - Items: {items_str} - {d['status']}")
                    return [types.TextContent(type="text", text=f"📊 All Orders ({len(rows)} total) - Detailed View:\n\n" + "\n".join(lines))]
                else:
                    # Return summary format with item counts
                    lines = []
                    for d in rows:
                        status_emoji = {"pending": "⏳", "shipped": "🚚", "cancelled": "❌"}.get(d["status"], "❓")
                        lines.append(f"{status_emoji} Order {d['order_id']}: {d['customer_name']} - {len(d['items'])} items - {d['status']}")
                    return [types.TextContent(type="text", text=f"📊 All Orders ({len(rows)} total):\n\n" + "\n".join(lines))]

            elif name == "update_order":
                oid = arguments["order_id"]
                payload = {}
                if "customer_name" in arguments: payload["customer_name"] = arguments["customer_name"]
                if "items" in arguments: payload["items"] = arguments["items"]
                if "status" in arguments: payload["status"] = arguments["status"]
                resp = await client.patch(f"/orders/{oid}", json=payload)
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Order {oid} not found")]
                resp.raise_for_status()
                d = resp.json()
                pieces = [f"👤 Customer: {d['customer_name']}", f"📦 Items: {', '.join(d['items'])}", f"🛈 Status: {d['status']}"]
                return [types.TextContent(type="text", text=f"✅ Order {oid} updated\n" + "\n".join(pieces))]

            elif name == "delete_order":
                oid = arguments["order_id"]
                resp = await client.delete(f"/orders/{oid}")
                if resp.status_code == 404:
                    return [types.TextContent(type="text", text=f"❌ Order {oid} not found")]
                resp.raise_for_status()
                return [types.TextContent(type="text", text=f"🗑️ Order {oid} deleted")]

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
                server_version="2.0.0",
                capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={}),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())