"""Test script for a hotel booking agent."""

import requests
import json
from datetime import datetime, timedelta

def test_hotel_agent():
    """Test the hotel booking agent endpoints."""
    base_url = "http://localhost:10002"
    
    print("🏨 Testing Hotel Booking Agent")
    print("=" * 50)
    
    # Test health endpoint
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test agent card endpoint
    print("\n2. Testing agent card endpoint...")
    try:
        response = requests.get(f"{base_url}/agent_card", timeout=5)
        if response.status_code == 200:
            print("✅ Agent card retrieved successfully")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Agent card failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Agent card error: {e}")
    
    # Test chat endpoint
    print("\n3. Testing chat endpoint...")
    try:
        # Calculate dates
        check_in = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=33)).strftime("%Y-%m-%d")
        
        test_message = f"Find budget-friendly hotels in Paris for 2 guests from {check_in} to {check_out}"
        
        payload = {"message": test_message}
        response = requests.post(
            f"{base_url}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Chat endpoint working")
            response_data = response.json()
            print(f"   Query: {test_message}")
            print(f"   Response: {response_data.get('response', 'No response')[:200]}...")
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Chat endpoint error: {e}")
    
    print("\n" + "=" * 50)
    print("Hotel Booking Agent test completed!")

if __name__ == "__main__":
    test_hotel_agent()