"""Test script for a travel planner agent."""

import requests
import json
from datetime import datetime, timedelta

def test_travel_planner_agent():
    """Test the travel planner agent endpoints."""
    base_url = "http://localhost:10001"
    
    print("🎯 Testing Travel Planner Agent")
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
        
        test_message = f"Plan a 3-day trip to Paris for 2 guests from {check_in} to {check_out} with a mid-range budget. I need both hotel and car rental recommendations."
        
        payload = {"message": test_message}
        response = requests.post(
            f"{base_url}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # Longer timeout for complex operations
        )
        
        if response.status_code == 200:
            print("✅ Chat endpoint working")
            response_data = response.json()
            print(f"   Query: {test_message}")
            print(f"   Response: {response_data.get('response', 'No response')[:300]}...")
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Chat endpoint error: {e}")
    
    print("\n" + "=" * 50)
    print("Travel Planner Agent test completed!")

def test_agent_connectivity():
    """Test connectivity between all agents."""
    print("\n🔗 Testing Agent Connectivity")
    print("=" * 50)
    
    agents = {
        "Travel Planner": "http://localhost:10001",
        "Hotel Booking": "http://localhost:10002", 
        "Car Rental": "http://localhost:10003"
    }
    
    for agent_name, url in agents.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {agent_name} Agent: Running")
            else:
                print(f"❌ {agent_name} Agent: Not responding ({response.status_code})")
        except Exception as e:
            print(f"❌ {agent_name} Agent: Not reachable ({e})")

if __name__ == "__main__":
    test_travel_planner_agent()
    test_agent_connectivity()