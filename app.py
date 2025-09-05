from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import redis

app = FastAPI(title="Warehouse API", version="1.0.0")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

class OrderIn(BaseModel):
    customer_name: str
    items: List[str]

class OrderUpdate(BaseModel):
    customer_name: str | None = None
    items: List[str] | None = None
    status: str | None = None

class OrderOut(BaseModel):
    order_id: int
    customer_name: str
    items: List[str]
    status: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/orders", response_model=OrderOut)
def create_order(order: OrderIn):
    order_id = r.incr("order_id")
    data = {
        "order_id": str(order_id),
        "customer_name": order.customer_name,
        "items": ",".join(order.items),
        "status": "pending",
    }
    r.hset(f"order:{order_id}", mapping=data)
    r.sadd("orders", order_id)
    return {
        "order_id": order_id,
        "customer_name": order.customer_name,
        "items": order.items,
        "status": "pending",
    }

@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int):
    key = f"order:{order_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Order not found")
    data = r.hgetall(key)
    return {
        "order_id": int(data["order_id"]),
        "customer_name": data["customer_name"],
        "items": data["items"].split(",") if data.get("items") else [],
        "status": data["status"],
    }

@app.get("/orders", response_model=List[OrderOut])
def list_orders():
    ids = sorted([int(i) for i in r.smembers("orders")], key=int)
    out: List[OrderOut] = []
    for oid in ids:
        data = r.hgetall(f"order:{oid}")
        if data:
            out.append({
                "order_id": int(data["order_id"]),
                "customer_name": data["customer_name"],
                "items": data["items"].split(",") if data.get("items") else [],
                "status": data["status"],
            })
    return out

@app.patch("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, upd: OrderUpdate):
    key = f"order:{order_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Order not found")

    if upd.customer_name is not None:
        r.hset(key, "customer_name", upd.customer_name)
    if upd.items is not None:
        r.hset(key, "items", ",".join(upd.items))
    if upd.status is not None:
        r.hset(key, "status", upd.status)

    data = r.hgetall(key)
    return {
        "order_id": int(data["order_id"]),
        "customer_name": data["customer_name"],
        "items": data["items"].split(",") if data.get("items") else [],
        "status": data["status"],
    }

@app.delete("/orders/{order_id}")
def delete_order(order_id: int):
    key = f"order:{order_id}"
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Order not found")
    r.delete(key)
    r.srem("orders", order_id)
    return {"deleted": order_id}
