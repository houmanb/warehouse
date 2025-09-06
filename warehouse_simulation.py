import mesa
import random
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import threading
from warehouse_client import CustomerAgentClient, FulfillmentAgentClient, WarehouseConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SimulationConfig:
    """Configuration for the warehouse simulation"""
    warehouse_url: str = "http://localhost:8000"
    num_customers: int = 5
    num_fulfillment_agents: int = 2
    
    # Timing (in simulation steps)
    customer_order_interval_min: int = 30  # 30 steps
    customer_order_interval_max: int = 60  # 60 steps
    fulfillment_check_interval: int = 10   # 10 steps
    
    # Order behavior
    min_items_per_order: int = 1
    max_items_per_order: int = 5
    cancellation_rate_min: float = 0.01   # 1%
    cancellation_rate_max: float = 0.05   # 5%
    
    # Simulation
    max_steps: int = 1000

class CustomerAgent(mesa.Agent):
    """Agent representing a customer that places and cancels orders"""
    
    def __init__(self, unique_id: int, model: 'WarehouseModel'):
        super().__init__(unique_id, model)
        self.client = CustomerAgentClient(WarehouseConfig(base_url=model.config.warehouse_url))
        self.name = f"Customer_{unique_id}"
        
        # Agent behavior parameters
        self.order_interval = random.randint(
            model.config.customer_order_interval_min,
            model.config.customer_order_interval_max
        )
        self.cancellation_rate = random.uniform(
            model.config.cancellation_rate_min,
            model.config.cancellation_rate_max
        )
        
        # State tracking
        self.steps_since_last_order = 0
        self.total_orders_placed = 0
        self.total_orders_cancelled = 0
        self.my_pending_orders = []  # Track my own orders for potential cancellation
        
        logger.info(f"Created {self.name} with order_interval={self.order_interval}, cancellation_rate={self.cancellation_rate:.1%}")
    
    def step(self):
        """Execute one step of customer behavior"""
        self.steps_since_last_order += 1
        
        # Check if it's time to place a new order
        if self.steps_since_last_order >= self.order_interval:
            self._try_place_order()
            self.steps_since_last_order = 0
            # Set new random interval for next order
            self.order_interval = random.randint(
                self.model.config.customer_order_interval_min,
                self.model.config.customer_order_interval_max
            )
        
        # Randomly cancel one of my pending orders
        self._maybe_cancel_order()
    
    def _try_place_order(self):
        """Attempt to place a new order"""
        try:
            # Get available items
            items = self.client.list_items()
            if not items:
                logger.warning(f"{self.name}: No items available for ordering")
                return
            
            # Select random number of items
            num_items = random.randint(
                self.model.config.min_items_per_order,
                min(self.model.config.max_items_per_order, len(items))
            )
            selected_items = random.sample(items, num_items)
            item_names = [item["name"] for item in selected_items]
            
            # Place order
            order = self.client.create_order(self.name, item_names, f"Order from {self.name}")
            self.total_orders_placed += 1
            self.my_pending_orders.append(order["order_id"])
            
            # Update model statistics
            self.model.total_orders_created += 1
            
            logger.info(f"{self.name}: Placed order #{order['order_id']} with {len(item_names)} items: {item_names}")
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to place order: {e}")
    
    def _maybe_cancel_order(self):
        """Randomly cancel one of my pending orders"""
        if not self.my_pending_orders:
            return
        
        # Check if we should cancel (based on cancellation rate)
        if random.random() < self.cancellation_rate:
            # Pick a random pending order to cancel
            order_id = random.choice(self.my_pending_orders)
            
            try:
                # Check if order is still pending (might have been processed)
                order = self.client.get_order(order_id)
                if order["status"] == "pending":
                    self.client.cancel_order(order_id)
                    self.my_pending_orders.remove(order_id)
                    self.total_orders_cancelled += 1
                    self.model.total_orders_cancelled += 1
                    
                    logger.info(f"{self.name}: Cancelled order #{order_id}")
                else:
                    # Remove from pending list since it's no longer pending
                    self.my_pending_orders.remove(order_id)
                    
            except Exception as e:
                logger.error(f"{self.name}: Failed to cancel order #{order_id}: {e}")
                # Remove from list anyway to avoid repeated errors
                if order_id in self.my_pending_orders:
                    self.my_pending_orders.remove(order_id)

class FulfillmentAgent(mesa.Agent):
    """Agent representing a fulfillment worker that processes orders"""
    
    def __init__(self, unique_id: int, model: 'WarehouseModel'):
        super().__init__(unique_id, model)
        self.client = FulfillmentAgentClient(WarehouseConfig(base_url=model.config.warehouse_url))
        self.name = f"Fulfillment_{unique_id}"
        
        # Agent behavior parameters
        self.check_interval = model.config.fulfillment_check_interval
        self.steps_since_last_check = 0
        
        # State tracking
        self.total_orders_processed = 0
        self.orders_by_status = {
            "confirmed": 0,
            "picking": 0,
            "packed": 0,
            "shipped": 0,
            "delivered": 0
        }
        
        logger.info(f"Created {self.name} with check_interval={self.check_interval}")
    
    def step(self):
        """Execute one step of fulfillment behavior"""
        self.steps_since_last_check += 1
        
        if self.steps_since_last_check >= self.check_interval:
            self._process_orders()
            self.steps_since_last_check = 0
    
    def _process_orders(self):
        """Process orders in the fulfillment pipeline"""
        try:
            # Process one order from each status in the pipeline
            statuses_to_process = ["pending", "confirmed", "picking", "packed", "shipped"]
            
            for status in statuses_to_process:
                orders = self.client.get_orders_by_status(status)
                
                if orders:
                    # Process the oldest order
                    oldest_order = min(orders, key=lambda x: x["created_at"])
                    order_id = oldest_order["order_id"]
                    
                    try:
                        result = self.client.advance_order(order_id, f"Processed by {self.name}")
                        
                        if result and "order" in result:
                            new_status = result["order"]["status"]
                            self.total_orders_processed += 1
                            
                            if new_status in self.orders_by_status:
                                self.orders_by_status[new_status] += 1
                            
                            # Update model statistics
                            self.model.total_orders_processed += 1
                            
                            logger.info(f"{self.name}: Advanced order #{order_id} from {status} to {new_status}")
                            
                            # Small delay to simulate processing time
                            time.sleep(0.1)
                            
                    except Exception as e:
                        logger.error(f"{self.name}: Failed to advance order #{order_id}: {e}")
                        
        except Exception as e:
            logger.error(f"{self.name}: Error in processing orders: {e}")

class WarehouseModel(mesa.Model):
    """Main model for the warehouse simulation"""
    
    def __init__(self, config: SimulationConfig = None):
        super().__init__()
        self.config = config or SimulationConfig()
        
        # Model statistics
        self.total_orders_created = 0
        self.total_orders_processed = 0
        self.total_orders_cancelled = 0
        self.step_count = 0
        
        # Create scheduler
        self.schedule = mesa.time.RandomActivation(self)
        
        # Create agents
        self._create_agents()
        
        # Data collector for visualization
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Total Orders Created": "total_orders_created",
                "Total Orders Processed": "total_orders_processed", 
                "Total Orders Cancelled": "total_orders_cancelled",
                "Active Customer Agents": lambda m: len([a for a in m.schedule.agents if isinstance(a, CustomerAgent)]),
                "Active Fulfillment Agents": lambda m: len([a for a in m.schedule.agents if isinstance(a, FulfillmentAgent)]),
                "Orders Per Minute": lambda m: m.total_orders_created / max(1, m.step_count / 60),
            },
            agent_reporters={
                "Agent Type": lambda a: type(a).__name__,
                "Orders Placed": lambda a: getattr(a, 'total_orders_placed', 0),
                "Orders Cancelled": lambda a: getattr(a, 'total_orders_cancelled', 0),
                "Orders Processed": lambda a: getattr(a, 'total_orders_processed', 0),
            }
        )
        
        # Test warehouse connection
        self._test_warehouse_connection()
        
        logger.info(f"Initialized WarehouseModel with {self.config.num_customers} customers and {self.config.num_fulfillment_agents} fulfillment agents")
    
    def _create_agents(self):
        """Create customer and fulfillment agents"""
        agent_id = 0
        
        # Create customer agents
        for i in range(self.config.num_customers):
            agent = CustomerAgent(agent_id, self)
            self.schedule.add(agent)
            agent_id += 1
        
        # Create fulfillment agents
        for i in range(self.config.num_fulfillment_agents):
            agent = FulfillmentAgent(agent_id, self)
            self.schedule.add(agent)
            agent_id += 1
    
    def _test_warehouse_connection(self):
        """Test connection to warehouse service"""
        try:
            from warehouse_client import WarehouseConfig, CustomerAgentClient
            test_client = CustomerAgentClient(WarehouseConfig(base_url=self.config.warehouse_url))
            
            if test_client.health_check():
                logger.info("✅ Successfully connected to warehouse service")
            else:
                logger.error("❌ Warehouse service health check failed")
        except Exception as e:
            logger.error(f"❌ Failed to connect to warehouse service: {e}")
    
    def step(self):
        """Execute one step of the simulation"""
        self.step_count += 1
        
        # Collect data before step
        self.datacollector.collect(self)
        
        # Step all agents
        self.schedule.step()
        
        # Log progress every 100 steps
        if self.step_count % 100 == 0:
            logger.info(f"Step {self.step_count}: Created={self.total_orders_created}, "
                       f"Processed={self.total_orders_processed}, Cancelled={self.total_orders_cancelled}")
    
    def run_model(self, step_count: int = None):
        """Run the simulation for specified number of steps"""
        steps = step_count or self.config.max_steps
        
        logger.info(f"Starting simulation for {steps} steps...")
        
        for i in range(steps):
            self.step()
            
            # Optional: Add small delay to make visualization more readable
            time.sleep(0.05)
        
        logger.info(f"Simulation completed after {steps} steps")
        logger.info(f"Final stats - Created: {self.total_orders_created}, "
                   f"Processed: {self.total_orders_processed}, Cancelled: {self.total_orders_cancelled}")

# ==================== MESA VISUALIZATION ====================

def agent_portrayal(agent):
    """Define how agents appear in the visualization"""
    if isinstance(agent, CustomerAgent):
        portrayal = {
            "Shape": "circle",
            "Color": "blue",
            "Filled": "true",
            "Layer": 0,
            "r": 0.8,
            "text": f"C{agent.unique_id}",
            "text_color": "white"
        }
    elif isinstance(agent, FulfillmentAgent):
        portrayal = {
            "Shape": "rect",
            "Color": "green", 
            "Filled": "true",
            "Layer": 0,
            "w": 0.8,
            "h": 0.8,
            "text": f"F{agent.unique_id}",
            "text_color": "white"
        }
    else:
        portrayal = {"Shape": "circle", "Color": "grey", "Filled": "true", "Layer": 0, "r": 0.5}
    
    return portrayal

def create_visualization_server():
    """Create Mesa visualization server"""
    
    # Simple grid for agent placement (not used for spatial relationships)
    grid = mesa.visualization.CanvasGrid(agent_portrayal, 10, 10, 500, 500)
    
    # Charts for tracking metrics
    charts = [
        mesa.visualization.ChartModule([
            {"Label": "Total Orders Created", "Color": "Blue"},
            {"Label": "Total Orders Processed", "Color": "Green"},
            {"Label": "Total Orders Cancelled", "Color": "Red"}
        ], data_collector_name='datacollector'),
        
        mesa.visualization.ChartModule([
            {"Label": "Orders Per Minute", "Color": "Purple"}
        ], data_collector_name='datacollector')
    ]
    
    # Model parameters that can be adjusted in the browser
    model_params = {
        "config": mesa.visualization.UserSettableParameter(
            "static_text",
            value="Warehouse Agent Simulation"
        )
    }
    
    # Create and return server
    server = mesa.visualization.ModularServer(
        WarehouseModel,
        [grid] + charts,
        "Warehouse Agent Simulation",
        model_params
    )
    
    return server

# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    import sys
    import os
    
    # Get configuration from environment variables
    config = SimulationConfig.from_env()
    
    # Wait for warehouse service to be available
    if not wait_for_warehouse_service(config):
        sys.exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Run visualization server
        print("🚀 Starting Mesa visualization server...")
        print(f"📊 Open http://localhost:8521 in your browser to view the simulation")
        print(f"🏪 Connected to warehouse at: {config.warehouse_url}")
        print(f"👥 Agents: {config.num_customers} customers, {config.num_fulfillment_agents} fulfillment")
        
        # For Docker, we need to bind to all interfaces, not just localhost
        server = create_visualization_server()
        server.port = 8521
        
        # In Docker, bind to all interfaces
        if os.getenv("WAREHOUSE_URL", "").startswith("http://fastapi-app"):
            server.launch(open_browser=False)  # Don't try to open browser in Docker
        else:
            server.launch()
        
    else:
        # Run headless simulation
        print("🤖 Running headless warehouse simulation...")
        print(f"🏪 Connected to warehouse at: {config.warehouse_url}")
        print(f"👥 Agents: {config.num_customers} customers, {config.num_fulfillment_agents} fulfillment")
        print(f"⏱️  Running for {config.max_steps} steps")
        
        model = WarehouseModel(config)
        model.run_model(config.max_steps)
        
        # Print final statistics
        print("\n📈 Final Statistics:")
        print(f"Total Orders Created: {model.total_orders_created}")
        print(f"Total Orders Processed: {model.total_orders_processed}")
        print(f"Total Orders Cancelled: {model.total_orders_cancelled}")
        
        # Print agent statistics
        print("\n👥 Agent Statistics:")
        for agent in model.schedule.agents:
            if isinstance(agent, CustomerAgent):
                print(f"{agent.name}: Placed={agent.total_orders_placed}, Cancelled={agent.total_orders_cancelled}")
            elif isinstance(agent, FulfillmentAgent):
                print(f"{agent.name}: Processed={agent.total_orders_processed}")