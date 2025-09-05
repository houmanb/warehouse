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
            if name == "create_order":
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
                server_version="0.1.0",
                capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={}),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
