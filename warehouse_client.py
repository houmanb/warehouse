import requests
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
import time

class WarehouseClient:
    """
    Python client for the State Machine Warehouse Service.
    Supports 'customer' and 'fulfillment' agent roles via X-AGENT-ROLE header.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", role: str = "customer"):
        """
        Initialize warehouse client.
        
        Args:
            base_url: Base URL of the warehouse API
            role: Agent role - 'customer' or 'fulfillment'
        """
        self.base_url = base_url.rstrip('/')
        self.role = role
        self.session = requests.Session()
        
        # Set default headers including role
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-AGENT-ROLE': role
        })
        
        self.logger = logging.getLogger(f"warehouse_client_{role}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Handle business logic errors with helpful messages
            if response.status_code == 400:
                error_data = response.json() if response.content else {}
                error_detail = error_data.get("detail", "Bad request")
                raise ValueError(error_detail)
            
            elif response.status_code == 403:
                error_data = response.json() if response.content else {}
                error_detail = error_data.get("detail", "Access denied")
                raise PermissionError(f"Role '{self.role}' access denied: {error_detail}")
            
            elif response.status_code == 404:
                error_data = response.json() if response.content else {}
                error_detail = error_data.get("detail", "Not found")
                raise ValueError(error_detail)
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"{method} {url} failed: {e}")
            raise
    
    # ============================================================================
    # BASIC API OPERATIONS
    # ============================================================================
    
    def health_check(self) -> Dict:
        """Check API health status."""
        return self._make_request("GET", "/health")
    
    def get_state_machine_info(self) -> Dict:
        """Get state machine configuration and role permissions."""
        return self._make_request("GET", "/state-machine/info")
    
    # ============================================================================
    # ORDER OPERATIONS
    # ============================================================================
    
    def create_order(self, customer_name: str, items: List[str], notes: str = None) -> Dict:
        """Create a new order."""
        data = {
            "customer_name": customer_name,
            "items": items,
            "notes": notes
        }
        return self._make_request("POST", "/orders", json=data)
    
    def get_order(self, order_id: str) -> Dict:
        """Get order details with available transitions for current role."""
        return self._make_request("GET", f"/orders/{order_id}")
    
    def list_orders(self, limit: int = 50) -> List[Dict]:
        """List orders with available transitions for current role."""
        params = {"limit": limit}
        return self._make_request("GET", "/orders", params=params)
    
    # ============================================================================
    # STATE TRANSITION OPERATIONS
    # ============================================================================
    
    def request_transition(self, order_id: str, transition: str, 
                          notes: str = None, agent_id: str = None) -> Dict:
        """Request a state transition for an order."""
        data = {
            "transition": transition,
            "notes": notes,
            "agent_id": agent_id
        }
        return self._make_request("POST", f"/orders/{order_id}/transition", json=data)
    
    # ============================================================================
    # QUEUE MANAGEMENT OPERATIONS
    # ============================================================================
    
    def claim_next_task(self, agent_id: str) -> Dict:
        """Claim the next task from role-specific queue."""
        params = {"agent_id": agent_id}
        return self._make_request("POST", "/queue/claim", params=params)
    
    def complete_task(self, task_id: str, agent_id: str) -> Dict:
        """Complete a claimed task."""
        params = {"task_id": task_id, "agent_id": agent_id}
        return self._make_request("POST", "/queue/complete", params=params)
    
    def release_task(self, agent_id: str, reason: str = "Manual release") -> Dict:
        """Release a claimed task back to the queue."""
        params = {"agent_id": agent_id, "reason": reason}
        return self._make_request("POST", "/queue/release", params=params)
    
    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        return self._make_request("GET", "/queue/status")
    
    # ============================================================================
    # CONVENIENCE METHODS FOR CUSTOMERS
    # ============================================================================
    
    def cancel_order(self, order_id: str, reason: str = "Customer cancellation") -> Dict:
        """
        Cancel an order by requesting appropriate cancellation transition.
        Will determine the correct transition based on current state.
        """
        order = self.get_order(order_id)
        current_state = order['current_state']
        
        # Map states to cancellation transitions
        cancel_transitions = {
            'pending': 'cancel_from_pending',
            'confirmed': 'cancel_from_confirmed',
            'picking': 'cancel_from_picking',
            'packed': 'cancel_from_packed'
        }
        
        if current_state in cancel_transitions:
            transition = cancel_transitions[current_state]
            return self.request_transition(order_id, transition, notes=reason)
        elif current_state == 'delivered':
            return self.request_transition(order_id, 'return_order', notes=reason)
        else:
            raise ValueError(f"Cannot cancel order in state '{current_state}'")
    
    def return_order(self, order_id: str, reason: str = "Customer return") -> Dict:
        """Return a delivered order."""
        return self.request_transition(order_id, 'return_order', notes=reason)
    
    def get_my_orders(self, customer_name: str) -> List[Dict]:
        """Get orders for a specific customer (filter by customer_name)."""
        all_orders = self.list_orders()
        return [order for order in all_orders if order.get('customer_name') == customer_name]
    
    # ============================================================================
    # CONVENIENCE METHODS FOR FULFILLMENT
    # ============================================================================
    
    def confirm_order(self, order_id: str, notes: str = None) -> Dict:
        """Confirm a pending order."""
        return self.request_transition(order_id, 'confirm', notes=notes)
    
    def start_picking(self, order_id: str, notes: str = None) -> Dict:
        """Start picking process for confirmed order."""
        return self.request_transition(order_id, 'start_picking', notes=notes)
    
    def pack_order(self, order_id: str, notes: str = None) -> Dict:
        """Pack a picked order."""
        return self.request_transition(order_id, 'pack', notes=notes)
    
    def ship_order(self, order_id: str, notes: str = None) -> Dict:
        """Ship a packed order."""
        return self.request_transition(order_id, 'ship', notes=notes)
    
    def deliver_order(self, order_id: str, notes: str = None) -> Dict:
        """Mark order as delivered."""
        return self.request_transition(order_id, 'deliver', notes=notes)
    
    def halt_order(self, order_id: str, reason: str = None) -> Dict:
        """Halt an order (emergency stop)."""
        order = self.get_order(order_id)
        current_state = order['current_state']
        
        halt_transitions = {
            'pending': 'halt_from_pending',
            'confirmed': 'halt_from_confirmed',
            'picking': 'halt_from_picking',
            'packed': 'halt_from_packed'
        }
        
        if current_state in halt_transitions:
            transition = halt_transitions[current_state]
            return self.request_transition(order_id, transition, notes=reason)
        else:
            raise ValueError(f"Cannot halt order in state '{current_state}'")
    
    def resume_order(self, order_id: str, target_state: str, notes: str = None) -> Dict:
        """Resume a halted order to a specific state."""
        resume_transitions = {
            'pending': 'resume_to_pending',
            'confirmed': 'resume_to_confirmed',
            'picking': 'resume_to_picking',
            'packed': 'resume_to_packed'
        }
        
        if target_state in resume_transitions:
            transition = resume_transitions[target_state]
            return self.request_transition(order_id, transition, notes=notes)
        else:
            raise ValueError(f"Cannot resume to state '{target_state}'")
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all orders in pending state."""
        all_orders = self.list_orders()
        return [order for order in all_orders if order.get('current_state') == 'pending']
    
    def get_orders_by_state(self, state: str) -> List[Dict]:
        """Get orders filtered by specific state."""
        all_orders = self.list_orders()
        return [order for order in all_orders if order.get('current_state') == state]
    
    # ============================================================================
    # WORKER/AGENT AUTOMATION
    # ============================================================================
    
    def process_next_task(self, agent_id: str) -> Dict:
        """
        Claim and process the next available task for this role.
        Returns task details and completion result.
        """
        # Claim next task
        claim_result = self.claim_next_task(agent_id)
        
        if 'task' not in claim_result:
            return claim_result  # No tasks available
        
        task = claim_result['task']
        
        try:
            # Complete the task
            complete_result = self.complete_task(task['task_id'], agent_id)
            
            return {
                'action': 'task_completed',
                'task': task,
                'result': complete_result
            }
            
        except Exception as e:
            # Release task back to queue on failure
            try:
                self.release_task(agent_id, f"Failed to complete: {str(e)}")
            except:
                pass  # Release might fail if task already released
            
            return {
                'action': 'task_failed',
                'task': task,
                'error': str(e)
            }
    
    def run_worker(self, agent_id: str, max_tasks: int = None, 
                   poll_interval: float = 1.0) -> List[Dict]:
        """
        Run as a worker agent, continuously processing tasks.
        
        Args:
            agent_id: Unique identifier for this worker
            max_tasks: Maximum number of tasks to process (None for unlimited)
            poll_interval: Seconds to wait between checking for new tasks
            
        Returns:
            List of processed task results
        """
        if self.role not in ['fulfillment']:
            self.logger.warning(f"Worker mode typically used by fulfillment agents, not {self.role}")
        
        processed_tasks = []
        task_count = 0
        
        self.logger.info(f"Starting worker {agent_id} (role: {self.role})")
        
        try:
            while max_tasks is None or task_count < max_tasks:
                result = self.process_next_task(agent_id)
                
                if result.get('action') == 'task_completed':
                    task_count += 1
                    processed_tasks.append(result)
                    self.logger.info(f"Completed task {result['task']['task_id']}: "
                                   f"{result['task']['transition']} for order {result['task']['order_id']}")
                
                elif result.get('action') == 'task_failed':
                    task_count += 1
                    processed_tasks.append(result)
                    self.logger.error(f"Failed task {result['task']['task_id']}: {result['error']}")
                
                else:
                    # No tasks available
                    if task_count == 0:
                        self.logger.info("No tasks available")
                        break
                    else:
                        self.logger.info("No more tasks available, waiting...")
                        time.sleep(poll_interval)
                        continue
                
                # Brief pause between tasks
                if poll_interval > 0:
                    time.sleep(min(poll_interval, 0.1))
                    
        except KeyboardInterrupt:
            self.logger.info(f"Worker {agent_id} stopped by user")
        except Exception as e:
            self.logger.error(f"Worker {agent_id} stopped due to error: {e}")
        
        self.logger.info(f"Worker {agent_id} processed {task_count} tasks")
        return processed_tasks
    
    # ============================================================================
    # TESTING AND SIMULATION
    # ============================================================================
    
    def simulate_customer_workflow(self, customer_name: str, items: List[str]) -> Dict:
        """Simulate a complete customer workflow."""
        workflow_steps = []
        
        try:
            # Create order
            order = self.create_order(customer_name, items, "Simulated customer order")
            order_id = order['order_id']
            workflow_steps.append(f"Created order {order_id}")
            
            # For simulation, we might cancel some orders
            if "cancel" in items[0].lower() if items else False:
                cancel_result = self.cancel_order(order_id, "Customer changed mind")
                workflow_steps.append(f"Cancelled order: {cancel_result.get('message', 'Success')}")
            
            final_order = self.get_order(order_id)
            
            return {
                "success": True,
                "order_id": order_id,
                "final_state": final_order['current_state'],
                "workflow_steps": workflow_steps,
                "final_order": final_order
            }
            
        except Exception as e:
            workflow_steps.append(f"Workflow failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workflow_steps": workflow_steps
            }
    
    def get_available_transitions(self, order_id: str) -> List[Dict]:
        """Get available transitions for an order based on current role."""
        order = self.get_order(order_id)
        return order.get('available_transitions', [])
    
    def can_perform_transition(self, order_id: str, transition: str) -> bool:
        """Check if current role can perform a specific transition on an order."""
        available = self.get_available_transitions(order_id)
        return any(t['transition'] == transition for t in available)


# ============================================================================
# CONVENIENCE FACTORY FUNCTIONS
# ============================================================================

def create_customer_client(base_url: str = "http://localhost:8000") -> WarehouseClient:
    """Create a client for customer agents."""
    return WarehouseClient(base_url=base_url, role="customer")

def create_fulfillment_client(base_url: str = "http://localhost:8000") -> WarehouseClient:
    """Create a client for fulfillment agents."""
    return WarehouseClient(base_url=base_url, role="fulfillment")


# ============================================================================
# TESTING FUNCTIONS
# ============================================================================

def test_complete_workflow(base_url: str = "http://localhost:8000"):
    """Test complete order workflow with both customer and fulfillment agents."""
    print("Testing Complete Workflow...")
    print("=" * 50)
    
    customer = create_customer_client(base_url)
    fulfillment = create_fulfillment_client(base_url)
    
    try:
        # 1. Customer creates order
        print("\n1. Customer creates order...")
        order = customer.create_order("Test Customer", ["Widget A", "Widget B"], "Test order")
        order_id = order['order_id']
        print(f"   Created order {order_id} in state: {order['current_state']}")
        
        # 2. Fulfillment agent processes the order through workflow
        print("\n2. Fulfillment agent processes order...")
        agent_id = "fulfillment-agent-001"
        
        # Process tasks until order is complete or no more tasks
        for step in range(10):  # Limit to prevent infinite loops
            result = fulfillment.process_next_task(agent_id)
            
            if result.get('action') == 'task_completed':
                task = result['task']
                if task['order_id'] == order_id:
                    new_state = result['result']['new_state']
                    print(f"   Step {step + 1}: {task['transition']} -> {new_state}")
                    
                    if new_state in ['delivered', 'cancelled']:
                        break
            else:
                print(f"   No more tasks available")
                break
        
        # 3. Check final state
        final_order = customer.get_order(order_id)
        print(f"\n3. Final order state: {final_order['current_state']}")
        
        # 4. If delivered, customer can return
        if final_order['current_state'] == 'delivered':
            print("\n4. Customer returns order...")
            return_result = customer.return_order(order_id, "Not satisfied with quality")
            print(f"   Return result: {return_result.get('message', 'Success')}")
        
        print("\n" + "=" * 50)
        print("Workflow test completed!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")


def test_role_permissions(base_url: str = "http://localhost:8000"):
    """Test role-based permission enforcement."""
    print("Testing Role Permissions...")
    print("=" * 50)
    
    customer = create_customer_client(base_url)
    fulfillment = create_fulfillment_client(base_url)
    
    try:
        # Create an order with customer
        order = customer.create_order("Permission Test", ["Test Item"], "Permission test order")
        order_id = order['order_id']
        print(f"\nCreated order {order_id}")
        
        # Test customer permissions
        print("\nTesting customer permissions:")
        
        # Customer should be able to cancel
        try:
            result = customer.request_transition(order_id, 'cancel_from_pending', notes="Customer cancellation")
            print("   ✓ Customer can cancel pending order")
        except Exception as e:
            print(f"   ✗ Customer cannot cancel: {e}")
        
        # Create another order for fulfillment tests
        order2 = customer.create_order("Permission Test 2", ["Test Item 2"], "For fulfillment test")
        order_id2 = order2['order_id']
        
        # Test fulfillment permissions
        print("\nTesting fulfillment permissions:")
        
        # Fulfillment should be able to confirm
        try:
            result = fulfillment.request_transition(order_id2, 'confirm', notes="Fulfillment confirmation")
            print("   ✓ Fulfillment can confirm order")
        except Exception as e:
            print(f"   ✗ Fulfillment cannot confirm: {e}")
        
        # Customer should NOT be able to confirm
        order3 = customer.create_order("Permission Test 3", ["Test Item 3"], "For negative test")
        order_id3 = order3['order_id']
        
        try:
            result = customer.request_transition(order_id3, 'confirm', notes="Customer trying to confirm")
            print("   ✗ ERROR: Customer was able to confirm order!")
        except PermissionError as e:
            print("   ✓ Customer correctly blocked from confirming")
        except Exception as e:
            print(f"   ? Unexpected error: {e}")
        
        print("\n" + "=" * 50)
        print("Permission test completed!")
        
    except Exception as e:
        print(f"Permission test failed: {e}")


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Warehouse Client Test")
    parser.add_argument("--test", choices=["workflow", "permissions", "all"], help="Run specific tests")
    parser.add_argument("--role", choices=["customer", "fulfillment"], default="customer", help="Agent role")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--worker", action="store_true", help="Run as worker agent")
    parser.add_argument("--agent-id", default="test-agent", help="Agent ID for worker mode")
    parser.add_argument("--max-tasks", type=int, help="Maximum tasks to process in worker mode")
    
    args = parser.parse_args()
    
    if args.test == "workflow":
        test_complete_workflow(args.url)
    elif args.test == "permissions":
        test_role_permissions(args.url)
    elif args.test == "all":
        test_complete_workflow(args.url)
        print("\n" + "=" * 70 + "\n")
        test_role_permissions(args.url)
    elif args.worker:
        # Run as worker
        client = WarehouseClient(base_url=args.url, role=args.role)
        client.run_worker(args.agent_id, args.max_tasks)
    else:
        # Interactive example
        client = WarehouseClient(base_url=args.url, role=args.role)
        
        print(f"Warehouse Client ({args.role} role)")
        print("=" * 40)
        
        try:
            # Check health
            health = client.health_check()
            print(f"API Status: {health['status']}")
            
            # Get state machine info
            info = client.get_state_machine_info()
            print(f"Available transitions for {args.role}: {info['role_permissions'][args.role]}")
            
            # Show queue status
            queue_status = client.get_queue_status()
            print(f"Queue status: {queue_status}")
            
            if args.role == "customer":
                # Create a sample order
                order = client.create_order("Sample Customer", ["Widget A", "Widget B"], "Sample order")
                print(f"Created sample order: {order['order_id']}")
                
                # Show available transitions
                transitions = client.get_available_transitions(order['order_id'])
                print(f"Available transitions: {[t['transition'] for t in transitions]}")
                
            else:  # fulfillment
                # Process one task if available
                result = client.process_next_task(args.agent_id)
                if result.get('action') == 'task_completed':
                    print(f"Processed task: {result['task']['transition']} for order {result['task']['order_id']}")
                else:
                    print("No tasks available to process")
            
        except Exception as e:
            print(f"Error: {e}")