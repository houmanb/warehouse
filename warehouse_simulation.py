# warehouse_simulation.py
import os
# Make Solara's cache writable inside containers to avoid permission warnings
os.environ.setdefault("SOLARA_PROXY_CACHE_DIR", "/tmp/solara")
os.makedirs(os.environ["SOLARA_PROXY_CACHE_DIR"], exist_ok=True)

import random
import time
import logging
from dataclasses import dataclass

import mesa
from mesa.datacollection import DataCollector
from mesa.visualization import SolaraViz, make_plot_component
import solara

from warehouse_client import CustomerAgentClient, FulfillmentAgentClient, WarehouseConfig

# ------------------------- Logging -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ------------------------- Config --------------------------
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

    @classmethod
    def from_env(cls):
        """Create configuration from environment variables"""
        return cls(
            warehouse_url=os.getenv("WAREHOUSE_URL", "http://localhost:8000"),
            num_customers=int(os.getenv("NUM_CUSTOMERS", "5")),
            num_fulfillment_agents=int(os.getenv("NUM_FULFILLMENT_AGENTS", "2")),
            customer_order_interval_min=int(os.getenv("CUSTOMER_ORDER_INTERVAL_MIN", "30")),
            customer_order_interval_max=int(os.getenv("CUSTOMER_ORDER_INTERVAL_MAX", "60")),
            fulfillment_check_interval=int(os.getenv("FULFILLMENT_CHECK_INTERVAL", "10")),
            min_items_per_order=int(os.getenv("MIN_ITEMS_PER_ORDER", "1")),
            max_items_per_order=int(os.getenv("MAX_ITEMS_PER_ORDER", "5")),
            cancellation_rate_min=float(os.getenv("CANCELLATION_RATE_MIN", "0.01")),
            cancellation_rate_max=float(os.getenv("CANCELLATION_RATE_MAX", "0.05")),
            max_steps=int(os.getenv("MAX_STEPS", "1000")),
        )

    def wait_for_service(self, max_attempts: int = 30) -> bool:
        """Wait for warehouse service to be available before starting simulation"""
        logger.info(f"Waiting for warehouse service at {self.warehouse_url}...")
        for attempt in range(max_attempts):
            try:
                test_client = CustomerAgentClient(WarehouseConfig(base_url=self.warehouse_url))
                if test_client.health_check():
                    logger.info(f"Warehouse service is ready after {attempt + 1} attempts")
                    return True
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1}: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
        logger.error(f"Failed to connect to warehouse service after {max_attempts} attempts")
        return False


# ------------------------- Agents -------------------------
class CustomerAgent(mesa.Agent):
    """Agent representing a customer that places and cancels orders"""

    def __init__(self, model: "WarehouseModel"):
        super().__init__(model)  # Mesa 3.x: auto-assign unique_id and auto-add to model
        self.client = CustomerAgentClient(WarehouseConfig(base_url=model.config.warehouse_url))
        self.name = f"Customer_{self.unique_id}"

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

        logger.info(
            f"Created {self.name} with order_interval={self.order_interval}, "
            f"cancellation_rate={self.cancellation_rate:.1%}"
        )

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
            items = self.client.list_items()
            if not items:
                logger.warning(f"{self.name}: No items available for ordering")
                return

            num_items = random.randint(
                self.model.config.min_items_per_order,
                min(self.model.config.max_items_per_order, len(items))
            )
            selected_items = random.sample(items, num_items)
            item_names = [item["name"] for item in selected_items]

            order = self.client.create_order(self.name, item_names, f"Order from {self.name}")
            self.total_orders_placed += 1
            self.my_pending_orders.append(order["order_id"])

            self.model.total_orders_created += 1

            logger.info(
                f"{self.name}: Placed order #{order['order_id']} with "
                f"{len(item_names)} items: {item_names}"
            )

        except Exception as e:
            logger.error(f"{self.name}: Failed to place order: {e}")

    def _maybe_cancel_order(self):
        """Randomly cancel one of my pending orders"""
        if not self.my_pending_orders:
            return

        if random.random() < self.cancellation_rate:
            order_id = random.choice(self.my_pending_orders)
            try:
                order = self.client.get_order(order_id)
                if order["status"] == "pending":
                    self.client.cancel_order(order_id)
                    self.my_pending_orders.remove(order_id)
                    self.total_orders_cancelled += 1
                    self.model.total_orders_cancelled += 1
                    logger.info(f"{self.name}: Cancelled order #{order_id}")
                else:
                    if order_id in self.my_pending_orders:
                        self.my_pending_orders.remove(order_id)

            except Exception as e:
                logger.error(f"{self.name}: Failed to cancel order #{order_id}: {e}")
                if order_id in self.my_pending_orders:
                    self.my_pending_orders.remove(order_id)


class FulfillmentAgent(mesa.Agent):
    """Agent representing a fulfillment worker that processes orders"""

    def __init__(self, model: "WarehouseModel"):
        super().__init__(model)  # Mesa 3.x auto-assigns unique_id and adds agent to model
        self.client = FulfillmentAgentClient(WarehouseConfig(base_url=model.config.warehouse_url))
        self.name = f"Fulfillment_{self.unique_id}"

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
            statuses_to_process = ["pending", "confirmed", "picking", "packed", "shipped"]

            for status in statuses_to_process:
                orders = self.client.get_orders_by_status(status)
                if orders:
                    oldest_order = min(orders, key=lambda x: x["created_at"])
                    order_id = oldest_order["order_id"]

                    try:
                        result = self.client.advance_order(order_id, f"Processed by {self.name}")

                        if result and "order" in result:
                            new_status = result["order"]["status"]
                            self.total_orders_processed += 1

                            if new_status in self.orders_by_status:
                                self.orders_by_status[new_status] += 1

                            self.model.total_orders_processed += 1

                            logger.info(
                                f"{self.name}: Advanced order #{order_id} from {status} to {new_status}"
                            )

                            time.sleep(0.1)

                    except Exception as e:
                        logger.error(f"{self.name}: Failed to advance order #{order_id}: {e}")

        except Exception as e:
            logger.error(f"{self.name}: Error in processing orders: {e}")


# ------------------------- Model --------------------------
class WarehouseModel(mesa.Model):
    """Main model for the warehouse simulation using Mesa 3.x AgentSet activation"""

    def __init__(self, config: SimulationConfig | None = None, *, seed: int | None = None):
        super().__init__(seed=seed)  # REQUIRED in Mesa 3.x
        self.config = config or SimulationConfig()

        # Model statistics
        self.total_orders_created = 0
        self.total_orders_processed = 0
        self.total_orders_cancelled = 0

        # Create agents (Mesa 3.x auto-adds to self.agents)
        for _ in range(self.config.num_customers):
            CustomerAgent(self)
        for _ in range(self.config.num_fulfillment_agents):
            FulfillmentAgent(self)

        # Data collector for visualization
        self.datacollector = DataCollector(
            model_reporters={
                "Total Orders Created": "total_orders_created",
                "Total Orders Processed": "total_orders_processed",
                "Total Orders Cancelled": "total_orders_cancelled",
                # Use Mesa's auto-incremented steps counter
                "Orders Per Minute": lambda m: m.total_orders_created / max(1, m.steps / 60),
                "Active Customer Agents": lambda m: len(m.agents_by_type.get(CustomerAgent, [])),
                "Active Fulfillment Agents": lambda m: len(m.agents_by_type.get(FulfillmentAgent, [])),
            },
            agent_reporters={
                "Agent Type": lambda a: type(a).__name__,
                "Orders Placed": lambda a: getattr(a, "total_orders_placed", 0),
                "Orders Cancelled": lambda a: getattr(a, "total_orders_cancelled", 0),
                "Orders Processed": lambda a: getattr(a, "total_orders_processed", 0),
            },
        )

        # Test warehouse connection
        self._test_warehouse_connection()

        logger.info(
            f"Initialized WarehouseModel with "
            f"{len(self.agents_by_type.get(CustomerAgent, []))} customers and "
            f"{len(self.agents_by_type.get(FulfillmentAgent, []))} fulfillment agents"
        )

    def _test_warehouse_connection(self):
        """Test connection to warehouse service"""
        try:
            test_client = CustomerAgentClient(WarehouseConfig(base_url=self.config.warehouse_url))
            if test_client.health_check():
                logger.info("Successfully connected to warehouse service")
            else:
                logger.error("Warehouse service health check failed")
        except Exception as e:
            logger.error(f"Failed to connect to warehouse service: {e}")

    def step(self):
        """Execute one step of the simulation (Mesa 3.x AgentSet API)"""
        # Collect BEFORE stepping so the first tick includes initial state
        self.datacollector.collect(self)

        # Random activation across all agents (replacement for RandomActivation)
        self.agents.shuffle_do("step")  # <— migration: replaces schedule.step()

        # Optional: log progress every 100 steps
        if self.steps % 100 == 0:
            logger.info(
                f"Step {self.steps}: Created={self.total_orders_created}, "
                f"Processed={self.total_orders_processed}, "
                f"Cancelled={self.total_orders_cancelled}"
            )

    def run_model(self, *, steps: int | None = None):
        """Run the simulation for specified number of steps"""
        target = steps or self.config.max_steps
        logger.info(f"Starting simulation for {target} steps...")
        # In Mesa 3.x, Model.steps is auto-incremented; loop until we reach target
        while self.steps < target:
            self.step()
            time.sleep(0.05)
        logger.info(
            f"Simulation completed after {self.steps} steps | "
            f"Created: {self.total_orders_created}, "
            f"Processed: {self.total_orders_processed}, "
            f"Cancelled: {self.total_orders_cancelled}"
        )


# ------------------------- Visualization (Solara) ------------------
def _build_model_from_env() -> WarehouseModel:
    cfg = SimulationConfig.from_env()
    return WarehouseModel(cfg)


@solara.component
def Page():
    """Solara entrypoint: `solara run warehouse_simulation.py` will render this."""
    model = _build_model_from_env()
    # Charts-only UI (no space)
    components = [
        make_plot_component("Total Orders Created"),
        make_plot_component("Total Orders Processed"),
        make_plot_component("Total Orders Cancelled"),
        make_plot_component("Orders Per Minute"),
    ]
    return SolaraViz(model, components=components, name="Warehouse Agent Simulation")


# ------------------------- Main ---------------------------
if __name__ == "__main__":
    import sys

    config = SimulationConfig.from_env()

    # Wait for FastAPI backend before starting Solara in Docker
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        if not config.wait_for_service():
            sys.exit(1)
        # Your image likely lacks `solara.run` in the Python API; use the CLI instead
        logger.info("Starting Mesa SolaraViz server via `solara run` ...")
        logger.info("Open http://localhost:8521 in your browser to view the simulation")
        logger.info(f"Connected to warehouse at: {config.warehouse_url}")
        logger.info(
            f"Agents (configured): {config.num_customers} customers, "
            f"{config.num_fulfillment_agents} fulfillment"
        )
        host = "0.0.0.0" if os.getenv("IN_DOCKER", "0") == "1" else "127.0.0.1"
        this_file = os.path.abspath(__file__)
        os.execvp("solara", ["solara", "run", this_file, "--host", host, "--port", "8521"])

    # Headless mode
    print("Running headless warehouse simulation...")
    print(f"Connected to warehouse at: {config.warehouse_url}")
    print(
        f"Agents (configured): {config.num_customers} customers, "
        f"{config.num_fulfillment_agents} fulfillment"
    )
    print(f"Running for {config.max_steps} steps")

    m = WarehouseModel(config)
    m.run_model(steps=config.max_steps)

    print("\nFinal Statistics:")
    print(f"Total Orders Created: {m.total_orders_created}")
    print(f"Total Orders Processed: {m.total_orders_processed}")
    print(f"Total Orders Cancelled: {m.total_orders_cancelled}")

    print("\nAgent Statistics:")
    # Iterate over agents using Mesa 3.x API
    for a in m.agents:
        if isinstance(a, CustomerAgent):
            print(f"{a.name}: Placed={a.total_orders_placed}, Cancelled={a.total_orders_cancelled}")
        elif isinstance(a, FulfillmentAgent):
            print(f"{a.name}: Processed={a.total_orders_processed}")
