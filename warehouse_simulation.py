import os
import random
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
from datetime import datetime, timedelta

import mesa
from mesa.datacollection import DataCollector
from mesa.visualization import SolaraViz, make_plot_component
import solara

# Import the dedicated warehouse client
try:
    from warehouse_client import WarehouseClient
except ImportError:
    # Fallback if warehouse_client.py is not available
    print("Warning: warehouse_client.py not found. Please ensure it's in the same directory.")
    print("You can copy the WarehouseClient class from the warehouse_client.py file.")
    raise ImportError("warehouse_client module is required for this simulation")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WarehouseZone(Enum):
    """Different warehouse zones with different characteristics"""
    ELECTRONICS = "electronics"
    APPAREL = "apparel"
    BOOKS = "books"
    HOUSEHOLD = "household"
    FRAGILE = "fragile"


class OrderPriority(Enum):
    """Order priority levels"""
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"


class ShiftType(Enum):
    """Different work shifts"""
    MORNING = "morning"    # 6am-2pm
    AFTERNOON = "afternoon"  # 2pm-10pm
    NIGHT = "night"        # 10pm-6am


@dataclass
class InventoryItem:
    """Represents an item in warehouse inventory"""
    name: str
    zone: WarehouseZone
    stock_level: int
    reorder_point: int
    pick_time_multiplier: float = 1.0  # Difficulty factor
    fragile: bool = False
    weight: float = 1.0  # Affects packing time


@dataclass
class SimulationConfig:
    """Enhanced configuration for realistic warehouse simulation"""
    warehouse_url: str = "http://warehouse-api:8000"
    
    # Agent configuration
    num_customers: int = 20
    num_fulfillment_agents: int = 6
    max_concurrent_orders_per_agent: int = 2
    
    # Timing configuration
    customer_order_interval_min: int = 20
    customer_order_interval_max: int = 90
    fulfillment_check_interval: int = 5
    
    # Order characteristics
    min_items_per_order: int = 1
    max_items_per_order: int = 5
    express_order_probability: float = 0.15
    overnight_order_probability: float = 0.05
    
    # Operational realism
    cancellation_rate_min: float = 0.02
    cancellation_rate_max: float = 0.08
    equipment_failure_probability: float = 0.001
    quality_check_failure_rate: float = 0.03
    weather_delay_probability: float = 0.02
    peak_hour_slowdown_factor: float = 1.5
    
    # Business patterns
    seasonal_demand_multiplier: float = 1.0
    enable_shift_patterns: bool = False
    enable_inventory_constraints: bool = False
    enable_operational_disruptions: bool = False
    
    # Simulation control
    max_steps: int = 1000
    simulation_speed_factor: float = 0.1  # Speed up time
    
    # Inventory items with realistic characteristics
    inventory_items: List[InventoryItem] = field(default_factory=lambda: [
        InventoryItem("Laptop", WarehouseZone.ELECTRONICS, 50, 10, 1.2, False, 3.0),
        InventoryItem("Smartphone", WarehouseZone.ELECTRONICS, 100, 20, 1.0, True, 0.5),
        InventoryItem("Tablet", WarehouseZone.ELECTRONICS, 75, 15, 1.1, True, 1.0),
        InventoryItem("T-Shirt", WarehouseZone.APPAREL, 200, 50, 0.8, False, 0.3),
        InventoryItem("Jeans", WarehouseZone.APPAREL, 150, 30, 0.9, False, 0.8),
        InventoryItem("Novel", WarehouseZone.BOOKS, 300, 50, 0.7, False, 0.4),
        InventoryItem("Textbook", WarehouseZone.BOOKS, 80, 20, 0.8, False, 1.5),
        InventoryItem("Coffee Mug", WarehouseZone.HOUSEHOLD, 120, 25, 0.9, True, 0.6),
        InventoryItem("Kitchen Knife", WarehouseZone.HOUSEHOLD, 60, 15, 1.1, False, 0.4),
        InventoryItem("Wine Glass", WarehouseZone.FRAGILE, 80, 20, 1.3, True, 0.3),
        InventoryItem("Mirror", WarehouseZone.FRAGILE, 40, 10, 1.5, True, 2.0),
    ])


    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Agent configuration validation
        if self.num_customers <= 0:
            issues.append("num_customers must be positive")
        if self.num_fulfillment_agents <= 0:
            issues.append("num_fulfillment_agents must be positive")
        if self.max_concurrent_orders_per_agent <= 0:
            issues.append("max_concurrent_orders_per_agent must be positive")
        
        # Timing configuration validation
        if self.customer_order_interval_min <= 0:
            issues.append("customer_order_interval_min must be positive")
        if self.customer_order_interval_max <= 0:
            issues.append("customer_order_interval_max must be positive")
        if self.customer_order_interval_min >= self.customer_order_interval_max:
            issues.append("order interval min must be less than max")
        if self.fulfillment_check_interval <= 0:
            issues.append("fulfillment_check_interval must be positive")
        
        # Order characteristics validation
        if self.min_items_per_order <= 0:
            issues.append("min_items_per_order must be positive")
        if self.max_items_per_order <= 0:
            issues.append("max_items_per_order must be positive")
        if self.min_items_per_order > self.max_items_per_order:
            issues.append("min_items_per_order must be <= max_items_per_order")
        
        # Probability validation (should be between 0 and 1)
        probabilities = [
            ("express_order_probability", self.express_order_probability),
            ("overnight_order_probability", self.overnight_order_probability),
            ("equipment_failure_probability", self.equipment_failure_probability),
            ("quality_check_failure_rate", self.quality_check_failure_rate),
            ("weather_delay_probability", self.weather_delay_probability),
        ]
        
        for name, value in probabilities:
            if not (0 <= value <= 1):
                issues.append(f"{name} must be between 0 and 1")
        
        # Rate validation
        if self.cancellation_rate_min < 0 or self.cancellation_rate_max < 0:
            issues.append("cancellation rates must be non-negative")
        if self.cancellation_rate_min > self.cancellation_rate_max:
            issues.append("cancellation_rate_min must be <= cancellation_rate_max")
        
        # Simulation control validation
        if self.max_steps <= 0:
            issues.append("max_steps must be positive")
        if self.simulation_speed_factor <= 0:
            issues.append("simulation_speed_factor must be positive")
        if self.seasonal_demand_multiplier <= 0:
            issues.append("seasonal_demand_multiplier must be positive")
        if self.peak_hour_slowdown_factor <= 0:
            issues.append("peak_hour_slowdown_factor must be positive")
        
        # Inventory validation
        if not self.inventory_items:
            issues.append("inventory_items cannot be empty")
        else:
            for i, item in enumerate(self.inventory_items):
                if item.stock_level < 0:
                    issues.append(f"inventory_items[{i}].stock_level must be non-negative")
                if item.reorder_point < 0:
                    issues.append(f"inventory_items[{i}].reorder_point must be non-negative")
                if item.pick_time_multiplier <= 0:
                    issues.append(f"inventory_items[{i}].pick_time_multiplier must be positive")
                if item.weight <= 0:
                    issues.append(f"inventory_items[{i}].weight must be positive")
        
        return issues


    @classmethod
    def from_env(cls):
        """Create configuration from environment variables with enhanced options"""
        return cls(
            warehouse_url=os.getenv("WAREHOUSE_URL", "http://warehouse-api:8000"),
            num_customers=int(os.getenv("NUM_CUSTOMERS", "8")),
            num_fulfillment_agents=int(os.getenv("NUM_FULFILLMENT_AGENTS", "3")),
            max_concurrent_orders_per_agent=int(os.getenv("MAX_CONCURRENT_ORDERS_PER_AGENT", "2")),
            customer_order_interval_min=int(os.getenv("CUSTOMER_ORDER_INTERVAL_MIN", "20")),
            customer_order_interval_max=int(os.getenv("CUSTOMER_ORDER_INTERVAL_MAX", "90")),
            fulfillment_check_interval=int(os.getenv("FULFILLMENT_CHECK_INTERVAL", "5")),
            express_order_probability=float(os.getenv("EXPRESS_ORDER_PROBABILITY", "0.15")),
            equipment_failure_probability=float(os.getenv("EQUIPMENT_FAILURE_PROBABILITY", "0.001")),
            enable_shift_patterns=os.getenv("ENABLE_SHIFT_PATTERNS", "true").lower() == "true",
            enable_inventory_constraints=os.getenv("ENABLE_INVENTORY_CONSTRAINTS", "true").lower() == "true",
            enable_operational_disruptions=os.getenv("ENABLE_OPERATIONAL_DISRUPTIONS", "true").lower() == "true",
            simulation_speed_factor=float(os.getenv("SIMULATION_SPEED_FACTOR", "0.1")),
        )

    def wait_for_service(self, max_attempts: int = 30) -> bool:
        """Wait for warehouse service to be available"""
        logger.info(f"Waiting for warehouse service at {self.warehouse_url}...")
        for attempt in range(max_attempts):
            try:
                # Use the dedicated client for health checks
                test_client = WarehouseClient(base_url=self.warehouse_url, role="customer")
                health_result = test_client.health_check()
                if health_result and health_result.get('status') == 'healthy':
                    logger.info(f"Warehouse service is ready after {attempt + 1} attempts")
                    return True
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1}: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
        logger.error(f"Failed to connect to warehouse service after {max_attempts} attempts")
        return False


class EnhancedCustomerAgent(mesa.Agent):
    """Enhanced customer agent with realistic behavior patterns using dedicated warehouse client"""

    def __init__(self, model):
        super().__init__(model)
        # Use the dedicated warehouse client
        self.client = WarehouseClient(base_url=model.config.warehouse_url, role="customer")
        self.name = f"Customer_{self.unique_id}"
        
        # Customer characteristics
        self.customer_type = random.choice(["regular", "premium", "business"])
        self.order_frequency_modifier = {
            "regular": 1.0,
            "premium": 0.7,  # Orders more frequently
            "business": 0.5   # Orders very frequently
        }[self.customer_type]
        
        # Behavioral parameters
        base_interval_min = model.config.customer_order_interval_min
        base_interval_max = model.config.customer_order_interval_max
        
        self.order_interval_min = int(base_interval_min * self.order_frequency_modifier)
        self.order_interval_max = int(base_interval_max * self.order_frequency_modifier)
        
        self.cancellation_rate = random.uniform(
            model.config.cancellation_rate_min,
            model.config.cancellation_rate_max
        )
        
        # Preferences
        self.preferred_zones = random.sample(list(WarehouseZone), k=random.randint(2, 4))
        self.express_probability = model.config.express_order_probability * (
            2.0 if self.customer_type == "business" else 
            1.5 if self.customer_type == "premium" else 1.0
        )
        
        # State tracking
        self.steps_since_last_order = random.randint(0, self.order_interval_max)
        self.total_orders_placed = 0
        self.total_orders_cancelled = 0
        self.total_express_orders = 0
        self.satisfaction_score = 1.0  # Affected by delivery performance

        logger.info(f"Customer {self.name} ({self.customer_type}) created")

    def step(self):
        """Enhanced customer behavior with business patterns"""
        self.steps_since_last_order += 1
        
        # Apply peak hour effects (slower ordering during busy times)
        current_hour = (self.model.steps // 60) % 24
        is_peak_hour = current_hour in [11, 12, 13, 17, 18, 19]  # Lunch and evening
        
        order_threshold = self.order_interval_min
        if is_peak_hour and self.customer_type == "regular":
            order_threshold = int(order_threshold * 1.2)  # Regular customers avoid peak hours
        
        if self.steps_since_last_order >= order_threshold:
            if self._should_place_order():
                self._try_place_order()
                self._reset_order_interval()

        self._maybe_cancel_order()

    def _should_place_order(self) -> bool:
        """Determine if customer should place order based on various factors"""
        # Seasonal demand (could be time-based in real implementation)
        seasonal_factor = self.model.config.seasonal_demand_multiplier
        
        # Satisfaction affects ordering frequency
        satisfaction_factor = self.satisfaction_score
        
        # Business customers are less affected by satisfaction
        if self.customer_type == "business":
            satisfaction_factor = max(0.8, satisfaction_factor)
        
        probability = seasonal_factor * satisfaction_factor
        return random.random() < probability

    def _try_place_order(self):
        """Enhanced order placement with realistic item selection"""
        try:
            # Select items based on preferences and availability
            available_items = [
                item for item in self.model.config.inventory_items
                if item.zone in self.preferred_zones and 
                   self.model.inventory_manager.is_available(item.name)
            ]
            
            if not available_items:
                # Fall back to any available items
                available_items = [
                    item for item in self.model.config.inventory_items
                    if self.model.inventory_manager.is_available(item.name)
                ]
            
            if not available_items:
                logger.debug(f"{self.name}: No items available for order")
                return

            # Select items with weighted preference for customer type
            num_items = self._get_order_size()
            selected_items = self._select_items(available_items, num_items)
            
            # Determine priority
            priority = self._determine_order_priority()
            
            # Create order with enhanced notes
            notes = f"{self.customer_type} customer order (Priority: {priority.value})"
            if priority != OrderPriority.STANDARD:
                notes += f" - {priority.value.upper()} PROCESSING REQUIRED"
            
            order = self.client.create_order(self.name, [item.name for item in selected_items], notes)
            
            if order:
                order_id = order["order_id"]
                self.total_orders_placed += 1
                self.model.total_orders_created += 1
                
                if priority != OrderPriority.STANDARD:
                    self.total_express_orders += 1
                    self.model.total_express_orders += 1
                
                # Update inventory
                for item in selected_items:
                    self.model.inventory_manager.reserve_item(item.name, 1)
                
                logger.info(f"{self.name}: Created {priority.value} order {order_id} with {len(selected_items)} items")
            else:
                logger.warning(f"{self.name}: Failed to place order")

        except Exception as e:
            logger.error(f"{self.name}: Exception placing order: {e}")

    def _get_order_size(self) -> int:
        """Determine order size based on customer type"""
        base_min = self.model.config.min_items_per_order
        base_max = self.model.config.max_items_per_order
        
        if self.customer_type == "business":
            return random.randint(max(base_min, 2), min(base_max + 2, 7))
        elif self.customer_type == "premium":
            return random.randint(base_min, base_max + 1)
        else:
            return random.randint(base_min, base_max)

    def _select_items(self, available_items: List[InventoryItem], num_items: int) -> List[InventoryItem]:
        """Select items with realistic preferences"""
        # Weight items by customer type preferences
        weights = []
        for item in available_items:
            weight = 1.0
            
            # Business customers prefer electronics and books
            if self.customer_type == "business" and item.zone in [WarehouseZone.ELECTRONICS, WarehouseZone.BOOKS]:
                weight *= 1.5
            
            # Premium customers prefer higher-value items
            if self.customer_type == "premium" and item.zone in [WarehouseZone.ELECTRONICS, WarehouseZone.FRAGILE]:
                weight *= 1.3
            
            weights.append(weight)
        
        # Select items with weighted random choice
        selected = []
        available_copy = available_items.copy()
        weights_copy = weights.copy()
        
        for _ in range(min(num_items, len(available_copy))):
            item = random.choices(available_copy, weights=weights_copy)[0]
            idx = available_copy.index(item)
            selected.append(available_copy.pop(idx))
            weights_copy.pop(idx)
        
        return selected

    def _determine_order_priority(self) -> OrderPriority:
        """Determine order priority based on customer type and randomness"""
        if random.random() < self.model.config.overnight_order_probability:
            return OrderPriority.OVERNIGHT
        elif random.random() < self.express_probability:
            return OrderPriority.EXPRESS
        else:
            return OrderPriority.STANDARD

    def _maybe_cancel_order(self):
        """Enhanced cancellation logic using dedicated client's convenience methods"""
        if random.random() >= self.cancellation_rate:
            return

        try:
            # Get my recent orders that might be cancellable using convenience method
            my_orders = self.client.get_my_orders(self.name)
            
            # Filter for cancellable orders
            cancellable_orders = [
                order for order in my_orders
                if order.get('current_state') in ['pending', 'confirmed', 'picking', 'packed']
            ]
            
            if not cancellable_orders:
                return

            order_to_cancel = random.choice(cancellable_orders)
            order_id = order_to_cancel['order_id']
            
            # Use the dedicated client's cancel_order convenience method
            result = self.client.cancel_order(order_id, "Customer cancellation - changed requirements")
            
            if result:
                self.total_orders_cancelled += 1
                self.model.total_orders_cancelled += 1
                logger.info(f"{self.name}: Cancelled order {order_id}")

        except Exception as e:
            logger.error(f"{self.name}: Exception during cancellation: {e}")

    def _reset_order_interval(self):
        """Reset ordering interval with some variation"""
        self.steps_since_last_order = 0
        self.order_interval_min = int(
            self.model.config.customer_order_interval_min * 
            self.order_frequency_modifier * 
            random.uniform(0.8, 1.2)
        )


class EnhancedFulfillmentAgent(mesa.Agent):
    """Enhanced fulfillment agent with realistic operational constraints using dedicated warehouse client"""

    def __init__(self, model):
        super().__init__(model)
        # Use the dedicated warehouse client
        self.client = WarehouseClient(base_url=model.config.warehouse_url, role="fulfillment")
        self.name = f"Fulfillment_{self.unique_id}"
        self.agent_id = f"fulfillment_agent_{self.unique_id}"
        
        # Agent characteristics
        self.skill_level = random.uniform(0.8, 1.2)  # Affects work speed
        self.experience_level = random.choice(["junior", "senior", "expert"])
        self.shift_type = random.choice(list(ShiftType))
        self.specialized_zones = random.sample(list(WarehouseZone), k=random.randint(2, 3))
        
        # Operational state
        self.currently_processing: Set[str] = set()  # Order IDs being processed
        self.max_concurrent = model.config.max_concurrent_orders_per_agent
        self.steps_since_last_check = 0
        self.check_interval = model.config.fulfillment_check_interval
        
        # Performance tracking
        self.total_orders_processed = 0
        self.total_work_time = 0.0
        self.equipment_failures = 0
        self.quality_failures = 0
        
        # State flags
        self.equipment_broken = False
        self.equipment_repair_time = 0
        self.on_break = False
        self.break_time_remaining = 0

        logger.info("Fulfillment agent creation begins here ...")
        logger.info(f"Fulfillment agent {self.name} ({self.experience_level}, {self.shift_type.value} shift) created")

    def step(self):
        """
        Enhanced fulfillment agent step logic. The agent processes tasks from the 
        warehouse API when available and not busy with equipment issues or breaks.
        """
        logger.info(f"{self.name} entered the step function.")
        logger.info(f"{self.name}: shift_patterns_enabled={self.model.config.enable_shift_patterns}, on_shift={self._is_on_shift()}")
        # Add this debug block:
        logger.info(f"{self.name}: equipment_broken={self.equipment_broken}")
        logger.info(f"{self.name}: on_break={self.on_break}")
        logger.info(f"{self.name}: currently_processing={len(self.currently_processing)}, max_concurrent={self.max_concurrent}")
        logger.info(f"{self.name}: steps_since_last_check={self.steps_since_last_check}, check_interval={self.check_interval}")


        # Handle equipment repairs
        if self.equipment_broken:
            self.equipment_repair_time -= 1
            if self.equipment_repair_time <= 0:
                self.equipment_broken = False
                logger.info(f"{self.name}: Equipment repaired, back to work.")
            return

        # Handle breaks
        if self.on_break:
            self.break_time_remaining -= 1
            if self.break_time_remaining <= 0:
                self.on_break = False
                logger.info(f"{self.name}: Break finished, back to work.")
            return
        
        # Check if agent should be working based on shift patterns
        if self.model.config.enable_shift_patterns and not self._is_on_shift():
            return
        
        # Check if we should take a break (random chance based on work time)
        if (self.total_work_time > 0 and 
            random.random() < 0.001 and  # Low probability per step
            len(self.currently_processing) == 0):  # Only when not busy
            self._take_break()
            return
        
        # Process next available task if we have capacity
        if len(self.currently_processing) < self.max_concurrent:
            # Update step counter for periodic processing
            self.steps_since_last_check += 1
            
            # Only check for new work periodically to avoid overwhelming the API
            if self.steps_since_last_check >= self.check_interval:
                self.steps_since_last_check = 0
                self._process_next_task()
        
        # If we have ongoing work, continue processing it
        # (This handles multi-step tasks that take time to complete)
        if len(self.currently_processing) > 0:
            # In a more detailed simulation, we could track individual task progress here
            # For now, the _process_next_task() method handles the complete workflow
            pass
    def _is_on_shift(self) -> bool:
        """Check if agent is currently on their shift"""
        current_hour = (self.model.steps // 60) % 24
        
        if self.shift_type == ShiftType.MORNING:
            return 6 <= current_hour < 14
        elif self.shift_type == ShiftType.AFTERNOON:
            return 14 <= current_hour < 22
        else:  # NIGHT
            return current_hour >= 22 or current_hour < 6

    def _take_break(self):
        """Agent takes a break"""
        self.on_break = True
        self.break_time_remaining = random.randint(10, 30)  # 10-30 steps
        logger.info(f"{self.name}: Taking a break for {self.break_time_remaining} steps")


    def _process_next_task(self):
        """Enhanced task processing with proactive pending order discovery"""
        try:
            # Equipment failure check
            if (self.model.config.enable_operational_disruptions and 
                random.random() < self.model.config.equipment_failure_probability):
                self._equipment_failure()
                return
            
            # First try to get an existing queued task
            result = self.client.process_next_task(self.agent_id)
            logger.info(f"{self.name}: API returned: {result}")

            # If no queued tasks available, look for pending orders to confirm
            if result.get('message') == 'No fulfillment tasks available':
                if self._queue_pending_confirmations():
                    # Try again after queuing a confirmation task
                    result = self.client.process_next_task(self.agent_id)
                    logger.info(f"{self.name}: After queuing confirmation, API returned: {result}")

            if result.get('action') == 'task_completed':
                task = result['task']
                task_result = result['result']
                
                order_id = task['order_id']
                transition = task['transition']
                new_state = task_result.get('new_state', 'unknown')
                
                # Add to currently processing during work simulation
                self.currently_processing.add(order_id)
                
                logger.info(f"{self.name}: Processing {transition} for order {order_id}")
                
                # Calculate and simulate work time
                base_work_time = self._get_work_time(transition, order_id)
                actual_work_time = self._apply_agent_factors(base_work_time, transition)
                
                # Quality check for certain operations
                if self._quality_check_required(transition) and not self._passes_quality_check():
                    self._handle_quality_failure(task['task_id'], order_id, transition)
                    self.currently_processing.discard(order_id)
                    return
                
                logger.info(f"{self.name}: Working on {transition} for {actual_work_time:.1f} seconds...")
                time.sleep(actual_work_time * self.model.config.simulation_speed_factor)
                
                # Update metrics
                self.total_orders_processed += 1
                self.total_work_time += actual_work_time
                self.model.total_orders_processed += 1
                
                logger.info(f"{self.name}: Completed {transition} -> {new_state} for order {order_id}")
                
                if new_state == "delivered":
                    self.model.total_orders_completed += 1
                    # Update customer satisfaction
                    self._update_customer_satisfaction(order_id)
                
                # Auto-queue next transition for efficiency
                self._queue_next_transition(order_id, new_state)
                
                # Remove from processing
                self.currently_processing.discard(order_id)
                
            elif result.get('action') == 'task_failed':
                task = result['task']
                logger.error(f"{self.name}: Task failed - {result.get('error', 'Unknown error')}")
                self.currently_processing.discard(task.get('order_id', 'unknown'))

        except Exception as e:
            logger.error(f"{self.name}: Exception processing task: {e}")
            # Clean up any stale processing state
            if 'order_id' in locals():
                self.currently_processing.discard(order_id)

    def _queue_pending_confirmations(self) -> bool:
        """Check for pending orders and queue confirm tasks. Returns True if a task was queued."""
        try:
            orders = self.client.list_orders()
            if not orders:
                return False
                
            for order in orders:
                if order.get('current_state') == 'pending':
                    # Queue confirm task
                    confirm_result = self.client.request_transition(
                        order['order_id'], 
                        'confirm', 
                        notes="Auto-queued by fulfillment agent",
                        agent_id=self.agent_id
                    )
                    if confirm_result:
                        logger.info(f"{self.name}: Queued confirm task for pending order {order['order_id']}")
                        return True  # Only queue one at a time to avoid overwhelming
                        
            return False  # No pending orders found
            
        except Exception as e:
            logger.debug(f"{self.name}: Error queuing pending confirmations: {e}")
            return False



    def _get_work_time(self, transition: str, order_id: str) -> float:
        """Enhanced work time calculation with order-specific factors"""
        base_times = {
            "confirm": (3, 7),
            "start_picking": (8, 20),
            "pack": (5, 12),
            "ship": (3, 8),
            "deliver": (15, 45),
            "cancel_from_pending": (2, 4),
            "cancel_from_confirmed": (3, 6),
            "cancel_from_picking": (5, 10),
            "cancel_from_packed": (6, 12),
        }
        
        min_time, max_time = base_times.get(transition, (2, 5))
        base_time = random.uniform(min_time, max_time)
        
        # Apply order-specific factors
        try:
            order_details = self.client.get_order(order_id)
            if order_details:
                items = order_details.get('items', [])
                
                # More items = more time for picking and packing
                if transition in ["start_picking", "pack"]:
                    item_factor = 1.0 + (len(items) - 1) * 0.2
                    base_time *= item_factor
                
                # Check if order contains items from agent's specialized zones
                zone_factor = 1.0
                if transition == "start_picking":
                    for item_name in items:
                        item = next((i for i in self.model.config.inventory_items if i.name == item_name), None)
                        if item and item.zone not in self.specialized_zones:
                            zone_factor *= 1.2  # Takes longer in unfamiliar zones
                
                base_time *= zone_factor
        
        except Exception:
            pass  # Use base time if order details unavailable
        
        return base_time

    def _apply_agent_factors(self, base_time: float, transition: str) -> float:
        """Apply agent-specific factors to work time"""
        # Skill level affects all work
        time_with_skill = base_time / self.skill_level
        
        # Experience level affects complex operations more
        experience_factors = {
            "junior": 1.2,
            "senior": 1.0,
            "expert": 0.8
        }
        
        if transition in ["start_picking", "pack"]:  # Complex operations
            time_with_experience = time_with_skill * experience_factors[self.experience_level]
        else:
            time_with_experience = time_with_skill * (1.0 + (experience_factors[self.experience_level] - 1.0) * 0.5)
        
        # Peak hour slowdown
        current_hour = (self.model.steps // 60) % 24
        is_peak_hour = current_hour in [11, 12, 13, 17, 18, 19]
        
        if is_peak_hour:
            time_with_experience *= self.model.config.peak_hour_slowdown_factor
        
        return time_with_experience

    def _quality_check_required(self, transition: str) -> bool:
        """Determine if quality check is required for this transition"""
        return transition in ["pack", "ship"]

    def _passes_quality_check(self) -> bool:
        """Perform quality check"""
        return random.random() > self.model.config.quality_check_failure_rate

    def _handle_quality_failure(self, task_id: str, order_id: str, transition: str):
        """Handle quality check failure - task is already completed by dedicated client, log the failure"""
        self.quality_failures += 1
        self.model.total_quality_failures += 1
        
        # Note: The dedicated client's process_next_task already handled the task completion
        # We just need to log this as a quality failure for metrics
        logger.warning(f"{self.name}: Quality check failed for {transition} on order {order_id}")
        
        # In a real system, this might trigger rework or quality control processes

    def _equipment_failure(self):
        """Handle equipment failure"""
        self.equipment_broken = True
        self.equipment_repair_time = random.randint(30, 120)  # 30-120 steps to repair
        self.equipment_failures += 1
        self.model.total_equipment_failures += 1
        logger.warning(f"{self.name}: Equipment failure! Repair time: {self.equipment_repair_time} steps")

    def _update_customer_satisfaction(self, order_id: str):
        """Update customer satisfaction based on delivery performance"""
        try:
            order_details = self.client.get_order(order_id)
            if order_details:
                customer_name = order_details.get('customer_name')
                # Find customer agent and update satisfaction
                for agent in self.model.agents:
                    if (isinstance(agent, EnhancedCustomerAgent) and 
                        agent.name == customer_name):
                        # Check delivery time vs expectations
                        created_time = order_details.get('created_at')
                        # Simplified satisfaction update
                        agent.satisfaction_score = min(1.0, agent.satisfaction_score + 0.1)
                        break
        except Exception:
            pass

    def _queue_next_transition(self, order_id: str, current_state: str):
        """Queue the next transition using dedicated client's convenience methods"""
        try:
            # Use the dedicated client's state-specific methods for better integration
            if current_state == "confirmed":
                result = self.client.request_transition(order_id, 'start_picking', 
                                                       notes="Auto-queued by simulation",
                                                       agent_id=f"{self.agent_id}_auto")
            elif current_state == "picking":
                result = self.client.request_transition(order_id, 'pack',
                                                       notes="Auto-queued by simulation", 
                                                       agent_id=f"{self.agent_id}_auto")
            elif current_state == "packed":
                result = self.client.request_transition(order_id, 'ship',
                                                       notes="Auto-queued by simulation",
                                                       agent_id=f"{self.agent_id}_auto")
            elif current_state == "shipped":
                result = self.client.request_transition(order_id, 'deliver',
                                                       notes="Auto-queued by simulation",
                                                       agent_id=f"{self.agent_id}_auto")
            else:
                # No next transition for this state
                return
                
            if result:
                logger.debug(f"{self.name}: Queued next transition for order {order_id} from {current_state}")

        except Exception as e:
            logger.debug(f"{self.name}: Error queuing next transition: {e}")


class InventoryManager:
    """Manages warehouse inventory with realistic constraints"""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.inventory: Dict[str, int] = {}
        self.reserved: Dict[str, int] = {}
        
        # Initialize inventory
        for item in config.inventory_items:
            self.inventory[item.name] = item.stock_level
            self.reserved[item.name] = 0
    
    def is_available(self, item_name: str, quantity: int = 1) -> bool:
        """Check if item is available for order"""
        if not self.config.enable_inventory_constraints:
            return True
        
        available = self.inventory.get(item_name, 0) - self.reserved.get(item_name, 0)
        return available >= quantity
    
    def reserve_item(self, item_name: str, quantity: int = 1):
        """Reserve item for order"""
        if self.config.enable_inventory_constraints:
            self.reserved[item_name] = self.reserved.get(item_name, 0) + quantity
    
    def consume_item(self, item_name: str, quantity: int = 1):
        """Consume item when order is shipped"""
        if self.config.enable_inventory_constraints:
            self.inventory[item_name] = max(0, self.inventory.get(item_name, 0) - quantity)
            self.reserved[item_name] = max(0, self.reserved.get(item_name, 0) - quantity)
    
    def restock_item(self, item_name: str, quantity: int):
        """Restock item (supplier delivery)"""
        self.inventory[item_name] = self.inventory.get(item_name, 0) + quantity
    
    def get_low_stock_items(self) -> List[str]:
        """Get items that are below reorder point"""
        low_stock = []
        for item in self.config.inventory_items:
            if self.inventory.get(item.name, 0) <= item.reorder_point:
                low_stock.append(item.name)
        return low_stock
    
    def get_inventory_summary(self) -> Dict[str, Dict[str, int]]:
        """Get complete inventory summary"""
        summary = {}
        for item in self.config.inventory_items:
            summary[item.name] = {
                "stock": self.inventory.get(item.name, 0),
                "reserved": self.reserved.get(item.name, 0),
                "available": self.inventory.get(item.name, 0) - self.reserved.get(item.name, 0),
                "reorder_point": item.reorder_point
            }
        return summary


class EnhancedWarehouseModel(mesa.Model):
    def __init__(self, config=None, seed=None):
        super().__init__(seed=seed)

        model_ref = self  # Store reference to the model
        self.schedule = type('SimpleScheduler', (), {
            'step': lambda scheduler_self: [agent.step() for agent in model_ref.agents],
            'add': lambda scheduler_self, agent: None  # Agents are already in model_ref.agents
        })()
        
        self.config = config or SimulationConfig.from_env()
        
        # Validate configuration
        config_issues = self.config.validate_config()
        if config_issues:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {issue}" for issue in config_issues)
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Enhanced model statistics
        self.total_orders_created = 0
        self.total_orders_processed = 0
        self.total_orders_completed = 0
        self.total_orders_cancelled = 0
        self.total_express_orders = 0
        self.total_equipment_failures = 0
        self.total_quality_failures = 0
        self.total_weather_delays = 0

        # Initialize inventory manager
        self.inventory_manager = InventoryManager(self.config)

        # Create enhanced agents and add to scheduler
        for _ in range(self.config.num_customers):
            agent = EnhancedCustomerAgent(self)
            self.schedule.add(agent)
        for _ in range(self.config.num_fulfillment_agents):
            agent = EnhancedFulfillmentAgent(self)
            self.schedule.add(agent)

        # Enhanced data collector
        self.datacollector = DataCollector(
            model_reporters={
                # Core metrics
                "Total Orders Created": "total_orders_created",
                "Total Orders Processed": "total_orders_processed", 
                "Total Orders Completed": "total_orders_completed",
                "Total Orders Cancelled": "total_orders_cancelled",
                "Total Express Orders": "total_express_orders",
                
                # Operational metrics
                "Equipment Failures": "total_equipment_failures",
                "Quality Failures": "total_quality_failures",
                "Weather Delays": "total_weather_delays",
                
                # Performance metrics
                "Orders in Pipeline": lambda m: m.total_orders_created - m.total_orders_completed - m.total_orders_cancelled,
                "Fulfillment Rate (%)": lambda m: (m.total_orders_completed / max(1, m.total_orders_created)) * 100,
                "Express Order Rate (%)": lambda m: (m.total_express_orders / max(1, m.total_orders_created)) * 100,
                "Quality Failure Rate (%)": lambda m: (m.total_quality_failures / max(1, m.total_orders_processed)) * 100,
                
                # State tracking
                "Pending Orders": lambda m: m._count_orders_by_state("pending"),
                "Confirmed Orders": lambda m: m._count_orders_by_state("confirmed"),
                "Picking Orders": lambda m: m._count_orders_by_state("picking"),
                "Packed Orders": lambda m: m._count_orders_by_state("packed"),
                "Shipped Orders": lambda m: m._count_orders_by_state("shipped"),
                "Delivered Orders": lambda m: m._count_orders_by_state("delivered"),
                "Cancelled Orders": lambda m: m._count_orders_by_state("cancelled"),
                
                # Inventory metrics
                "Low Stock Items": lambda m: len(m.inventory_manager.get_low_stock_items()),
                "Total Reserved Items": lambda m: sum(m.inventory_manager.reserved.values()),
                
                # Queue and capacity metrics
                "Queue Size": lambda m: m._get_queue_size(),
                "Agents Working": lambda m: m._count_working_agents(),
                "Agents on Break": lambda m: m._count_agents_on_break(),
                "Agents with Broken Equipment": lambda m: m._count_agents_with_broken_equipment(),
            },
            agent_reporters={
                "Agent Type": lambda a: type(a).__name__,
                "Customer Type": lambda a: getattr(a, "customer_type", "N/A"),
                "Shift Type": lambda a: getattr(a, "shift_type", "N/A").value if hasattr(getattr(a, "shift_type", None), "value") else "N/A",
                "Orders Placed": lambda a: getattr(a, "total_orders_placed", 0),
                "Orders Cancelled": lambda a: getattr(a, "total_orders_cancelled", 0),
                "Orders Processed": lambda a: getattr(a, "total_orders_processed", 0),
                "Express Orders": lambda a: getattr(a, "total_express_orders", 0),
                "Equipment Failures": lambda a: getattr(a, "equipment_failures", 0),
                "Quality Failures": lambda a: getattr(a, "quality_failures", 0),
                "Satisfaction Score": lambda a: getattr(a, "satisfaction_score", 1.0),
                "Currently Processing": lambda a: len(getattr(a, "currently_processing", set())),
            },
        )

        self._test_warehouse_connection()
        logger.info(f"Enhanced simulation initialized with {len(self.agents)} agents")


    def _count_orders_by_state(self, state: str) -> int:
        """Count orders in specific state using dedicated client"""
        try:
            fulfillment_agents = [a for a in self.agents if isinstance(a, EnhancedFulfillmentAgent)]
            if fulfillment_agents:
                client = fulfillment_agents[0].client
                orders = client.list_orders()
                if orders:
                    return len([o for o in orders if o.get('current_state') == state])
            return 0
        except Exception:
            return 0

    def _get_queue_size(self) -> int:
        """Get total queue size using dedicated client"""
        try:
            fulfillment_agents = [a for a in self.agents if isinstance(a, EnhancedFulfillmentAgent)]
            if fulfillment_agents:
                client = fulfillment_agents[0].client
                status = client.get_queue_status()
                if status:
                    return status.get("total_queued", 0)
            return 0
        except Exception:
            return 0

    def _count_working_agents(self) -> int:
        """Count agents currently working"""
        count = 0
        for agent in self.agents:
            if isinstance(agent, EnhancedFulfillmentAgent):
                if (not agent.equipment_broken and not agent.on_break and 
                    len(agent.currently_processing) > 0):
                    count += 1
        return count

    def _count_agents_on_break(self) -> int:
        """Count agents on break"""
        return len([a for a in self.agents if isinstance(a, EnhancedFulfillmentAgent) and a.on_break])

    def _count_agents_with_broken_equipment(self) -> int:
        """Count agents with broken equipment"""
        return len([a for a in self.agents if isinstance(a, EnhancedFulfillmentAgent) and a.equipment_broken])

    def _test_warehouse_connection(self):
        """Test connection to warehouse service using dedicated client"""
        try:
            test_client = WarehouseClient(base_url=self.config.warehouse_url, role="customer")
            health_result = test_client.health_check()
            if health_result and health_result.get('status') == 'healthy':
                logger.info("Successfully connected to warehouse service")
            else:
                logger.error("Warehouse service health check failed")
        except Exception as e:
            logger.error(f"Failed to connect to warehouse service: {e}")

    def step(self):
            """Execute one enhanced simulation step"""
            self.steps += 1
            self.datacollector.collect(self)
            self.schedule.step()

            # Periodic inventory restocking
            if self.steps % 100 == 0:
                self._restock_inventory()

            # Weather delay simulation
            if (self.config.enable_operational_disruptions and
                random.random() < self.config.weather_delay_probability):
                self.total_weather_delays += 1
                logger.info(f"Weather delay event at step {self.steps}")

            # Progress logging
            if self.steps % 100 == 0 and self.steps > 0:
                self._log_comprehensive_status()

    def _restock_inventory(self):
        """Periodic inventory restocking"""
        low_stock_items = self.inventory_manager.get_low_stock_items()
        for item_name in low_stock_items:
            restock_quantity = random.randint(20, 50)
            self.inventory_manager.restock_item(item_name, restock_quantity)
            logger.info(f"Restocked {item_name}: +{restock_quantity} units")

    def _log_comprehensive_status(self):
        """Log comprehensive simulation status"""
        pipeline = self.total_orders_created - self.total_orders_completed - self.total_orders_cancelled
        fulfillment_rate = (self.total_orders_completed / max(1, self.total_orders_created)) * 100
        
        working_agents = self._count_working_agents()
        agents_on_break = self._count_agents_on_break()
        broken_equipment = self._count_agents_with_broken_equipment()
        
        logger.info(
            f"Step {self.steps}: Created={self.total_orders_created}, "
            f"Completed={self.total_orders_completed}, "
            f"Cancelled={self.total_orders_cancelled}, "
            f"Express={self.total_express_orders}, "
            f"Pipeline={pipeline}, "
            f"Fulfillment={fulfillment_rate:.1f}%, "
            f"Working={working_agents}, "
            f"OnBreak={agents_on_break}, "
            f"Broken={broken_equipment}, "
            f"QualityFails={self.total_quality_failures}"
        )

    def run_model(self, steps=None):
        """Run the enhanced simulation"""
        target = steps or self.config.max_steps
        logger.info(f"Starting enhanced simulation for {target} steps")
        
        while self.steps < target:
            self.step()
            time.sleep(0.05)  # Slower for observation
            
        logger.info(f"Enhanced simulation completed after {self.steps} steps")
        self._print_final_report()

    def _print_final_report(self):
        """Print comprehensive final report"""
        print(f"\n{'='*60}")
        print("ENHANCED WAREHOUSE SIMULATION FINAL REPORT")
        print(f"{'='*60}")
        
        print(f"\nORDER METRICS:")
        print(f"Total Orders Created: {self.total_orders_created}")
        print(f"Total Orders Completed: {self.total_orders_completed}")
        print(f"Total Orders Cancelled: {self.total_orders_cancelled}")
        print(f"Total Express Orders: {self.total_express_orders}")
        
        if self.total_orders_created > 0:
            fulfillment_rate = (self.total_orders_completed / self.total_orders_created) * 100
            express_rate = (self.total_express_orders / self.total_orders_created) * 100
            print(f"Fulfillment Rate: {fulfillment_rate:.1f}%")
            print(f"Express Order Rate: {express_rate:.1f}%")
        
        print(f"\nOPERATIONAL METRICS:")
        print(f"Equipment Failures: {self.total_equipment_failures}")
        print(f"Quality Failures: {self.total_quality_failures}")
        print(f"Weather Delays: {self.total_weather_delays}")
        
        if self.total_orders_processed > 0:
            quality_rate = (self.total_quality_failures / self.total_orders_processed) * 100
            print(f"Quality Failure Rate: {quality_rate:.1f}%")
        
        print(f"\nINVENTORY STATUS:")
        inventory_summary = self.inventory_manager.get_inventory_summary()
        for item_name, data in inventory_summary.items():
            if data["stock"] <= data["reorder_point"]:
                print(f"⚠️  {item_name}: {data['stock']} units (LOW STOCK)")
            else:
                print(f"✅ {item_name}: {data['stock']} units")


# Global model instance for Solara
_global_model = None

def _get_or_create_model() -> EnhancedWarehouseModel:
    """Get global model instance"""
    global _global_model
    if _global_model is None:
        config = SimulationConfig.from_env()
        _global_model = EnhancedWarehouseModel(config)
    return _global_model

@solara.component
def Page():
    """Enhanced Solara visualization dashboard"""
    model = _get_or_create_model()
    components = [
        # Core metrics
        make_plot_component("Total Orders Created"),
        make_plot_component("Total Orders Completed"), 
        make_plot_component("Total Express Orders"),
        make_plot_component("Total Orders Cancelled"),
        
        # Performance metrics
        make_plot_component("Fulfillment Rate (%)"),
        make_plot_component("Express Order Rate (%)"),
        make_plot_component("Quality Failure Rate (%)"),
        
        # State tracking
        make_plot_component("Pending Orders"),
        make_plot_component("Confirmed Orders"),
        make_plot_component("Picking Orders"),
        make_plot_component("Packed Orders"),
        make_plot_component("Shipped Orders"),
        make_plot_component("Delivered Orders"),
        
        # Operational metrics
        make_plot_component("Equipment Failures"),
        make_plot_component("Quality Failures"),
        make_plot_component("Agents Working"),
        make_plot_component("Agents on Break"),
        make_plot_component("Agents with Broken Equipment"),
        
        # Inventory and capacity
        make_plot_component("Low Stock Items"),
        make_plot_component("Total Reserved Items"),
        make_plot_component("Queue Size"),
        make_plot_component("Orders in Pipeline"),
    ]
    return SolaraViz(
        model, 
        components=components, 
        name="Enhanced Warehouse Simulation Dashboard"
    )


def make_solara_viz_server(config):
    """
    Creates and configures the Solara visualization server.
    """
    model = EnhancedWarehouseModel(config)
    components = [
        # Dashboard metrics
        make_plot_component("Total Orders Created"),
        make_plot_component("Total Orders Cancelled"),
        make_plot_component("Orders Shipped per Agent"),
        make_plot_component("Average Fulfillment Time"),
        
        # Operational metrics
        make_plot_component("Equipment Failures"),
        make_plot_component("Quality Failures"),
        make_plot_component("Agents Working"),
        make_plot_component("Agents on Break"),
        make_plot_component("Agents with Broken Equipment"),
        
        # Inventory and capacity
        make_plot_component("Low Stock Items"),
        make_plot_component("Total Reserved Items"),
        make_plot_component("Queue Size"),
        make_plot_component("Orders in Pipeline"),
    ]
    return SolaraViz(
        model, 
        components=components, 
        name="Enhanced Warehouse Simulation Dashboard"
    )
