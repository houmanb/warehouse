#!/usr/bin/env python3
"""
Enhanced Warehouse API Testing Script
Tests all the new endpoints and functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print("✅ Health check passed")

def test_categories():
    """Test category operations"""
    print("\n📂 Testing Categories...")
    
    # List existing categories
    response = requests.get(f"{BASE_URL}/categories")
    print(f"Found {len(response.json())} existing categories")
    
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
    print("\n👥 Testing Customers...")
    
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
    print("\n📦 Testing Items...")
    
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
    print("\n🛒 Testing Baskets...")
    
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

def test_orders():
    """Test order operations (existing functionality)"""
    print("\n📋 Testing Orders...")
    
    # Create an order
    new_order = {
        "customer_name": "Jane Test",
        "items": ["Test Product A", "Test Product B"]
    }
    response = requests.post(f"{BASE_URL}/orders", json=new_order)
    assert response.status_code == 200
    order_id = response.json()["order_id"]
    print(f"✅ Created order with ID: {order_id}")
    
    # Get the order
    response = requests.get(f"{BASE_URL}/orders/{order_id}")
    assert response.status_code == 200
    print(f"✅ Retrieved order for: {response.json()['customer_name']}")
    
    # Update order status
    update