import asyncio
import os
import sys
from typing import List

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Import the warehouse client
from warehouse_client import WarehouseClient, create_customer_client, create_fulfillment_client

API_BASE_URL = os.getenv("API_BASE_URL", "http://warehouse-api:8000")
DEFAULT_AGENT_ROLE = os.getenv("AGENT_ROLE", "fulfillment")
CONTAINER_MODE = os.getenv("CONTAINER_MODE", "true").lower() == "true"

server = Server("warehouse-state-machine-mcp")

# ... (keep all your existing @server decorators and functions exactly the same) ...
@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    return [
        # Basic API Operations
        types.Tool(
            name="health_check",
            description="Check API health status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_state_machine_info",
            description="Get state machine configuration and role permissions",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                }
            }
        ),
        
        # Order Management
        types.Tool(
            name="create_order",
            description="Create a new warehouse order",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Name of the customer"},
                    "items": {"type": "array", "items": {"type": "string"}, "description": "List of items"},
                    "notes": {"type": "string", "description": "Optional order notes"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["customer_name", "items"]
            }
        ),
        types.Tool(
            name="get_order",
            description="Get order details with available transitions",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="list_orders",
            description="List all orders with available transitions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of orders to return", "default": 50},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                }
            }
        ),
        
        # State Transitions
        types.Tool(
            name="request_transition",
            description="Request a state transition for an order",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID"},
                    "transition": {"type": "string", "description": "Transition name (e.g., 'confirm', 'cancel_from_pending')"},
                    "notes": {"type": "string", "description": "Optional notes for the transition"},
                    "agent_id": {"type": "string", "description": "Agent ID performing the transition"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["order_id", "transition"]
            }
        ),
        
        # Queue Management
        types.Tool(
            name="claim_next_task",
            description="Claim the next task from role-specific queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID claiming the task"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["agent_id"]
            }
        ),
        types.Tool(
            name="complete_task",
            description="Complete a claimed task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to complete"},
                    "agent_id": {"type": "string", "description": "Agent ID completing the task"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["task_id", "agent_id"]
            }
        ),
        types.Tool(
            name="release_task",
            description="Release a claimed task back to the queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID releasing the task"},
                    "reason": {"type": "string", "description": "Reason for releasing the task", "default": "Manual release"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["agent_id"]
            }
        ),
        types.Tool(
            name="get_queue_status",
            description="Get current queue status for all roles",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # Convenience Methods - Workflow Actions
        types.Tool(
            name="cancel_order",
            description="Cancel an order (automatically determines correct cancellation transition)",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to cancel"},
                    "reason": {"type": "string", "description": "Reason for cancellation", "default": "Customer cancellation"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "customer"}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="confirm_order",
            description="Confirm a pending order (fulfillment only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to confirm"},
                    "notes": {"type": "string", "description": "Optional confirmation notes"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "fulfillment"}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="start_picking",
            description="Start picking process for confirmed order (fulfillment only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to start picking"},
                    "notes": {"type": "string", "description": "Optional picking notes"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "fulfillment"}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="pack_order",
            description="Pack a picked order (fulfillment only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to pack"},
                    "notes": {"type": "string", "description": "Optional packing notes"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "fulfillment"}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="ship_order",
            description="Ship a packed order (fulfillment only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to ship"},
                    "notes": {"type": "string", "description": "Optional shipping notes"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "fulfillment"}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="deliver_order",
            description="Mark order as delivered (fulfillment only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to mark as delivered"},
                    "notes": {"type": "string", "description": "Optional delivery notes"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "fulfillment"}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="return_order",
            description="Return a delivered order",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to return"},
                    "reason": {"type": "string", "description": "Reason for return", "default": "Customer return"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "customer"}
                },
                "required": ["order_id"]
            }
        ),
        
        # Order Analysis and Filtering
        types.Tool(
            name="get_orders_by_state",
            description="Get orders filtered by specific state - perfect for customer order status aggregation",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "State to filter by", "enum": ["pending", "confirmed", "picking", "packed", "shipped", "delivered", "cancelled", "halted", "returned"]},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["state"]
            }
        ),
        types.Tool(
            name="get_my_orders",
            description="Get all orders for a specific customer - useful for customer order history and aggregation",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name to filter by"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "customer"}
                },
                "required": ["customer_name"]
            }
        ),
        types.Tool(
            name="get_pending_orders",
            description="Get all orders in pending state (fulfillment focused)",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "fulfillment"}
                }
            }
        ),
        
        # Worker/Automation Tools
        types.Tool(
            name="process_next_task",
            description="Claim and process the next available task automatically",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID processing tasks"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["agent_id"]
            }
        ),
        types.Tool(
            name="run_worker",
            description="Run as worker agent, continuously processing tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID for worker"},
                    "max_tasks": {"type": "integer", "description": "Maximum tasks to process (default: 10)"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": DEFAULT_AGENT_ROLE}
                },
                "required": ["agent_id"]
            }
        ),
        
        # Simulation Tools for Claude Interface
        types.Tool(
            name="simulate_customer_workflow",
            description="Simulate a complete customer workflow - create order and optionally cancel",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name for simulation"},
                    "items": {"type": "array", "items": {"type": "string"}, "description": "Items for simulation"},
                    "agent_role": {"type": "string", "description": "Agent role: 'customer' or 'fulfillment'", "default": "customer"}
                },
                "required": ["customer_name", "items"]
            }
        ),
        types.Tool(
            name="simulate_complete_workflow",
            description="Simulate complete order workflow from customer creation through fulfillment to delivery",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name for simulation"},
                    "items": {"type": "array", "items": {"type": "string"}, "description": "Items for simulation"},
                    "agent_id": {"type": "string", "description": "Agent ID for simulation", "default": "claude-simulation-agent"}
                },
                "required": ["customer_name", "items"]
            }
        )
    ]

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
        from datetime import datetime
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return ts_str

def format_order_details(order_data: dict, agent_role: str) -> str:
    """Format order details for display"""
    lines = [
        f"Order {order_data['order_id']} (viewed by {agent_role})",
        f"Customer: {order_data['customer_name']}",
        f"Items: {', '.join(order_data['items'])}",
        f"Current State: {order_data['current_state']}",
        f"Created: {format_timestamp(order_data.get('created_at'))}",
        f"Updated: {format_timestamp(order_data.get('updated_at'))}"
    ]
    
    if order_data.get('notes'):
        lines.append(f"Notes: {order_data['notes']}")
    
    # Show available transitions
    if order_data.get('available_transitions'):
        lines.append(f"\nAvailable transitions for {agent_role}:")
        for transition in order_data['available_transitions']:
            lines.append(f"  - {transition['transition']}: {transition['description']}")
    
    # Show recent history
    if order_data.get('history'):
        lines.append(f"\nRecent History ({len(order_data['history'])} total entries):")
        for entry in order_data['history'][-3:]:  # Show last 3 entries
            lines.append(f"  - {entry['state']} - {format_timestamp(entry['timestamp'])}")
            if entry.get('notes'):
                lines.append(f"    {entry['notes']}")
    
    return "\n".join(lines)

def get_client(agent_role: str) -> WarehouseClient:
    """Get appropriate client based on agent role"""
    if agent_role == "customer":
        return create_customer_client(API_BASE_URL)
    elif agent_role == "fulfillment":
        return create_fulfillment_client(API_BASE_URL)
    else:
        raise ValueError(f"Invalid agent role: {agent_role}")

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    # Extract agent role from arguments
    agent_role = arguments.get("agent_role", DEFAULT_AGENT_ROLE)
    
    # Validate agent role
    if agent_role not in ["customer", "fulfillment"]:
        return [types.TextContent(type="text", 
            text=f"Invalid agent role: {agent_role}. Must be 'customer' or 'fulfillment'.")]
    
    try:
        client = get_client(agent_role)
        
        # Basic API Operations
        if name == "health_check":
            result = client.health_check()
            return [types.TextContent(type="text",
                text=f"API Health: {result['status']}\nTimestamp: {format_timestamp(result['timestamp'])}")]
        
        elif name == "get_state_machine_info":
            info = client.get_state_machine_info()
            
            lines = [
                f"State Machine Configuration",
                f"Role: {agent_role}",
                "",
                f"Available States: {', '.join(info['states'])}",
                "",
                f"Available Transitions for {agent_role}:"
            ]
            
            role_transitions = info['role_permissions'].get(agent_role, [])
            for transition in role_transitions:
                lines.append(f"  - {transition}")
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        # Order Management
        elif name == "create_order":
            order = client.create_order(
                customer_name=arguments["customer_name"],
                items=arguments["items"],
                notes=arguments.get("notes")
            )
            return [types.TextContent(type="text", 
                text=f"Order created by {agent_role}\n\n{format_order_details(order, agent_role)}")]
        
        elif name == "get_order":
            order_id = arguments["order_id"]
            order = client.get_order(order_id)
            return [types.TextContent(type="text", text=format_order_details(order, agent_role))]
        
        elif name == "list_orders":
            limit = arguments.get("limit", 50)
            orders = client.list_orders(limit)
            
            if not orders:
                return [types.TextContent(type="text", text="No orders found")]
            
            lines = [f"Orders ({len(orders)} total) - {agent_role} view:", ""]
            for order in orders:
                lines.append(f"- Order {order['order_id']}: {order['customer_name']} - {order['current_state']} - {len(order['items'])} items")
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        # State Transitions
        elif name == "request_transition":
            result = client.request_transition(
                order_id=arguments["order_id"],
                transition=arguments["transition"],
                notes=arguments.get("notes"),
                agent_id=arguments.get("agent_id", f"claude-{agent_role}-agent")
            )
            return [types.TextContent(type="text", 
                text=f"Transition requested by {agent_role}\n{result['message']}\nTask ID: {result['task_id']}")]
        
        # Queue Management
        elif name == "claim_next_task":
            agent_id = arguments["agent_id"]
            result = client.claim_next_task(agent_id)
            
            if "No" in result["message"] and "tasks available" in result["message"]:
                return [types.TextContent(type="text", text=f"No {agent_role} tasks available for {agent_id}")]
            
            task = result["task"]
            lines = [
                f"Task claimed by {agent_id}",
                f"Task ID: {task['task_id']}",
                f"Order ID: {task['order_id']}",
                f"Transition: {task['transition']}",
                f"Expires in: {result.get('expires_in_seconds', 300)} seconds"
            ]
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        elif name == "complete_task":
            result = client.complete_task(
                task_id=arguments["task_id"],
                agent_id=arguments["agent_id"]
            )
            return [types.TextContent(type="text", 
                text=f"Task completed: {result['message']}\nOrder {result['order_id']} -> {result['new_state']}")]
        
        elif name == "release_task":
            result = client.release_task(
                agent_id=arguments["agent_id"],
                reason=arguments.get("reason", "Manual release")
            )
            return [types.TextContent(type="text", text=f"Task released: {result['message']}")]
        
        elif name == "get_queue_status":
            status = client.get_queue_status()
            
            lines = [
                "Queue Status:",
                f"Customer queue: {status['customer_queued']} tasks",
                f"Fulfillment queue: {status['fulfillment_queued']} tasks",
                f"Total processing: {status['total_processing']} tasks",
                f"Total tasks: {status['total_tasks']}"
            ]
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        # Convenience Methods - Use Client's Smart Logic
        elif name == "cancel_order":
            result = client.cancel_order(
                order_id=arguments["order_id"],
                reason=arguments.get("reason", "Customer cancellation via Claude MCP")
            )
            return [types.TextContent(type="text", 
                text=f"Order cancellation requested by {agent_role}\n{result['message']}")]
        
        elif name == "confirm_order":
            result = client.confirm_order(
                order_id=arguments["order_id"],
                notes=arguments.get("notes")
            )
            return [types.TextContent(type="text", 
                text=f"Order confirmation completed by {agent_role}\n{result['message']}")]
        
        elif name == "start_picking":
            result = client.start_picking(
                order_id=arguments["order_id"],
                notes=arguments.get("notes")
            )
            return [types.TextContent(type="text", 
                text=f"Picking started by {agent_role}\n{result['message']}")]
        
        elif name == "pack_order":
            result = client.pack_order(
                order_id=arguments["order_id"],
                notes=arguments.get("notes")
            )
            return [types.TextContent(type="text", 
                text=f"Order packed by {agent_role}\n{result['message']}")]
        
        elif name == "ship_order":
            result = client.ship_order(
                order_id=arguments["order_id"],
                notes=arguments.get("notes")
            )
            return [types.TextContent(type="text", 
                text=f"Order shipped by {agent_role}\n{result['message']}")]
        
        elif name == "deliver_order":
            result = client.deliver_order(
                order_id=arguments["order_id"],
                notes=arguments.get("notes")
            )
            return [types.TextContent(type="text", 
                text=f"Order delivered by {agent_role}\n{result['message']}")]
        
        elif name == "return_order":
            result = client.return_order(
                order_id=arguments["order_id"],
                reason=arguments.get("reason", "Customer return via Claude MCP")
            )
            return [types.TextContent(type="text", 
                text=f"Order return requested by {agent_role}\n{result['message']}")]
        
        # Filtering methods using client's convenience methods
        elif name == "get_my_orders":
            orders = client.get_my_orders(arguments["customer_name"])
            
            if not orders:
                return [types.TextContent(type="text", text=f"No orders found for customer: {arguments['customer_name']}")]
            
            lines = [f"Orders for {arguments['customer_name']} ({len(orders)} total) - {agent_role} view:", ""]
            for order in orders:
                lines.append(f"- Order {order['order_id']}: {order['customer_name']} - {order['current_state']} - {len(order['items'])} items")
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        elif name == "get_orders_by_state":
            orders = client.get_orders_by_state(arguments["state"])
            
            if not orders:
                return [types.TextContent(type="text", text=f"No orders found in {arguments['state']} state")]
            
            lines = [f"Orders in {arguments['state']} state ({len(orders)} total) - {agent_role} view:", ""]
            for order in orders:
                lines.append(f"- Order {order['order_id']}: {order['customer_name']} - {order['current_state']} - {len(order['items'])} items")
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        elif name == "get_pending_orders":
            orders = client.get_pending_orders()
            
            if not orders:
                return [types.TextContent(type="text", text="No pending orders found")]
            
            lines = [f"Pending Orders ({len(orders)} total) - {agent_role} view:", ""]
            for order in orders:
                lines.append(f"- Order {order['order_id']}: {order['customer_name']} - {order['current_state']} - {len(order['items'])} items")
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        # Worker/Automation Tools
        elif name == "process_next_task":
            agent_id = arguments["agent_id"]
            result = client.process_next_task(agent_id)
            
            if result.get('action') == 'task_completed':
                task = result['task']
                completion = result['result']
                lines = [
                    f"Task completed by {agent_id}",
                    f"Order {completion['order_id']}: {task['transition']} -> {completion['new_state']}",
                    f"Message: {completion['message']}"
                ]
                return [types.TextContent(type="text", text="\n".join(lines))]
            
            elif result.get('action') == 'task_failed':
                return [types.TextContent(type="text", text=f"Task failed: {result['error']}")]
            
            else:
                return [types.TextContent(type="text", text=f"No {agent_role} tasks available for {agent_id}")]
        
        elif name == "run_worker":
            agent_id = arguments["agent_id"]
            max_tasks = arguments.get("max_tasks", 10)
            
            processed_tasks = client.run_worker(agent_id, max_tasks, poll_interval=0)
            
            if not processed_tasks:
                return [types.TextContent(type="text", text=f"Worker {agent_id} found no tasks to process")]
            
            lines = [f"Worker {agent_id} processed {len(processed_tasks)} tasks:", ""]
            for result in processed_tasks:
                if result.get('action') == 'task_completed':
                    task = result['task']
                    completion = result['result']
                    lines.append(f"- SUCCESS: {task['transition']} -> {completion['new_state']} for order {completion['order_id']}")
                elif result.get('action') == 'task_failed':
                    task = result['task']
                    lines.append(f"- FAILED: {task['transition']} for order {task['order_id']} - {result['error']}")
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        # Simulation Tools
        elif name == "simulate_customer_workflow":
            result = client.simulate_customer_workflow(
                customer_name=arguments["customer_name"],
                items=arguments["items"]
            )
            
            lines = [
                f"Customer workflow simulation completed",
                f"Success: {result['success']}",
                f"Order ID: {result.get('order_id', 'N/A')}",
                f"Final State: {result.get('final_state', 'N/A')}",
                "",
                "Workflow steps:"
            ] + [f"- {step}" for step in result['workflow_steps']]
            
            return [types.TextContent(type="text", text="\n".join(lines))]
        
        elif name == "simulate_complete_workflow":
            # Use warehouse client for customer creation, then switch to fulfillment for processing
            customer_name = arguments["customer_name"]
            items = arguments["items"]
            agent_id = arguments.get("agent_id", "claude-simulation-agent")
            
            workflow_steps = []
            
            try:
                # Create order as customer
                customer_client = create_customer_client(API_BASE_URL)
                order = customer_client.create_order(customer_name, items, "Complete workflow simulation via Claude MCP")
                order_id = order['order_id']
                workflow_steps.append(f"Customer created order {order_id}")
                
                # Process through fulfillment workflow
                fulfillment_client = create_fulfillment_client(API_BASE_URL)
                
                # Run fulfillment agent to process all tasks for this order
                processed_tasks = fulfillment_client.run_worker(agent_id, max_tasks=10, poll_interval=0)
                
                for result in processed_tasks:
                    if result.get('action') == 'task_completed':
                        task = result['task']
                        completion = result['result']
                        if task['order_id'] == order_id:
                            workflow_steps.append(f"Completed {task['transition']} -> {completion['new_state']}")
                    elif result.get('action') == 'task_failed':
                        task = result['task']
                        if task['order_id'] == order_id:
                            workflow_steps.append(f"FAILED {task['transition']}: {result['error']}")
                
                # Get final order state
                final_order = customer_client.get_order(order_id)
                
                lines = [
                    f"Complete workflow simulation finished",
                    f"Order {order_id} final state: {final_order['current_state']}",
                    "",
                    "Workflow steps:"
                ] + [f"- {step}" for step in workflow_steps]
                
                return [types.TextContent(type="text", text="\n".join(lines))]
                
            except Exception as e:
                return [types.TextContent(type="text", text=f"Complete simulation error: {e}")]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except ValueError as e:
        # Client validation errors (like permission errors, invalid requests)
        return [types.TextContent(type="text", text=f"Request error: {e}")]
    except PermissionError as e:
        # Role permission errors
        return [types.TextContent(type="text", text=f"Permission denied: {e}")]
    except Exception as e:
        # Unexpected errors
        return [types.TextContent(type="text", text=f"Unexpected error: {e}")]

async def main():
    # Only print to stderr in MCP mode to avoid breaking JSON-RPC protocol
    if CONTAINER_MODE:
        # In container mode, we can safely print to stdout
        print(f"Starting Warehouse State Machine MCP Server v1.0.0")
        print(f"Default agent role: {DEFAULT_AGENT_ROLE}")
        print(f"API Base URL: {API_BASE_URL}")
        print("Running in container mode - server staying alive")
        try:
            # Keep the container running indefinitely
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Server shutting down...")
    else:
        # Normal MCP stdio mode - NO stdout prints allowed
        import sys
        sys.stderr.write(f"Starting MCP Server - stdio mode\n")
        sys.stderr.flush()
        
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="warehouse-state-machine-mcp",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(), 
                        experimental_capabilities={}
                    ),
                ),
            )

if __name__ == "__main__":
    asyncio.run(main())
