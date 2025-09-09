from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Annotated
from statemachine import StateMachine, State
from statemachine.exceptions import TransitionNotAllowed
import redis
import json
import uuid
import os
from datetime import datetime
from enum import Enum
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="State Machine Warehouse Service", version="1.0.0")

# Redis connection with environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

class Role(str, Enum):
    CUSTOMER = "customer"
    FULFILLMENT = "fulfillment"

# ============================================================================
# STATE MACHINE DEFINITION
# ============================================================================

class OrderStateMachine(StateMachine):
    """Declarative state machine for order workflow"""
    
    # Define states
    pending = State(initial=True)
    confirmed = State()
    picking = State()
    packed = State()
    shipped = State()
    delivered = State()
    cancelled = State(final=True)
    halted = State()
    returned = State(final=True)
    
    # Customer transitions
    cancel_from_pending = pending.to(cancelled)
    cancel_from_confirmed = confirmed.to(cancelled)
    cancel_from_picking = picking.to(cancelled)
    cancel_from_packed = packed.to(cancelled)
    return_order = delivered.to(returned)
    
    # Fulfillment forward transitions
    confirm = pending.to(confirmed)
    start_picking = confirmed.to(picking)
    pack = picking.to(packed)
    ship = packed.to(shipped)
    deliver = shipped.to(delivered)
    
    # Fulfillment halt transitions
    halt_from_pending = pending.to(halted)
    halt_from_confirmed = confirmed.to(halted)
    halt_from_picking = picking.to(halted)
    halt_from_packed = packed.to(halted)
    
    # Resume transitions (fulfillment)
    resume_to_pending = halted.to(pending)
    resume_to_confirmed = halted.to(confirmed)
    resume_to_picking = halted.to(picking)
    resume_to_packed = halted.to(packed)

# ============================================================================
# ROLE-BASED TRANSITION PERMISSIONS
# ============================================================================

# Map transitions to allowed roles
TRANSITION_PERMISSIONS = {
    # Customer transitions
    "cancel_from_pending": [Role.CUSTOMER],
    "cancel_from_confirmed": [Role.CUSTOMER],
    "cancel_from_picking": [Role.CUSTOMER],
    "cancel_from_packed": [Role.CUSTOMER],
    "return_order": [Role.CUSTOMER],
    
    # Fulfillment transitions
    "confirm": [Role.FULFILLMENT],
    "start_picking": [Role.FULFILLMENT],
    "pack": [Role.FULFILLMENT],
    "ship": [Role.FULFILLMENT],
    "deliver": [Role.FULFILLMENT],
    "halt_from_pending": [Role.FULFILLMENT],
    "halt_from_confirmed": [Role.FULFILLMENT],
    "halt_from_picking": [Role.FULFILLMENT],
    "halt_from_packed": [Role.FULFILLMENT],
    "resume_to_pending": [Role.FULFILLMENT],
    "resume_to_confirmed": [Role.FULFILLMENT],
    "resume_to_picking": [Role.FULFILLMENT],
    "resume_to_packed": [Role.FULFILLMENT],
}

# ============================================================================
# ORDER MODEL FOR STATE MACHINE
# ============================================================================

class OrderModel:
    """Model object that holds order state for the state machine"""
    def __init__(self, order_id: str, state: str = "pending"):
        self.order_id = order_id
        self.state = state

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class OrderCreate(BaseModel):
    customer_name: str
    items: List[str]
    notes: Optional[str] = None

class OrderResponse(BaseModel):
    order_id: str
    customer_name: str
    items: List[str]
    current_state: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str
    history: List[Dict]
    available_transitions: Optional[List[Dict]] = None

class TransitionRequest(BaseModel):
    transition: str
    notes: Optional[str] = None
    agent_id: Optional[str] = None

class QueueTask(BaseModel):
    task_id: str
    order_id: str
    transition: str
    role: Role
    agent_id: Optional[str] = None
    created_at: str
    notes: Optional[str] = None

# ============================================================================
# QUEUE MANAGEMENT WITH PROPER CONCURRENCY
# ============================================================================

class TaskQueue:
    """Redis-based task queue with atomic operations and role filtering"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.lock_timeout = 300  # 5 minutes
    
    def _get_queue_key(self, role: Role) -> str:
        """Get role-specific queue key"""
        return f"transition_queue:{role.value}"
    
    def _get_processing_key(self, agent_id: str) -> str:
        """Get agent-specific processing key"""
        return f"processing:{agent_id}"
    
    def enqueue_transition(self, order_id: str, transition: str, role: Role, 
                          agent_id: str = None, notes: str = None) -> str:
        """Add a transition task to role-specific queue"""
        task_id = str(uuid.uuid4())
        task = QueueTask(
            task_id=task_id,
            order_id=order_id,
            transition=transition,
            role=role,
            agent_id=agent_id,
            created_at=datetime.utcnow().isoformat(),
            notes=notes
        )
        
        # Add to role-specific queue
        queue_key = self._get_queue_key(role)
        self.redis.lpush(queue_key, task.model_dump_json())
        logger.info(f"Enqueued transition task {task_id}: {transition} for order {order_id} in {role.value} queue")
        return task_id
    
    def claim_next_task(self, agent_id: str, role: Role) -> Optional[QueueTask]:
        """Atomically claim the next available task from role-specific queue"""
        queue_key = self._get_queue_key(role)
        processing_key = self._get_processing_key(agent_id)
        
        # Use Lua script for atomic operation
        lua_script = """
        local queue_key = KEYS[1]
        local processing_key = KEYS[2]
        local timeout = ARGV[1]
        
        local task_json = redis.call('RPOP', queue_key)
        if task_json then
            redis.call('SET', processing_key, task_json, 'EX', timeout)
            return task_json
        else
            return nil
        end
        """
        
        task_json = self.redis.eval(lua_script, 2, queue_key, processing_key, self.lock_timeout)
        
        if task_json:
            try:
                task = QueueTask.model_validate_json(task_json)
                logger.info(f"Agent {agent_id} claimed task {task.task_id}")
                return task
            except Exception as e:
                logger.error(f"Failed to parse task JSON: {e}")
                # Remove invalid task from processing
                self.redis.delete(processing_key)
                return None
        return None
    
    def complete_task(self, agent_id: str, task_id: str):
        """Mark task as completed and remove from processing"""
        processing_key = self._get_processing_key(agent_id)
        self.redis.delete(processing_key)
        logger.info(f"Agent {agent_id} completed task {task_id}")
    
    def release_task(self, agent_id: str, role: Role, reason: str = None):
        """Release a claimed task back to the queue"""
        processing_key = self._get_processing_key(agent_id)
        queue_key = self._get_queue_key(role)
        
        # Use Lua script for atomic release
        lua_script = """
        local processing_key = KEYS[1]
        local queue_key = KEYS[2]
        
        local task_json = redis.call('GET', processing_key)
        if task_json then
            redis.call('DEL', processing_key)
            redis.call('RPUSH', queue_key, task_json)
            return 1
        else
            return 0
        end
        """
        
        result = self.redis.eval(lua_script, 2, processing_key, queue_key)
        if result:
            logger.info(f"Agent {agent_id} released task. Reason: {reason}")
            return True
        return False
    
    def get_queue_status(self) -> Dict:
        """Get current queue status for all roles"""
        status = {}
        total_queued = 0
        total_processing = 0
        
        for role in Role:
            queue_key = self._get_queue_key(role)
            queued = self.redis.llen(queue_key)
            total_queued += queued
            status[f"{role.value}_queued"] = queued
        
        processing_keys = self.redis.keys("processing:*")
        total_processing = len(processing_keys)
        
        status.update({
            "total_queued": total_queued,
            "total_processing": total_processing,
            "total_tasks": total_queued + total_processing
        })
        
        return status

# ============================================================================
# ORDER MANAGEMENT WITH PROPER ERROR HANDLING
# ============================================================================

class OrderManager:
    """Manages order state and persistence with proper concurrency control"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def create_order(self, order_data: OrderCreate) -> str:
        """Create a new order"""
        order_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        order = {
            "order_id": order_id,
            "customer_name": order_data.customer_name,
            "items": json.dumps(order_data.items),
            "current_state": "pending",
            "notes": order_data.notes or "",
            "created_at": timestamp,
            "updated_at": timestamp,
            "history": json.dumps([{
                "state": "pending",
                "timestamp": timestamp,
                "notes": "Order created"
            }])
        }
        
        self.redis.hset(f"order:{order_id}", mapping=order)
        self.redis.sadd("orders", order_id)
        
        logger.info(f"Created order {order_id} for {order_data.customer_name}")
        return order_id
    
    def get_order(self, order_id: str) -> Optional[OrderResponse]:
        """Retrieve an order with error handling"""
        order_data = self.redis.hgetall(f"order:{order_id}")
        if not order_data:
            return None
        
        try:
            return OrderResponse(
                order_id=order_data["order_id"],
                customer_name=order_data["customer_name"],
                items=json.loads(order_data["items"]),
                current_state=order_data["current_state"],
                notes=order_data["notes"],
                created_at=order_data["created_at"],
                updated_at=order_data["updated_at"],
                history=json.loads(order_data["history"])
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing order {order_id}: {e}")
            return None
    
    def atomic_state_transition(self, order_id: str, transition: str, notes: str = None) -> bool:
        """Atomically execute state transition and update order"""
        
        # Use optimistic locking with WATCH
        pipe = self.redis.pipeline()
        order_key = f"order:{order_id}"
        
        try:
            # Watch the order for changes
            pipe.watch(order_key)
            
            # Get current order state
            order_data = self.redis.hgetall(order_key)
            if not order_data:
                pipe.unwatch()
                logger.error(f"Order {order_id} not found")
                return False
            
            current_state = order_data["current_state"]
            logger.info(f"Attempting transition {transition} from state {current_state} for order {order_id}")
            
            # Create state machine with model that has current state
            model = OrderModel(order_id, current_state)
            sm = OrderStateMachine(model)
            
            # Check if transition exists
            if not hasattr(sm, transition):
                pipe.unwatch()
                logger.error(f"Transition {transition} not found")
                return False
            
            # Execute transition
            try:
                transition_func = getattr(sm, transition)
                transition_func()
                new_state = sm.current_state.id
            except (TransitionNotAllowed, AttributeError) as e:
                pipe.unwatch()
                logger.error(f"Transition {transition} failed: {e}")
                return False
                
            timestamp = datetime.utcnow().isoformat()
            
            # Parse current history
            try:
                current_history = json.loads(order_data["history"])
            except json.JSONDecodeError:
                pipe.unwatch()
                logger.error(f"Invalid history JSON for order {order_id}")
                return False
            
            # Add new history entry
            current_history.append({
                "state": new_state,
                "timestamp": timestamp,
                "notes": notes or f"Transitioned to {new_state}"
            })
            
            # Start transaction
            pipe.multi()
            
            # Update order atomically
            pipe.hset(order_key, mapping={
                "current_state": new_state,
                "updated_at": timestamp,
                "history": json.dumps(current_history)
            })
            
            # Execute transaction
            pipe.execute()
            
            logger.info(f"Order {order_id} transitioned from {current_state} to {new_state}")
            return True
            
        except Exception as e:
            logger.error(f"State transition failed for order {order_id}: {e}")
            try:
                pipe.unwatch()
            except:
                pass
            return False
    
    def list_orders(self, limit: int = 50) -> List[OrderResponse]:
        """List all orders with error handling"""
        order_ids = list(self.redis.smembers("orders"))[:limit]
        orders = []
        for order_id in order_ids:
            order = self.get_order(order_id)
            if order:
                orders.append(order)
        return orders
    
    def get_available_transitions(self, order_id: str, role: Role) -> List[Dict]:
        """Get available transitions for an order based on current state and role"""
        order = self.get_order(order_id)
        if not order:
            return []
        
        # Create state machine with model that has current state
        model = OrderModel(order_id, order.current_state)
        sm = OrderStateMachine(model)
        
        # Get all possible transitions and filter by what's available from current state
        available = []
        for transition_name, allowed_roles in TRANSITION_PERMISSIONS.items():
            if role in allowed_roles:
                # Check if this transition is available from current state
                if hasattr(sm, transition_name):
                    try:
                        # Create a test state machine to see where this transition leads
                        test_model = OrderModel(order_id, order.current_state)
                        test_sm = OrderStateMachine(test_model)
                        
                        # Try to execute the transition to get destination state
                        transition_func = getattr(test_sm, transition_name)
                        transition_func()
                        dest_state = test_sm.current_state.id
                        
                        available.append({
                            "transition": transition_name,
                            "from_state": order.current_state,
                            "to_state": dest_state,
                            "description": f"Transition from {order.current_state} to {dest_state}"
                        })
                    except Exception:
                        # Transition not available from this state, skip it
                        continue
        
        return available

# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_role(x_agent_role: Annotated[str, Header()]) -> Role:
    """Extract and validate role from header"""
    try:
        return Role(x_agent_role.lower())
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid role. Must be 'customer' or 'fulfillment'"
        )

# Initialize services
task_queue = TaskQueue(r)
order_manager = OrderManager(r)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
def health_check():
    return {"ok": True, "status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/orders", response_model=OrderResponse)
def create_order(order_data: OrderCreate, role: Role = Depends(get_role)):
    """Create a new order"""
    order_id = order_manager.create_order(order_data)
    order = order_manager.get_order(order_id)
    if order:
        order.available_transitions = order_manager.get_available_transitions(order_id, role)
    return order

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, role: Role = Depends(get_role)):
    """Get order by ID with available transitions"""
    order = order_manager.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.available_transitions = order_manager.get_available_transitions(order_id, role)
    return order

@app.get("/orders", response_model=List[OrderResponse])
def list_orders(limit: int = 50, role: Role = Depends(get_role)):
    """List all orders with available transitions"""
    orders = order_manager.list_orders(limit)
    for order in orders:
        order.available_transitions = order_manager.get_available_transitions(order.order_id, role)
    return orders

@app.post("/orders/{order_id}/transition")
def request_transition(order_id: str, request: TransitionRequest, role: Role = Depends(get_role)):
    """Request a state transition for an order with proper validation"""
    
    # Validate order exists
    order = order_manager.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check role permission BEFORE any other validation
    if role not in TRANSITION_PERMISSIONS.get(request.transition, []):
        raise HTTPException(
            status_code=403, 
            detail=f"Role '{role.value}' not allowed to perform transition '{request.transition}'"
        )
    
    # Validate transition is available from current state
    model = OrderModel(order_id, order.current_state)
    sm = OrderStateMachine(model)
    
    # Check if transition exists and can be executed
    if not hasattr(sm, request.transition):
        raise HTTPException(
            status_code=400, 
            detail=f"Transition '{request.transition}' not found"
        )
    
    # Try to validate transition can be executed (without actually executing it)
    try:
        test_model = OrderModel(order_id, order.current_state)
        test_sm = OrderStateMachine(test_model)
        transition_func = getattr(test_sm, request.transition)
        transition_func()  # This will raise TransitionNotAllowed if invalid
    except Exception:
        raise HTTPException(
            status_code=400, 
            detail=f"Transition '{request.transition}' not allowed from state '{order.current_state}'"
        )
    
    # Enqueue the transition to role-specific queue
    task_id = task_queue.enqueue_transition(
        order_id=order_id,
        transition=request.transition,
        role=role,
        agent_id=request.agent_id,
        notes=request.notes
    )
    
    queue_status = task_queue.get_queue_status()
    
    return {
        "message": f"Transition '{request.transition}' queued for order {order_id}",
        "task_id": task_id,
        "queue_position": queue_status.get(f"{role.value}_queued", 0)
    }

@app.post("/queue/claim")
def claim_next_task(agent_id: str, role: Role = Depends(get_role)):
    """Claim the next task from role-specific queue"""
    task = task_queue.claim_next_task(agent_id, role)
    if not task:
        return {"message": f"No {role.value} tasks available", "agent_id": agent_id}
    
    return {
        "message": f"Claimed task {task.task_id}",
        "task": task,
        "expires_in_seconds": task_queue.lock_timeout
    }

@app.post("/queue/complete")
def complete_task(task_id: str, agent_id: str, role: Role = Depends(get_role)):
    """Complete a claimed task with atomic state transition"""
    
    # Get the task from processing
    processing_key = f"processing:{agent_id}"
    task_json = task_queue.redis.get(processing_key)
    if not task_json:
        raise HTTPException(status_code=404, detail="No task claimed by this agent")
    
    try:
        task = QueueTask.model_validate_json(task_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid task data: {e}")
    
    if task.task_id != task_id:
        raise HTTPException(status_code=400, detail="Task ID mismatch")
    
    # Execute atomic state transition
    success = order_manager.atomic_state_transition(
        order_id=task.order_id,
        transition=task.transition,
        notes=task.notes
    )
    
    if not success:
        # Release task back to queue on failure
        task_queue.release_task(agent_id, role, "Transition execution failed")
        raise HTTPException(status_code=400, detail="State transition failed")
    
    # Mark task as complete
    task_queue.complete_task(agent_id, task_id)
    
    # Get updated order
    updated_order = order_manager.get_order(task.order_id)
    
    return {
        "message": f"Task {task_id} completed successfully",
        "order_id": task.order_id,
        "transition": task.transition,
        "new_state": updated_order.current_state if updated_order else "unknown"
    }

@app.post("/queue/release")
def release_task(agent_id: str, reason: str = "Manual release", role: Role = Depends(get_role)):
    """Release a claimed task back to the queue"""
    if task_queue.release_task(agent_id, role, reason):
        return {"message": f"Task released by agent {agent_id}", "reason": reason}
    else:
        raise HTTPException(status_code=404, detail="No task claimed by this agent")

@app.get("/queue/status")
def get_queue_status():
    """Get current queue status"""
    return task_queue.get_queue_status()

@app.get("/state-machine/info")
def get_state_machine_info():
    """Get state machine configuration"""
    temp_model = OrderModel("temp", "pending")
    temp_sm = OrderStateMachine(temp_model)
    
    return {
        "states": [state.id for state in temp_sm.states],
        "transitions": list(TRANSITION_PERMISSIONS.keys()),
        "role_permissions": {
            role.value: [
                transition for transition, roles in TRANSITION_PERMISSIONS.items() 
                if role in roles
            ]
            for role in Role
        }
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting State Machine Warehouse Service")
    uvicorn.run(app, host="0.0.0.0", port=8000)
