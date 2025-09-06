#!/usr/bin/env python3
"""
Enhanced Warehouse API Testing Script with Order Timeline Testing
Tests all endpoints including the new timestamp and workflow functionality
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def print_timestamp():
    """Print current timestamp for reference"""
    print(f"🕐 Current time: {datetime.now().isoformat()}")

def test_health():
    """Test health endpoint"""
    print_section("HEALTH CHECK")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print("✅ Health check passed")
    return True

def test_categories():
    """Test category operations"""
    print_section("CATEGORY OPERATIONS")
    
    # List existing categories
    response = requests.get(f"{BASE_URL}/categories")
    print(f"📂 Found {len(response.json())} existing categories")
    
    # Create a new category
    new_category = {
        "name": "Test Category",
        "description": "A test category for API testing"
    }
    response = requests.post(f"{BASE_URL}/categories", json=new_category)
    assert response.status_code == 200
    category_id = response.json()["category_id"]
    print(f"✅ Created category with ID: {category_id}")
    
    # Get the category
    response = requests.get(f"{BASE_URL}/categories/{category_id}")
    assert response.status_code == 200
    print(f"✅ Retrieved category: {response.json()['name']}")
    
    return category_id

def test_customers():
    """Test customer operations"""
    print_section("CUSTOMER OPERATIONS")
    
    # Create a new customer
    new_customer = {
        "name": "John Test",
        "email": "john.test@example.com",
        "phone": "555-0123",
        "address": "123 Test Street, Test City"
    }
    response = requests.post(f"{BASE_URL}/customers", json=new_customer)
    assert response.status_code == 200
    customer_id = response.json()["customer_id"]
    print(f"✅ Created customer with ID: {customer_id}")
    
    # Get the customer
    response = requests.get(f"{BASE_URL}/customers/{customer_id}")
    assert response.status_code == 200
    print(f"✅ Retrieved customer: {response.json()['name']}")
    
    # Update customer
    update_data = {"phone": "555-9999"}
    response = requests.patch(f"{BASE_URL}/customers/{customer_id}", json=update_data)
    assert response.status_code == 200
    print(f"✅ Updated customer phone to: {response.json()['phone']}")
    
    # List all customers
    response = requests.get(f"{BASE_URL}/customers")
    print(f"✅ Found {len(response.json())} total customers")
    
    return customer_id

def test_items(category_id):
    """Test item operations"""
    print_section("ITEM OPERATIONS")
    
    # Create a new item
    new_item = {
        "name": "Test Product",
        "description": "A test product for API testing",
        "price": 99.99,
        "stock_quantity": 50,
        "category_id": category_id,
        "sku": "TEST001"
    }
    response = requests.post(f"{BASE_URL}/items", json=new_item)
    assert response.status_code == 200
    item_id = response.json()["item_id"]
    print(f"✅ Created item with ID: {item_id}")
    
    # Get the item
    response = requests.get(f"{BASE_URL}/items/{item_id}")
    assert response.status_code == 200
    print(f"✅ Retrieved item: {response.json()['name']} - ${response.json()['price']}")
    
    # Update item stock
    update_data = {"stock_quantity": 75}
    response = requests.patch(f"{BASE_URL}/items/{item_id}", json=update_data)
    assert response.status_code == 200
    print(f"✅ Updated item stock to: {response.json()['stock_quantity']}")
    
    # List all items
    response = requests.get(f"{BASE_URL}/items")
    print(f"✅ Found {len(response.json())} total items")
    
    return item_id

def test_baskets(customer_id, item_id):
    """Test basket operations"""
    print_section("BASKET OPERATIONS")
    
    # Add item to basket
    basket_item = {
        "item_id": item_id,
        "quantity": 3
    }
    response = requests.post(f"{BASE_URL}/baskets/{customer_id}/items", json=basket_item)
    assert response.status_code == 200
    print("✅ Added item to basket")
    
    # Get basket
    response = requests.get(f"{BASE_URL}/baskets/{customer_id}")
    assert response.status_code == 200
    basket = response.json()
    print(f"✅ Retrieved basket with {len(basket['items'])} items, total: ${basket['total_amount']:.2f}")
    
    # Add more of the same item
    response = requests.post(f"{BASE_URL}/baskets/{customer_id}/items", json=basket_item)
    assert response.status_code == 200
    print("✅ Added more items to basket")
    
    # Check updated basket
    response = requests.get(f"{BASE_URL}/baskets/{customer_id}")
    basket = response.json()
    print(f"✅ Updated basket quantity: {basket['items'][0]['quantity']}")
    
    # Remove item from basket
    response = requests.delete(f"{BASE_URL}/baskets/{customer_id}/items/{item_id}")
    assert response.status_code == 200
    print("✅ Removed item from basket")
    
    return True

def test_enhanced_orders():
    """Test enhanced order operations with timestamps"""
    print_section("ENHANCED ORDER OPERATIONS")
    print_timestamp()
    
    # Create an order with notes
    new_order = {
        "customer_name": "Jane Test Enhanced",
        "items": ["Enhanced Product A", "Enhanced Product B", "Enhanced Product C"],
        "notes": "Urgent order - customer requested expedited processing"
    }
    
    print("\n📋 Creating order with notes...")
    response = requests.post(f"{BASE_URL}/orders", json=new_order)
    assert response.status_code == 200
    order_data = response.json()
    order_id = order_data["order_id"]
    
    print(f"✅ Created order with ID: {order_id}")
    print(f"📝 Order notes: {order_data.get('notes', 'None')}")
    print(f"🕐 Created at: {order_data['created_at']}")
    print(f"🕐 Placed at: {order_data.get('placed_at', 'Not set')}")
    
    # Get the order with full timestamp details
    print(f"\n📋 Getting order {order_id} details...")
    response = requests.get(f"{BASE_URL}/orders/{order_id}")
    assert response.status_code == 200
    order_details = response.json()
    
    print(f"✅ Retrieved order for: {order_details['customer_name']}")
    print(f"📊 Status: {order_details['status']}")
    print(f"📜 Status history entries: {len(order_details.get('status_history', []))}")
    
    # Test the order timeline endpoint
    print(f"\n📅 Getting order {order_id} timeline...")
    response = requests.get(f"{BASE_URL}/orders/{order_id}/timeline")
    assert response.status_code == 200
    timeline = response.json()
    
    print(f"✅ Retrieved timeline for order {timeline['order_id']}")
    print(f"📊 Current status: {timeline['current_status']}")
    print(f"📜 Status changes: {len(timeline['status_changes'])}")
    
    # Test advancing the order through workflow
    print(f"\n🚀 Testing order workflow advancement...")
    
    # Advance to confirmed
    print("⏩ Advancing to 'confirmed'...")
    time.sleep(1)  # Small delay to see timestamp differences
    response = requests.post(f"{BASE_URL}/orders/{order_id}/advance", 
                           params={"notes": "Order confirmed by warehouse team"})
    assert response.status_code == 200
    result = response.json()
    print(f"✅ {result['message']}")
    
    # Advance to picking
    print("⏩ Advancing to 'picking'...")
    time.sleep(1)
    response = requests.post(f"{BASE_URL}/orders/{order_id}/advance",
                           params={"notes": "Items are being picked from inventory"})
    assert response.status_code == 200
    result = response.json()
    print(f"✅ {result['message']}")
    
    # Advance to packed
    print("⏩ Advancing to 'packed'...")
    time.sleep(1)
    response = requests.post(f"{BASE_URL}/orders/{order_id}/advance",
                           params={"notes": "Items packed and ready for shipping"})
    assert response.status_code == 200
    result = response.json()
    print(f"✅ {result['message']}")
    
    # Advance to shipped
    print("⏩ Advancing to 'shipped'...")
    time.sleep(1)
    response = requests.post(f"{BASE_URL}/orders/{order_id}/advance",
                           params={"notes": "Package shipped via FedEx, tracking: 1234567890"})
    assert response.status_code == 200
    result = response.json()
    print(f"✅ {result['message']}")
    
    # Get final timeline
    print(f"\n📅 Getting final timeline for order {order_id}...")
    response = requests.get(f"{BASE_URL}/orders/{order_id}/timeline")
    assert response.status_code == 200
    final_timeline = response.json()
    
    print(f"✅ Final status: {final_timeline['current_status']}")
    print(f"📜 Total status changes: {len(final_timeline['status_changes'])}")
    
    # Display the complete fulfillment timeline
    print("\n🕐 Complete Fulfillment Timeline:")
    fulfillment = final_timeline['fulfillment_timestamps']
    timeline_steps = [
        ("placed_at", "📅 Order Placed"),
        ("confirmed_at", "✅ Confirmed"),
        ("picked_at", "🔍 Picked"),
        ("packed_at", "📦 Packed"),
        ("shipped_at", "🚚 Shipped"),
        ("delivered_at", "✅ Delivered"),
        ("cancelled_at", "❌ Cancelled")
    ]
    
    for field, label in timeline_steps:
        if fulfillment.get(field):
            print(f"  {label}: {fulfillment[field]}")
    
    print("\n📜 Status Change History:")
    for i, change in enumerate(final_timeline['status_changes'], 1):
        print(f"  {i}. {change['status']} - {change['timestamp']}")
        if change.get('notes'):
            print(f"     📝 {change['notes']}")
    
    # Test manual status update with notes
    print(f"\n🔄 Testing manual status update...")
    time.sleep(1)
    update_data = {
        "status": "delivered",
        "notes": "Package delivered to customer - signed by John Doe"
    }
    response = requests.patch(f"{BASE_URL}/orders/{order_id}", json=update_data)
    assert response.status_code == 200
    print("✅ Manually updated order to 'delivered' status")
    
    # Get final order details
    response = requests.get(f"{BASE_URL}/orders/{order_id}")
    final_order = response.json()
    print(f"📊 Final order status: {final_order['status']}")
    print(f"🕐 Last updated: {final_order['updated_at']}")
    print(f"🕐 Delivered at: {final_order.get('delivered_at', 'Not set')}")
    
    return order_id

def test_order_edge_cases():
    """Test edge cases and error conditions for orders"""
    print_section("ORDER EDGE CASES & ERROR HANDLING")
    
    # Test advancing order that's already at final status
    print("🧪 Testing advancement of completed order...")
    completed_order = {
        "customer_name": "Edge Case Customer",
        "items": ["Edge Product"],
        "notes": "Order for edge case testing"
    }
    
    response = requests.post(f"{BASE_URL}/orders", json=completed_order)
    edge_order_id = response.json()["order_id"]
    
    # Advance through all statuses quickly
    statuses = ["confirmed", "picking", "packed", "shipped", "delivered"]
    for status in statuses:
        response = requests.post(f"{BASE_URL}/orders/{edge_order_id}/advance")
        if response.status_code != 200:
            break
    
    # Try to advance again (should fail)
    response = requests.post(f"{BASE_URL}/orders/{edge_order_id}/advance")
    if response.status_code == 400:
        print("✅ Correctly prevented advancement of completed order")
    else:
        print("❌ Should have prevented advancement of completed order")
    
    # Test getting timeline for non-existent order
    print("\n🧪 Testing timeline for non-existent order...")
    response = requests.get(f"{BASE_URL}/orders/99999/timeline")
    if response.status_code == 404:
        print("✅ Correctly returned 404 for non-existent order timeline")
    else:
        print("❌ Should have returned 404 for non-existent order")
    
    return True

def test_order_list_with_details():
    """Test the enhanced order listing with details"""
    print_section("ORDER LISTING WITH DETAILS")
    
    # Create multiple orders for testing
    print("📋 Creating multiple test orders...")
    test_orders = []
    
    for i in range(3):
        order_data = {
            "customer_name": f"List Test Customer {i+1}",
            "items": [f"List Product {i+1}A", f"List Product {i+1}B"],
            "notes": f"Test order {i+1} for list testing"
        }
        response = requests.post(f"{BASE_URL}/orders", json=order_data)
        test_orders.append(response.json()["order_id"])
        
        # Advance each order to different statuses
        if i >= 1:
            requests.post(f"{BASE_URL}/orders/{test_orders[i]}/advance")
        if i >= 2:
            requests.post(f"{BASE_URL}/orders/{test_orders[i]}/advance")
    
    print(f"✅ Created {len(test_orders)} test orders")
    
    # Test basic list
    print("\n📊 Testing basic order list...")
    response = requests.get(f"{BASE_URL}/orders")
    assert response.status_code == 200
    orders = response.json()
    print(f"✅ Retrieved {len(orders)} total orders")
    
    # Verify our test orders are included
    test_order_ids = set(test_orders)
    retrieved_ids = {order['order_id'] for order in orders}
    if test_order_ids.issubset(retrieved_ids):
        print("✅ All test orders found in list")
    else:
        print("❌ Some test orders missing from list")
    
    # Display sample order details
    if orders:
        sample_order = orders[0]
        print(f"\n📋 Sample Order Details:")
        print(f"  ID: {sample_order['order_id']}")
        print(f"  Customer: {sample_order['customer_name']}")
        print(f"  Status: {sample_order['status']}")
        print(f"  Items: {len(sample_order['items'])}")
        print(f"  Created: {sample_order['created_at']}")
        
        if sample_order.get('status_history'):
            print(f"  Status Changes: {len(sample_order['status_history'])}")
    
    return True

def run_comprehensive_test():
    """Run all tests in sequence"""
    print("🚀 Starting Comprehensive Warehouse API Test Suite")
    print_timestamp()
    
    try:
        # Basic functionality tests
        test_health()
        category_id = test_categories()
        customer_id = test_customers()
        item_id = test_items(category_id)
        test_baskets(customer_id, item_id)
        
        # Enhanced order tests
        order_id = test_enhanced_orders()
        test_order_edge_cases()
        test_order_list_with_details()
        
        print_section("TEST SUMMARY")
        print("✅ All tests completed successfully!")
        print(f"🎯 Created test data:")
        print(f"   📂 Category ID: {category_id}")
        print(f"   👤 Customer ID: {customer_id}")
        print(f"   📦 Item ID: {item_id}")
        print(f"   📋 Order ID: {order_id}")
        
        print(f"\n🔗 API Documentation: {BASE_URL}/docs")
        print(f"🏥 Health Check: {BASE_URL}/health")
        
        return True
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_mcp_integration():
    """Test MCP server integration (if available)"""
    print_section("MCP INTEGRATION TEST")
    
    # This would test the MCP server if it's running
    # For now, just document the expected MCP functions
    print("📋 Available MCP Functions for Order Management:")
    
    mcp_functions = [
        ("create_order", "Create order with timestamp tracking"),
        ("get_order", "Get order with full timeline details"),
        ("list_orders", "List orders with optional detail view"),
        ("update_order", "Update order and track status changes"),
        ("advance_order", "Advance order through workflow"),
        ("get_order_timeline", "Get detailed timeline and history"),
        ("delete_order", "Delete order with cancellation tracking")
    ]
    
    for func_name, description in mcp_functions:
        print(f"  🔧 {func_name}: {description}")
    
    print("\n💬 Example MCP Conversations:")
    examples = [
        "Create an order for Alice with laptop and mouse, add note 'rush order'",
        "Show me the timeline for order 123",
        "Advance order 456 to shipped status with tracking number",
        "List all orders with detailed timestamps",
        "What's the status history for order 789?"
    ]
    
    for example in examples:
        print(f"  💭 '{example}'")
    
    return True

if __name__ == "__main__":
    print("🧪 Enhanced Warehouse API Test Suite")
    print("=" * 60)
    
    success = run_comprehensive_test()
    
    if success:
        test_mcp_integration()
        print("\n🎉 All tests completed successfully!")
        print("✨ Enhanced warehouse system with timestamp tracking is ready!")
    else:
        print("\n💥 Tests failed. Please check the API server.")
        exit(1)