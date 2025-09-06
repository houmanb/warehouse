import requests
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentRole(Enum):
    CUSTOMER = "customer"
    FULFILLMENT = "fulfillment"

@dataclass
class WarehouseConfig:
    base_url: str = "http://localhost:8000"
    timeout: int = 30
    retry_attempts: int = 3

class WarehouseClientError(Exception):
    """Custom exception for warehouse client errors"""
    pass

class WarehouseClient:
    """
    Client for interacting with the warehouse REST API
    Supports role-based operations via X-AGENT-ROLE header
    """
    
    def __init__(self, config: WarehouseConfig = None, agent_role: AgentRole = AgentRole.CUSTOMER):
        self.config = config or WarehouseConfig()
        self.agent_role = agent_role
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-AGENT-ROLE": agent_role.value
        })
        
        logger.info(f"Initialized WarehouseClient with role: {agent_role.value}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make HTTP request with error handling and retries"""
        url = f"{self.config.base_url}{endpoint}"
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.config.timeout
                )
                
                response.raise_for_status()
                
                # Handle empty responses
                if not response.content:
                    return {}
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise WarehouseClientError(f"Request failed after {self.config.retry_attempts} attempts: {e}")
        
        raise WarehouseClientError("Unexpected error in request handling")
    
    def health_check(self) -> bool:
        """Check if the warehouse service is healthy"""
        try:
            response = self._make_request("GET", "/health")
            return response.get("ok", False)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    # ==================== CUSTOMER OPERATIONS ====================
    
    def create_customer(self, name: str, email: str, phone: str = None, address: str = None) -> Dict:
        """Create a new customer"""
        data = {
            "name": name,
            "email": email,
            "phone": phone,
            "address": address
        }
        return self._make_request("POST", "/customers", data)
    
    def get_customer(self, customer_id: int) -> Dict:
        """Get customer by ID"""
        return self._make_request("GET", f"/customers/{customer_id}")
    
    def list_customers(self) -> List[Dict]:
        """List all customers"""
        return self._make_request("GET", "/customers")
    
    def update_customer(self, customer_id: int, name: str = None, email: str = None, 
                       phone: str = None, address: str = None) -> Dict:
        """Update customer information"""
        data = {}
        if name is not None:
            data["name"] = name
        if email is not None:
            data["email"] = email
        if phone is not None:
            data["phone"] = phone
        if address is not None:
            data["address"] = address
        
        return self._make_request("PATCH", f"/customers/{customer_id}", data)
    
    # ==================== CATEGORY OPERATIONS ====================
    
    def list_categories(self) -> List[Dict]:
        """List all categories"""
        return self._make_request("GET", "/categories")
    
    def get_category(self, category_id: int) -> Dict:
        """Get category by ID"""
        return self._make_request("GET", f"/categories/{category_id}")
    
    # ==================== ITEM OPERATIONS ====================
    
    def list_items(self) -> List[Dict]:
        """List all active items"""
        return self._make_request("GET", "/items")
    
    def get_item(self, item_id: int) -> Dict:
        """Get item by ID"""
        return self._make_request("GET", f"/items/{item_id}")
    
    # ==================== BASKET OPERATIONS ====================
    
    def add_to_basket(self, customer_id: int, item_id: int, quantity: int) -> Dict:
        """Add item to customer's basket"""
        data = {
            "item_id": item_id,
            "quantity": quantity
        }
        return self._make_request("POST", f"/baskets/{customer_id}/items", data)
    
    def get_basket(self, customer_id: int) -> Dict:
        """Get customer's basket"""
        return self._make_request("GET", f"/baskets/{customer_id}")
    
    def remove_from_basket(self, customer_id: int, item_id: int) -> Dict:
        """Remove item from customer's basket"""
        return self._make_request("DELETE", f"/baskets/{customer_id}/items/{item_id}")
    
    def clear_basket(self, customer_id: int) -> Dict:
        """Clear all items from customer's basket"""
        return self._make_request("DELETE", f"/baskets/{customer_id}")
    
    # ==================== ORDER OPERATIONS ====================
    
    def create_order(self, customer_name: str, items: List[str], notes: str = None) -> Dict:
        """Create a new order"""
        data = {
            "customer_name": customer_name,
            "items": items,
            "notes": notes
        }
        return self._make_request("POST", "/orders", data)
    
    def get_order(self, order_id: int) -> Dict:
        """Get order by ID"""
        return self._make_request("GET", f"/orders/{order_id}")
    
    def list_orders(self) -> List[Dict]:
        """List all orders"""
        return self._make_request("GET", "/orders")
    
    def update_order(self, order_id: int, customer_name: str = None, items: List[str] = None, 
                    status: str = None, notes: str = None) -> Dict:
        """Update order information"""
        data = {}
        if customer_name is not None:
            data["customer_name"] = customer_name
        if items is not None:
            data["items"] = items
        if status is not None:
            data["status"] = status
        if notes is not None:
            data["notes"] = notes
        
        return self._make_request("PATCH", f"/orders/{order_id}", data)
    
    def cancel_order(self, order_id: int) -> Dict:
        """Cancel/delete an order"""
        return self._make_request("DELETE", f"/orders/{order_id}")
    
    def advance_order(self, order_id: int, notes: str = None) -> Dict:
        """Advance order to next status in fulfillment workflow"""
        params = {"notes": notes} if notes else None
        return self._make_request("POST", f"/orders/{order_id}/advance", params=params)
    
    def get_order_timeline(self, order_id: int) -> Dict:
        """Get detailed timeline of order status changes"""
        return self._make_request("GET", f"/orders/{order_id}/timeline")
    
    # ==================== CONVENIENCE METHODS ====================
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all orders with pending status"""
        orders = self.list_orders()
        return [order for order in orders if order.get("status") == "pending"]
    
    def get_orders_by_status(self, status: str) -> List[Dict]:
        """Get all orders with specific status"""
        orders = self.list_orders()
        return [order for order in orders if order.get("status") == status]
    
    def get_customer_orders(self, customer_name: str) -> List[Dict]:
        """Get all orders for a specific customer"""
        orders = self.list_orders()
        return [order for order in orders if order.get("customer_name") == customer_name]
    
    def get_random_item(self) -> Dict:
        """Get a random item for simulation purposes"""
        import random
        items = self.list_items()
        return random.choice(items) if items else None
    
    def get_random_customer(self) -> Dict:
        """Get a random customer for simulation purposes"""
        import random
        customers = self.list_customers()
        active_customers = [c for c in customers if c.get("is_active", True)]
        return random.choice(active_customers) if active_customers else None

# ==================== ROLE-SPECIFIC CLIENT CLASSES ====================

class CustomerAgentClient(WarehouseClient):
    """Client specifically for customer agents"""
    
    def __init__(self, config: WarehouseConfig = None):
        super().__init__(config, AgentRole.CUSTOMER)
    
    def place_random_order(self, customer_name: str = None) -> Dict:
        """Place a random order for simulation"""
        import random
        
        # Get random customer if not specified
        if not customer_name:
            customer = self.get_random_customer()
            customer_name = customer["name"] if customer else "Test Customer"
        
        # Get random items (1-3 items)
        items = self.list_items()
        if not items:
            raise WarehouseClientError("No items available for ordering")
        
        num_items = random.randint(1, min(3, len(items)))
        selected_items = random.sample(items, num_items)
        item_names = [item["name"] for item in selected_items]
        
        logger.info(f"Customer {customer_name} placing order for: {item_names}")
        return self.create_order(customer_name, item_names)

class FulfillmentAgentClient(WarehouseClient):
    """Client specifically for fulfillment agents"""
    
    def __init__(self, config: WarehouseConfig = None):
        super().__init__(config, AgentRole.FULFILLMENT)
    
    def process_next_order(self) -> Optional[Dict]:
        """Process the next pending order in the queue"""
        pending_orders = self.get_pending_orders()
        
        if not pending_orders:
            logger.info("No pending orders to process")
            return None
        
        # Get oldest pending order
        oldest_order = min(pending_orders, key=lambda x: x["created_at"])
        order_id = oldest_order["order_id"]
        
        logger.info(f"Processing order {order_id} for {oldest_order['customer_name']}")
        return self.advance_order(order_id, "Automated fulfillment processing")
    
    def process_orders_by_status(self, current_status: str) -> List[Dict]:
        """Process all orders with a specific status"""
        orders = self.get_orders_by_status(current_status)
        results = []
        
        for order in orders:
            try:
                result = self.advance_order(order["order_id"], f"Batch processing from {current_status}")
                results.append(result)
                logger.info(f"Advanced order {order['order_id']} from {current_status}")
            except Exception as e:
                logger.error(f"Failed to advance order {order['order_id']}: {e}")
        
        return results

# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    # Example usage
    config = WarehouseConfig(base_url="http://localhost:8000")
    
    # Test customer client
    customer_client = CustomerAgentClient(config)
    if customer_client.health_check():
        print("✅ Warehouse service is healthy")
        
        # Place a random order
        try:
            order = customer_client.place_random_order("John Doe")
            print(f"Created order: {order['order_id']}")
        except Exception as e:
            print(f"Failed to create order: {e}")
    
    # Test fulfillment client
    fulfillment_client = FulfillmentAgentClient(config)
    try:
        result = fulfillment_client.process_next_order()
        if result:
            print(f"Processed order: {result}")
        else:
            print("No orders to process")
    except Exception as e:
        print(f"Failed to process order: {e}")