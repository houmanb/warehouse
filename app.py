from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import redis
import json
from datetime import datetime

app = FastAPI(title="Enhanced Warehouse API", version="2.1.0")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

# Enhanced Pydantic Models
class OrderStatusHistory(BaseModel):
    status: str
    timestamp: str
    notes: Optional[str] = None

class OrderIn(BaseModel):
    customer_name: str
    items: List[str]
    notes: Optional[str] = None

class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    items: Optional[List[str]] = None
    status: Optional[str] = None
    notes: Optional[str] = None

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

# Existing models
class CustomerIn(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerOut(BaseModel):
    customer_id: int
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: str
    is_active: bool

class CategoryIn(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryOut(BaseModel):
    category_id: int
    name: str
    description: Optional[str] = None
    created_at: str

class ItemIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int
    category_id: int
    sku: str

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    category_id: Optional[int] = None
    sku: Optional[str] = None

class ItemOut(BaseModel):
    item_id: int
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int
    category_id: int
    sku: str
    is_active: bool
    created_at: str

class BasketItemIn(BaseModel):
    item_id: int
    quantity: int

class BasketItemOut(BaseModel):
    item_id: int
    item_name: str
    quantity: int
    unit_price: float
    total_price: float

class BasketOut(BaseModel):
    basket_id: int
    customer_id: int
    items: List[BasketItemOut]
    total_amount: float
    created_at: str
    updated_at: str

# Helper Functions
def get_timestamp():
    return datetime.utcnow().isoformat()

def add_status_to_history(order_id: int, status: str, notes: Optional[str] = None):
    """Add a status change to order history"""
    timestamp = get_timestamp()
    history_key = f"order_history:{order_id}"
    
    new_entry = {
        "status": status,
        "timestamp": timestamp,
        "notes": notes
    }
    
    # Store as JSON string in Redis list
    r.lpush(history_key, json.dumps(new_entry))
    
    return timestamp

def get_order_history(order_id: int) -> List[OrderStatusHistory]:
    """Get order status history"""
    history_key = f"order_history:{order_id}"
    history_data = r.lrange(history_key, 0, -1)
    
    if not history_data:
        return []
    
    # Reverse to get chronological order (oldest first)
    history_items = [json.loads(item) for item in reversed(history_data)]
    return [OrderStatusHistory(**item) for item in history_items]

def update_fulfillment_timestamp(order_id: int, status: str):
    """Update specific fulfillment workflow timestamp"""
    timestamp = get_timestamp()
    order_key = f"order:{order_id}"
    
    # Map status to timestamp field
    timestamp_mapping = {
        "pending": "placed_at",
        "confirmed": "confirmed_at", 
        "picking": "picked_at",
        "packed": "packed_at",
        "shipped": "shipped_at",
        "delivered": "delivered_at",
        "cancelled": "cancelled_at"
    }
    
    if status in timestamp_mapping:
        field_name = timestamp_mapping[status]
        r.hset(order_key, field_name, timestamp)
    
    return timestamp

def get_order_response(order_id: int) -> OrderOut:
    """Helper function to build OrderOut response with all timestamps"""
    data = r.hgetall(f"order:{order_id}")
    history = get_order_history(order_id)
    
    return OrderOut(
        order_id=int(data["order_id"]),
        customer_name=data["customer_name"],
        items=data["items"].split(",") if data.get("items") else [],
        status=data["status"],
        notes=data.get("notes"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        status_history=history,
        placed_at=data.get("placed_at"),
        confirmed_at=data.get("confirmed_at"),
        picked_at=data.get("picked_at"),
        packed_at=data.get("packed_at"),
        shipped_at=data.get("shipped_at"),
        delivered_at=data.get("delivered_at"),
        cancelled_at=data.get("cancelled_at")
    )

def init_sample_data():
    """Initialize sample data if not exists"""
    if not r.exists("categories_initialized"):
        # Sample categories
        categories = [
            {"name": "Electronics", "description": "Electronic devices and accessories"},
            {"name": "Clothing", "description": "Apparel and fashion items"},
            {"name": "Books", "description": "Books and educational materials"},
            {"name": "Home & Garden", "description": "Home improvement and gardening supplies"}
        ]
        
        for cat in categories:
            cat_id = r.incr("category_id")
            data = {
                "category_id": str(cat_id),
                "name": cat["name"],
                "description": cat["description"],
                "created_at": get_timestamp()
            }
            r.hset(f"category:{cat_id}", mapping=data)
            r.sadd("categories", cat_id)
        
        # Sample items
        items = [
            {"name": "Laptop", "description": "High-performance laptop", "price": 999.99, "stock_quantity": 50, "category_id": 1, "sku": "ELEC001"},
            {"name": "Smartphone", "description": "Latest smartphone", "price": 699.99, "stock_quantity": 100, "category_id": 1, "sku": "ELEC002"},
            {"name": "T-Shirt", "description": "Cotton t-shirt", "price": 19.99, "stock_quantity": 200, "category_id": 2, "sku": "CLOT001"},
            {"name": "Jeans", "description": "Denim jeans", "price": 49.99, "stock_quantity": 75, "category_id": 2, "sku": "CLOT002"},
            {"name": "Python Programming", "description": "Learn Python programming", "price": 29.99, "stock_quantity": 30, "category_id": 3, "sku": "BOOK001"},
            {"name": "Garden Hose", "description": "50ft garden hose", "price": 39.99, "stock_quantity": 25, "category_id": 4, "sku": "HOME001"}
        ]
        
        for item in items:
            item_id = r.incr("item_id")
            data = {
                "item_id": str(item_id),
                "name": item["name"],
                "description": item["description"],
                "price": str(item["price"]),
                "stock_quantity": str(item["stock_quantity"]),
                "category_id": str(item["category_id"]),
                "sku": item["sku"],
                "is_active": "true",
                "created_at": get_timestamp()
            }
            r.hset(f"item:{item_id}", mapping=data)
            r.sadd("items", item_id)
        
        r.set("categories_initialized", "true")

# Initialize sample data on startup
init_sample_data()

@app.get("/health")
def health():
    return {"ok": True}

# Customer Endpoints
@app.post("/customers", response_model=CustomerOut)
def create_customer(customer: CustomerIn):
    # Check if email already exists
    existing_customers = r.smembers("customers")
    for cid in existing_customers:
        existing_data = r.hgetall(f"customer:{cid}")
        if existing_data.get("email") == customer.email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    customer_id = r.incr("customer_id")
    data = {
        "customer_id": str(customer_id),
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone or "",
        "address": customer.address or "",
        "created_at": get_timestamp(),
        "is_active": "true"
    }
    r.hset(f"customer:{customer_id}", mapping=data)
    r.sadd("customers", customer_id)
    
    return CustomerOut(
        customer_id=customer_id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        created_at=data["created_at"],
        is_active=True
    )

@app.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int):
    key = f"customer:{customer_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Customer not found")
    
    data = r.hgetall(key)
    return CustomerOut(
        customer_id=int(data["customer_id"]),
        name=data["name"],
        email=data["email"],
        phone=data["phone"] if data["phone"] else None,
        address=data["address"] if data["address"] else None,
        created_at=data["created_at"],
        is_active=data["is_active"] == "true"
    )

@app.get("/customers", response_model=List[CustomerOut])
def list_customers():
    ids = sorted([int(i) for i in r.smembers("customers")])
    customers = []
    for cid in ids:
        data = r.hgetall(f"customer:{cid}")
        if data:
            customers.append(CustomerOut(
                customer_id=int(data["customer_id"]),
                name=data["name"],
                email=data["email"],
                phone=data["phone"] if data["phone"] else None,
                address=data["address"] if data["address"] else None,
                created_at=data["created_at"],
                is_active=data["is_active"] == "true"
            ))
    return customers

@app.patch("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, upd: CustomerUpdate):
    key = f"customer:{customer_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if upd.name is not None:
        r.hset(key, "name", upd.name)
    if upd.email is not None:
        r.hset(key, "email", upd.email)
    if upd.phone is not None:
        r.hset(key, "phone", upd.phone)
    if upd.address is not None:
        r.hset(key, "address", upd.address)
    
    data = r.hgetall(key)
    return CustomerOut(
        customer_id=int(data["customer_id"]),
        name=data["name"],
        email=data["email"],
        phone=data["phone"] if data["phone"] else None,
        address=data["address"] if data["address"] else None,
        created_at=data["created_at"],
        is_active=data["is_active"] == "true"
    )

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int):
    key = f"customer:{customer_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Soft delete
    r.hset(key, "is_active", "false")
    return {"deleted": customer_id}

# Category Endpoints
@app.post("/categories", response_model=CategoryOut)
def create_category(category: CategoryIn):
    category_id = r.incr("category_id")
    data = {
        "category_id": str(category_id),
        "name": category.name,
        "description": category.description or "",
        "created_at": get_timestamp()
    }
    r.hset(f"category:{category_id}", mapping=data)
    r.sadd("categories", category_id)
    
    return CategoryOut(
        category_id=category_id,
        name=category.name,
        description=category.description,
        created_at=data["created_at"]
    )

@app.get("/categories/{category_id}", response_model=CategoryOut)
def get_category(category_id: int):
    key = f"category:{category_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Category not found")
    
    data = r.hgetall(key)
    return CategoryOut(
        category_id=int(data["category_id"]),
        name=data["name"],
        description=data["description"] if data["description"] else None,
        created_at=data["created_at"]
    )

@app.get("/categories", response_model=List[CategoryOut])
def list_categories():
    ids = sorted([int(i) for i in r.smembers("categories")])
    categories = []
    for cid in ids:
        data = r.hgetall(f"category:{cid}")
        if data:
            categories.append(CategoryOut(
                category_id=int(data["category_id"]),
                name=data["name"],
                description=data["description"] if data["description"] else None,
                created_at=data["created_at"]
            ))
    return categories

# Item Endpoints
@app.post("/items", response_model=ItemOut)
def create_item(item: ItemIn):
    # Check if SKU already exists
    existing_items = r.smembers("items")
    for iid in existing_items:
        existing_data = r.hgetall(f"item:{iid}")
        if existing_data.get("sku") == item.sku:
            raise HTTPException(status_code=400, detail="SKU already exists")
    
    # Check if category exists
    if not r.exists(f"category:{item.category_id}"):
        raise HTTPException(status_code=400, detail="Category not found")
    
    item_id = r.incr("item_id")
    data = {
        "item_id": str(item_id),
        "name": item.name,
        "description": item.description or "",
        "price": str(item.price),
        "stock_quantity": str(item.stock_quantity),
        "category_id": str(item.category_id),
        "sku": item.sku,
        "is_active": "true",
        "created_at": get_timestamp()
    }
    r.hset(f"item:{item_id}", mapping=data)
    r.sadd("items", item_id)
    
    return ItemOut(
        item_id=item_id,
        name=item.name,
        description=item.description,
        price=item.price,
        stock_quantity=item.stock_quantity,
        category_id=item.category_id,
        sku=item.sku,
        is_active=True,
        created_at=data["created_at"]
    )

@app.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int):
    key = f"item:{item_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Item not found")
    
    data = r.hgetall(key)
    return ItemOut(
        item_id=int(data["item_id"]),
        name=data["name"],
        description=data["description"] if data["description"] else None,
        price=float(data["price"]),
        stock_quantity=int(data["stock_quantity"]),
        category_id=int(data["category_id"]),
        sku=data["sku"],
        is_active=data["is_active"] == "true",
        created_at=data["created_at"]
    )

@app.get("/items", response_model=List[ItemOut])
def list_items():
    ids = sorted([int(i) for i in r.smembers("items")])
    items = []
    for iid in ids:
        data = r.hgetall(f"item:{iid}")
        if data and data.get("is_active") == "true":
            items.append(ItemOut(
                item_id=int(data["item_id"]),
                name=data["name"],
                description=data["description"] if data["description"] else None,
                price=float(data["price"]),
                stock_quantity=int(data["stock_quantity"]),
                category_id=int(data["category_id"]),
                sku=data["sku"],
                is_active=True,
                created_at=data["created_at"]
            ))
    return items

@app.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, upd: ItemUpdate):
    key = f"item:{item_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Item not found")
    
    if upd.name is not None:
        r.hset(key, "name", upd.name)
    if upd.description is not None:
        r.hset(key, "description", upd.description)
    if upd.price is not None:
        r.hset(key, "price", str(upd.price))
    if upd.stock_quantity is not None:
        r.hset(key, "stock_quantity", str(upd.stock_quantity))
    if upd.category_id is not None:
        if not r.exists(f"category:{upd.category_id}"):
            raise HTTPException(status_code=400, detail="Category not found")
        r.hset(key, "category_id", str(upd.category_id))
    if upd.sku is not None:
        r.hset(key, "sku", upd.sku)
    
    data = r.hgetall(key)
    return ItemOut(
        item_id=int(data["item_id"]),
        name=data["name"],
        description=data["description"] if data["description"] else None,
        price=float(data["price"]),
        stock_quantity=int(data["stock_quantity"]),
        category_id=int(data["category_id"]),
        sku=data["sku"],
        is_active=data["is_active"] == "true",
        created_at=data["created_at"]
    )

# Basket Endpoints
@app.post("/baskets/{customer_id}/items")
def add_to_basket(customer_id: int, basket_item: BasketItemIn):
    # Check if customer exists
    if not r.exists(f"customer:{customer_id}"):
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check if item exists
    if not r.exists(f"item:{basket_item.item_id}"):
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Get or create basket for customer
    basket_key = f"basket:{customer_id}"
    if not r.exists(basket_key):
        basket_data = {
            "basket_id": str(customer_id),
            "customer_id": str(customer_id),
            "created_at": get_timestamp(),
            "updated_at": get_timestamp()
        }
        r.hset(basket_key, mapping=basket_data)
    else:
        r.hset(basket_key, "updated_at", get_timestamp())
    
    # Add item to basket
    basket_item_key = f"basket_item:{customer_id}:{basket_item.item_id}"
    if r.exists(basket_item_key):
        # Update quantity if item already in basket
        current_qty = int(r.hget(basket_item_key, "quantity"))
        new_qty = current_qty + basket_item.quantity
        r.hset(basket_item_key, "quantity", str(new_qty))
    else:
        # Add new item to basket
        item_data = r.hgetall(f"item:{basket_item.item_id}")
        basket_item_data = {
            "item_id": str(basket_item.item_id),
            "quantity": str(basket_item.quantity),
            "unit_price": item_data["price"],
            "added_at": get_timestamp()
        }
        r.hset(basket_item_key, mapping=basket_item_data)
        r.sadd(f"basket_items:{customer_id}", basket_item.item_id)
    
    return {"message": "Item added to basket"}

@app.get("/baskets/{customer_id}", response_model=BasketOut)
def get_basket(customer_id: int):
    basket_key = f"basket:{customer_id}"
    if not r.exists(basket_key):
        raise HTTPException(status_code=404, detail="Basket not found")
    
    basket_data = r.hgetall(basket_key)
    basket_items = []
    total_amount = 0.0
    
    item_ids = r.smembers(f"basket_items:{customer_id}")
    for item_id in item_ids:
        basket_item_key = f"basket_item:{customer_id}:{item_id}"
        basket_item_data = r.hgetall(basket_item_key)
        if basket_item_data:
            item_data = r.hgetall(f"item:{item_id}")
            quantity = int(basket_item_data["quantity"])
            unit_price = float(basket_item_data["unit_price"])
            total_price = quantity * unit_price
            total_amount += total_price
            
            basket_items.append(BasketItemOut(
                item_id=int(item_id),
                item_name=item_data["name"],
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            ))
    
    return BasketOut(
        basket_id=int(basket_data["basket_id"]),
        customer_id=int(basket_data["customer_id"]),
        items=basket_items,
        total_amount=total_amount,
        created_at=basket_data["created_at"],
        updated_at=basket_data["updated_at"]
    )

@app.delete("/baskets/{customer_id}/items/{item_id}")
def remove_from_basket(customer_id: int, item_id: int):
    basket_item_key = f"basket_item:{customer_id}:{item_id}"
    if not r.exists(basket_item_key):
        raise HTTPException(status_code=404, detail="Item not in basket")
    
    r.delete(basket_item_key)
    r.srem(f"basket_items:{customer_id}", item_id)
    
    # Update basket timestamp
    basket_key = f"basket:{customer_id}"
    if r.exists(basket_key):
        r.hset(basket_key, "updated_at", get_timestamp())
    
    return {"message": "Item removed from basket"}

@app.delete("/baskets/{customer_id}")
def clear_basket(customer_id: int):
    basket_key = f"basket:{customer_id}"
    if not r.exists(basket_key):
        raise HTTPException(status_code=404, detail="Basket not found")
    
    # Remove all basket items
    item_ids = r.smembers(f"basket_items:{customer_id}")
    for item_id in item_ids:
        r.delete(f"basket_item:{customer_id}:{item_id}")
    
    r.delete(f"basket_items:{customer_id}")
    r.delete(basket_key)
    
    return {"message": "Basket cleared"}

# Enhanced Order Endpoints
@app.post("/orders", response_model=OrderOut)
def create_order(order: OrderIn):
    order_id = r.incr("order_id")
    timestamp = get_timestamp()
    
    # Create order with enhanced timestamps
    data = {
        "order_id": str(order_id),
        "customer_name": order.customer_name,
        "items": ",".join(order.items),
        "status": "pending",
        "notes": order.notes or "",
        "created_at": timestamp,
        "updated_at": timestamp,
        "placed_at": timestamp,  # Order placed timestamp
    }
    r.hset(f"order:{order_id}", mapping=data)
    r.sadd("orders", order_id)
    
    # Add initial status to history
    add_status_to_history(order_id, "pending", "Order created")
    
    # Get the created order for response
    return get_order_response(order_id)

@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int):
    key = f"order:{order_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Order not found")
    
    return get_order_response(order_id)

@app.get("/orders", response_model=List[OrderOut])
def list_orders():
    ids = sorted([int(i) for i in r.smembers("orders")], key=int)
    orders = []
    for oid in ids:
        data = r.hgetall(f"order:{oid}")
        if data:
            orders.append(get_order_response(oid))
    return orders

@app.patch("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, upd: OrderUpdate):
    key = f"order:{order_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Order not found")

    # Get current status for comparison
    current_data = r.hgetall(key)
    current_status = current_data.get("status")
    
    # Update basic fields
    if upd.customer_name is not None:
        r.hset(key, "customer_name", upd.customer_name)
    if upd.items is not None:
        r.hset(key, "items", ",".join(upd.items))
    if upd.notes is not None:
        r.hset(key, "notes", upd.notes)
    
    # Handle status change with workflow timestamps
    if upd.status is not None and upd.status != current_status:
        r.hset(key, "status", upd.status)
        
        # Update fulfillment workflow timestamp
        update_fulfillment_timestamp(order_id, upd.status)
        
        # Add to status history
        status_note = f"Status changed from {current_status} to {upd.status}"
        if upd.notes:
            status_note += f" - {upd.notes}"
        add_status_to_history(order_id, upd.status, status_note)
    
    # Update the updated_at timestamp
    r.hset(key, "updated_at", get_timestamp())
    
    return get_order_response(order_id)

@app.delete("/orders/{order_id}")
def delete_order(order_id: int):
    key = f"order:{order_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Add cancellation to history before deletion
    add_status_to_history(order_id, "cancelled", "Order deleted")
    
    r.delete(key)
    r.delete(f"order_history:{order_id}")
    r.srem("orders", order_id)
    return {"deleted": order_id}

# New endpoint for advancing order through workflow
@app.post("/orders/{order_id}/advance")
def advance_order_status(order_id: int, notes: Optional[str] = None):
    """Advance order to next status in fulfillment workflow"""
    key = f"order:{order_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Order not found")
    
    current_data = r.hgetall(key)
    current_status = current_data.get("status")
    
    # Define workflow progression
    workflow = {
        "pending": "confirmed",
        "confirmed": "picking", 
        "picking": "packed",
        "packed": "shipped",
        "shipped": "delivered"
    }
    
    if current_status not in workflow:
        raise HTTPException(status_code=400, detail=f"Cannot advance from status: {current_status}")
    
    next_status = workflow[current_status]
    
    # Update status and timestamps
    r.hset(key, "status", next_status)
    r.hset(key, "updated_at", get_timestamp())
    update_fulfillment_timestamp(order_id, next_status)
    
    # Add to history
    advance_note = f"Order advanced to {next_status}"
    if notes:
        advance_note += f" - {notes}"
    add_status_to_history(order_id, next_status, advance_note)
    
    return {"message": f"Order advanced to {next_status}", "order": get_order_response(order_id)}

# New endpoint to get order timeline
@app.get("/orders/{order_id}/timeline")
def get_order_timeline(order_id: int):
    """Get detailed timeline of order status changes"""
    if not r.exists(f"order:{order_id}"):
        raise HTTPException(status_code=404, detail="Order not found")
    
    history = get_order_history(order_id)
    data = r.hgetall(f"order:{order_id}")
    
    timeline = {
        "order_id": order_id,
        "customer_name": data["customer_name"],
        "current_status": data["status"],
        "created_at": data["created_at"],
        "status_changes": [
            {
                "status": h.status,
                "timestamp": h.timestamp,
                "notes": h.notes
            } for h in history
        ],
        "fulfillment_timestamps": {
            "placed_at": data.get("placed_at"),
            "confirmed_at": data.get("confirmed_at"),
            "picked_at": data.get("picked_at"),
            "packed_at": data.get("packed_at"),
            "shipped_at": data.get("shipped_at"),
            "delivered_at": data.get("delivered_at"),
            "cancelled_at": data.get("cancelled_at")
        }
    }
    
    return timeline

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)