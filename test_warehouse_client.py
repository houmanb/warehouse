import pytest
import time
from typing import Dict, List, Optional
from warehouse_client import create_customer_client, create_fulfillment_client, WarehouseClient

# Test Configuration
BASE_URL = "http://warehouse-api:8000"  # Docker container networking

@pytest.fixture(scope="session")
def customer_client():
    """Customer client fixture"""
    client = create_customer_client(BASE_URL)
    # Ensure API is healthy before running tests
    health = client.health_check()
    assert health["ok"] is True
    return client

@pytest.fixture(scope="session")
def fulfillment_client():
    """Fulfillment client fixture"""
    client = create_fulfillment_client(BASE_URL)
    # Ensure API is healthy before running tests
    health = client.health_check()
    assert health["ok"] is True
    return client

class TestClientBasicWorkflow:
    """Test the complete order workflow using the warehouse client"""
    
    def test_01_health_check(self, customer_client):
        """Test API health via client"""
        result = customer_client.health_check()
        assert result["ok"] is True
        assert "timestamp" in result
    
    def test_02_state_machine_info(self, fulfillment_client):
        """Test state machine configuration via client"""
        info = fulfillment_client.get_state_machine_info()
        
        assert "states" in info
        assert "transitions" in info
        assert "role_permissions" in info
        
        # Verify expected states
        expected_states = ["pending", "confirmed", "picking", "packed", "shipped", "delivered", "cancelled", "halted", "returned"]
        for state in expected_states:
            assert state in info["states"]
        
        # Verify role permissions exist
        assert "customer" in info["role_permissions"]
        assert "fulfillment" in info["role_permissions"]
        
        # Verify customer permissions
        customer_perms = info["role_permissions"]["customer"]
        assert "cancel_from_pending" in customer_perms
        assert "return_order" in customer_perms
        
        # Verify fulfillment permissions
        fulfillment_perms = info["role_permissions"]["fulfillment"]
        assert "confirm" in fulfillment_perms
        assert "start_picking" in fulfillment_perms
        assert "pack" in fulfillment_perms
        assert "ship" in fulfillment_perms
        assert "deliver" in fulfillment_perms
    
    def test_03_create_order_as_customer(self, customer_client):
        """Test order creation by customer using client"""
        order = customer_client.create_order(
            customer_name="Test Customer",
            items=["Widget A", "Widget B", "Gadget C"],
            notes="Test order for workflow validation"
        )
        
        assert order["customer_name"] == "Test Customer"
        assert order["items"] == ["Widget A", "Widget B", "Gadget C"]
        assert order["current_state"] == "pending"
        assert "order_id" in order
        assert "available_transitions" in order
        
        # Store order_id for subsequent tests
        TestClientBasicWorkflow.order_id = order["order_id"]
    
    def test_04_get_order_as_customer(self, customer_client):
        """Test getting order details as customer using client"""
        order = customer_client.get_order(TestClientBasicWorkflow.order_id)
        
        assert order["order_id"] == TestClientBasicWorkflow.order_id
        assert order["current_state"] == "pending"
        assert "available_transitions" in order
        
        # Customer should see cancel transitions from pending state
        transitions = [t["transition"] for t in order["available_transitions"]]
        assert "cancel_from_pending" in transitions
    
    def test_05_get_order_as_fulfillment(self, fulfillment_client):
        """Test getting order details as fulfillment agent using client"""
        order = fulfillment_client.get_order(TestClientBasicWorkflow.order_id)
        
        assert order["order_id"] == TestClientBasicWorkflow.order_id
        assert order["current_state"] == "pending"
        
        # Fulfillment should see different transitions
        transitions = [t["transition"] for t in order["available_transitions"]]
        assert "confirm" in transitions
        assert "halt_from_pending" in transitions
    
    def test_06_customer_cannot_confirm_order(self, customer_client):
        """Test that customers cannot perform fulfillment transitions using client"""
        with pytest.raises(PermissionError) as exc_info:
            customer_client.request_transition(
                TestClientBasicWorkflow.order_id,
                "confirm",
                notes="Customer attempting to confirm order"
            )
        assert "not allowed" in str(exc_info.value)
    
    def test_07_fulfillment_confirm_order(self, fulfillment_client):
        """Test order confirmation by fulfillment agent using client"""
        result = fulfillment_client.request_transition(
            TestClientBasicWorkflow.order_id,
            "confirm",
            agent_id="fulfillment-agent-001",
            notes="Order confirmed by fulfillment team"
        )
        
        assert "task_id" in result
        assert "queued" in result["message"]
        TestClientBasicWorkflow.confirm_task_id = result["task_id"]
    
    def test_08_claim_and_complete_confirm_task(self, fulfillment_client):
        """Test claiming and completing the confirm task using client"""
        # Claim the task
        claim_result = fulfillment_client.claim_next_task("fulfillment-agent-001")
        
        if "No fulfillment tasks available" in claim_result["message"]:
            # Wait a moment and try again
            time.sleep(1)
            claim_result = fulfillment_client.claim_next_task("fulfillment-agent-001")
        
        assert "task" in claim_result
        task = claim_result["task"]
        assert task["transition"] == "confirm"
        assert task["order_id"] == TestClientBasicWorkflow.order_id
        
        # Complete the task
        complete_result = fulfillment_client.complete_task(
            task["task_id"],
            "fulfillment-agent-001"
        )
        
        assert complete_result["new_state"] == "confirmed"
        assert "completed successfully" in complete_result["message"]
    
    def test_09_verify_order_confirmed(self, fulfillment_client):
        """Verify order is now in confirmed state using client"""
        order = fulfillment_client.get_order(TestClientBasicWorkflow.order_id)
        assert order["current_state"] == "confirmed"
        
        # Check history
        assert len(order["history"]) >= 2  # Created + Confirmed
        latest_history = order["history"][-1]
        assert latest_history["state"] == "confirmed"
    
    def test_10_complete_picking_workflow(self, fulfillment_client):
        """Test the complete picking workflow using client convenience methods"""
        # Use convenience method for starting picking
        result = fulfillment_client.start_picking(
            TestClientBasicWorkflow.order_id,
            notes="Starting picking process"
        )
        assert "task_id" in result
        
        # Process the task automatically
        task_result = fulfillment_client.process_next_task("fulfillment-agent-001")
        assert task_result["action"] == "task_completed"
        assert task_result["result"]["new_state"] == "picking"
    
    def test_11_complete_packing_workflow(self, fulfillment_client):
        """Test the complete packing workflow using client convenience methods"""
        # Use convenience method for packing
        result = fulfillment_client.pack_order(
            TestClientBasicWorkflow.order_id,
            notes="Packing completed"
        )
        assert "task_id" in result
        
        # Process the task automatically
        task_result = fulfillment_client.process_next_task("fulfillment-agent-001")
        assert task_result["action"] == "task_completed"
        assert task_result["result"]["new_state"] == "packed"
    
    def test_12_complete_shipping_workflow(self, fulfillment_client):
        """Test the complete shipping workflow using client convenience methods"""
        # Use convenience method for shipping
        result = fulfillment_client.ship_order(
            TestClientBasicWorkflow.order_id,
            notes="Order shipped via UPS"
        )
        assert "task_id" in result
        
        # Process the task automatically
        task_result = fulfillment_client.process_next_task("fulfillment-agent-001")
        assert task_result["action"] == "task_completed"
        assert task_result["result"]["new_state"] == "shipped"
    
    def test_13_complete_delivery_workflow(self, fulfillment_client):
        """Test the complete delivery workflow using client convenience methods"""
        # Use convenience method for delivery
        result = fulfillment_client.deliver_order(
            TestClientBasicWorkflow.order_id,
            notes="Order delivered successfully"
        )
        assert "task_id" in result
        
        # Process the task automatically
        task_result = fulfillment_client.process_next_task("fulfillment-agent-001")
        assert task_result["action"] == "task_completed"
        assert task_result["result"]["new_state"] == "delivered"
    
    def test_14_verify_final_state(self, customer_client):
        """Verify order reached final delivered state using client"""
        order = customer_client.get_order(TestClientBasicWorkflow.order_id)
        assert order["current_state"] == "delivered"
        
        # Verify complete history
        states_in_history = [h["state"] for h in order["history"]]
        expected_states = ["pending", "confirmed", "picking", "packed", "shipped", "delivered"]
        assert states_in_history == expected_states
        
        # Customer should now see return option
        transitions = [t["transition"] for t in order["available_transitions"]]
        assert "return_order" in transitions

class TestClientCancellationWorkflow:
    """Test order cancellation scenarios using client"""
    
    def test_01_create_order_for_cancellation(self, customer_client):
        """Create an order to test cancellation using client"""
        order = customer_client.create_order(
            customer_name="Cancel Test Customer",
            items=["Cancel Item"],
            notes="Order for cancellation testing"
        )
        
        TestClientCancellationWorkflow.cancel_order_id = order["order_id"]
    
    def test_02_customer_cancel_pending_order(self, customer_client):
        """Test customer cancelling a pending order using client convenience method"""
        # Use the convenience cancel_order method
        result = customer_client.cancel_order(
            TestClientCancellationWorkflow.cancel_order_id,
            reason="Customer requested cancellation"
        )
        assert "task_id" in result
        
        # Process the cancellation task
        task_result = customer_client.process_next_task("customer-001")
        assert task_result["action"] == "task_completed"
        assert task_result["result"]["new_state"] == "cancelled"

class TestClientErrorHandling:
    """Test error handling and edge cases using client"""
    
    def test_01_invalid_role_creation(self):
        """Test creating client with invalid role"""
        with pytest.raises(ValueError):
            # This should fail during role validation in the client
            client = WarehouseClient(BASE_URL, role="invalid_role")
            client.list_orders()  # Try to make a request
    
    def test_02_invalid_order_id(self, customer_client):
        """Test accessing non-existent order using client"""
        with pytest.raises(ValueError) as exc_info:
            customer_client.get_order("invalid-order-id")
        assert "not found" in str(exc_info.value)
    
    def test_03_invalid_transition(self, customer_client):
        """Test invalid transition request using client"""
        # Create a test order
        order = customer_client.create_order(
            customer_name="Error Test Customer",
            items=["Error Item"],
            notes="Order for error testing"
        )
        order_id = order["order_id"]
        
        # Try invalid transition
        with pytest.raises(PermissionError) as exc_info:
            customer_client.request_transition(
                order_id,
                "invalid_transition",
                notes="This should fail"
            )
        assert "not allowed" in str(exc_info.value)
    
    def test_04_customer_cannot_use_fulfillment_methods(self, customer_client):
        """Test that customer client cannot use fulfillment-specific methods"""
        # Create a test order
        order = customer_client.create_order(
            customer_name="Role Test Customer",
            items=["Role Item"],
            notes="Order for role testing"
        )
        order_id = order["order_id"]
        
        # Customer should not be able to confirm orders
        with pytest.raises(PermissionError):
            customer_client.confirm_order(order_id)

class TestClientQueueManagement:
    """Test queue management functionality using client"""
    
    def test_01_queue_status(self, fulfillment_client):
        """Test getting queue status using client"""
        status = fulfillment_client.get_queue_status()
        
        assert "customer_queued" in status
        assert "fulfillment_queued" in status
        assert "total_queued" in status
        assert "total_processing" in status
        assert "total_tasks" in status
    
    def test_02_claim_empty_queue(self, customer_client):
        """Test claiming from empty queue using client"""
        result = customer_client.claim_next_task("test-agent")
        assert "No customer tasks available" in result["message"]
    
    def test_03_release_non_existent_task(self, fulfillment_client):
        """Test releasing a task that doesn't exist using client"""
        with pytest.raises(ValueError) as exc_info:
            fulfillment_client.release_task("non-existent-agent", "test")
        assert "No task claimed" in str(exc_info.value)

class TestClientListOrders:
    """Test order listing functionality using client"""
    
    def test_01_list_orders_as_customer(self, customer_client):
        """Test listing orders as customer using client"""
        orders = customer_client.list_orders()
        assert isinstance(orders, list)
        
        # Each order should have available_transitions for customer role
        for order in orders:
            assert "available_transitions" in order
            assert isinstance(order["available_transitions"], list)
    
    def test_02_list_orders_as_fulfillment(self, fulfillment_client):
        """Test listing orders as fulfillment agent using client"""
        orders = fulfillment_client.list_orders()
        assert isinstance(orders, list)
        
        # Each order should have available_transitions for fulfillment role
        for order in orders:
            assert "available_transitions" in order
            assert isinstance(order["available_transitions"], list)
    
    def test_03_get_orders_by_state(self, fulfillment_client):
        """Test filtering orders by state using client convenience method"""
        delivered_orders = fulfillment_client.get_orders_by_state("delivered")
        for order in delivered_orders:
            assert order["current_state"] == "delivered"
        
        pending_orders = fulfillment_client.get_pending_orders()
        for order in pending_orders:
            assert order["current_state"] == "pending"

class TestClientConvenienceMethods:
    """Test client convenience methods and workflow helpers"""
    
    def test_01_customer_workflow_simulation(self, customer_client):
        """Test customer workflow simulation using client"""
        result = customer_client.simulate_customer_workflow(
            "Simulation Customer",
            ["Sim Widget A", "Sim Widget B"]
        )
        
        assert result["success"] is True
        assert "order_id" in result
        assert "final_state" in result
        assert "workflow_steps" in result
        assert result["final_state"] == "pending"  # Customer can only create orders
    
    def test_02_get_my_orders(self, customer_client):
        """Test getting orders for specific customer using client"""
        # Create an order first
        order = customer_client.create_order(
            "My Orders Test Customer",
            ["My Test Item"],
            "Test for my orders"
        )
        
        # Get orders for this customer
        my_orders = customer_client.get_my_orders("My Orders Test Customer")
        
        # Should find at least the order we just created
        order_ids = [o["order_id"] for o in my_orders]
        assert order["order_id"] in order_ids
    
    def test_03_check_available_transitions(self, customer_client, fulfillment_client):
        """Test checking available transitions using client"""
        # Create an order
        order = customer_client.create_order(
            "Transitions Test Customer",
            ["Transitions Item"],
            "Test for transitions"
        )
        order_id = order["order_id"]
        
        # Check customer transitions
        customer_transitions = customer_client.get_available_transitions(order_id)
        assert len(customer_transitions) > 0
        assert any(t["transition"] == "cancel_from_pending" for t in customer_transitions)
        
        # Check fulfillment transitions
        fulfillment_transitions = fulfillment_client.get_available_transitions(order_id)
        assert len(fulfillment_transitions) > 0
        assert any(t["transition"] == "confirm" for t in fulfillment_transitions)
        
        # Test can_perform_transition method
        assert customer_client.can_perform_transition(order_id, "cancel_from_pending") is True
        assert customer_client.can_perform_transition(order_id, "confirm") is False
        assert fulfillment_client.can_perform_transition(order_id, "confirm") is True
        assert fulfillment_client.can_perform_transition(order_id, "cancel_from_pending") is False

class TestClientWorkerMode:
    """Test client worker mode functionality"""
    
    def test_01_fulfillment_worker_processing(self, fulfillment_client, customer_client):
        """Test fulfillment worker processing multiple orders"""
        # Create several orders to process
        order_ids = []
        for i in range(3):
            order = customer_client.create_order(
                f"Worker Test Customer {i}",
                [f"Worker Item {i}"],
                f"Worker test order {i}"
            )
            order_ids.append(order["order_id"])
            
            # Queue up some transitions
            fulfillment_client.confirm_order(order["order_id"], f"Confirming order {i}")
        
        # Process tasks in worker mode (limit to prevent infinite loop)
        results = fulfillment_client.run_worker(
            agent_id="test-worker-001",
            max_tasks=3,
            poll_interval=0.1
        )
        
        # Should have processed 3 tasks
        assert len(results) == 3
        for result in results:
            assert result["action"] == "task_completed"
            assert result["task"]["transition"] == "confirm"
    
    def test_02_worker_with_no_tasks(self, fulfillment_client):
        """Test worker mode when no tasks are available"""
        # Run worker with max_tasks=1 on empty queue
        results = fulfillment_client.run_worker(
            agent_id="empty-queue-worker",
            max_tasks=1,
            poll_interval=0.1
        )
        
        # Should return empty list since no tasks were available
        assert len(results) == 0

class TestClientAdvancedWorkflows:
    """Test advanced workflow scenarios using client"""
    
    def test_01_halt_and_resume_workflow(self, fulfillment_client, customer_client):
        """Test halting and resuming an order using client"""
        # Create and confirm an order
        order = customer_client.create_order(
            "Halt Test Customer",
            ["Halt Item"],
            "Test for halt/resume"
        )
        order_id = order["order_id"]
        
        # Confirm the order
        fulfillment_client.confirm_order(order_id, "Confirming for halt test")
        task_result = fulfillment_client.process_next_task("halt-agent")
        assert task_result["result"]["new_state"] == "confirmed"
        
        # Halt the order
        halt_result = fulfillment_client.halt_order(order_id, "Emergency halt for testing")
        assert "task_id" in halt_result
        
        # Process halt task
        task_result = fulfillment_client.process_next_task("halt-agent")
        assert task_result["result"]["new_state"] == "halted"
        
        # Resume to confirmed state
        resume_result = fulfillment_client.resume_order(order_id, "confirmed", "Resuming after halt")
        assert "task_id" in resume_result
        
        # Process resume task
        task_result = fulfillment_client.process_next_task("halt-agent")
        assert task_result["result"]["new_state"] == "confirmed"
    
    def test_02_return_delivered_order(self, fulfillment_client, customer_client):
        """Test returning a delivered order using client"""
        # Create an order and process it to delivered state
        order = customer_client.create_order(
            "Return Test Customer",
            ["Return Item"],
            "Test for return"
        )
        order_id = order["order_id"]
        
        # Process through to delivered (simulate full workflow)
        transitions = ["confirm", "start_picking", "pack", "ship", "deliver"]
        agent_id = "return-test-agent"
        
        for transition in transitions:
            fulfillment_client.request_transition(order_id, transition, notes=f"Processing {transition}")
            task_result = fulfillment_client.process_next_task(agent_id)
            assert task_result["action"] == "task_completed"
        
        # Verify order is delivered
        final_order = customer_client.get_order(order_id)
        assert final_order["current_state"] == "delivered"
        
        # Customer returns the order
        return_result = customer_client.return_order(order_id, "Not satisfied with quality")
        assert "task_id" in return_result
        
        # Process return task
        task_result = customer_client.process_next_task("return-customer")
        assert task_result["result"]["new_state"] == "returned"

if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "--tb=short", "--color=yes"])