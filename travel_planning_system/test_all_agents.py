"""Test script for all agents in the multi-agent travel planning system."""

import requests
import time
from datetime import datetime, timedelta

def test_agent_health(agent_name, url):
    """Test health endpoint for a specific agent."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ {agent_name}: Running")
            return True
        else:
            print(f"❌ {agent_name}: Not responding ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {agent_name}: Not reachable ({e})")
        return False

def test_system_integration():
    """Test the complete multi-agent system integration."""
    print("🌐 Multi-Agent Travel Planning System Test")
    print("=" * 60)
    
    # Define agents
    agents = {
        "Travel Planner Agent": "http://localhost:10001",
        "Hotel Booking Agent": "http://localhost:10002", 
        "Car Rental Agent": "http://localhost:10003",
        "Currency Agent": "http://localhost:10004"
    }
    
    # Step 1: Check all agents are running
    print("1. Checking agent health...")
    all_healthy = True
    for agent_name, url in agents.items():
        healthy = test_agent_health(agent_name, url)
        all_healthy = all_healthy and healthy
    
    if not all_healthy:
        print("\n❌ Some agents are not running. Please start all agents before testing.")
        return
    
    print("\n✅ All agents are running!")
    
    # Step 2: Test agent cards
    print("\n2. Testing agent cards...")
    for agent_name, url in agents.items():
        try:
            response = requests.get(f"{url}/agent_card", timeout=5)
            if response.status_code == 200:
                card = response.json()
                print(f"✅ {agent_name}: {card.get('name', 'Unknown')} - {card.get('description', 'No description')[:50]}...")
            else:
                print(f"❌ {agent_name}: Agent card failed ({response.status_code})")
        except Exception as e:
            print(f"❌ {agent_name}: Agent card error ({e})")
    
    # Step 3: Test individual agent functionality
    print("\n3. Testing individual agents...")
    
    # Calculate test dates
    check_in = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    check_out = (datetime.now() + timedelta(days=33)).strftime("%Y-%m-%d")
    
    # Test Hotel Booking Agent
    print("\n   3a. Testing Hotel Booking Agent...")
    try:
        hotel_query = f"Find budget-friendly hotels in Paris for 2 guests from {check_in} to {check_out}"
        response = requests.post(
            f"{agents['Hotel Booking Agent']}/chat",
            json={"message": hotel_query},
            timeout=30
        )
        if response.status_code == 200:
            print(f"   ✅ Hotel agent responded successfully")
        else:
            print(f"   ❌ Hotel agent failed ({response.status_code})")
    except Exception as e:
        print(f"   ❌ Hotel agent error: {e}")
    
    # Test Car Rental Agent
    print("\n   3b. Testing Car Rental Agent...")
    try:
        car_query = f"Find car rental options in Paris from {check_in} to {check_out}"
        response = requests.post(
            f"{agents['Car Rental Agent']}/chat",
            json={"message": car_query},
            timeout=30
        )
        if response.status_code == 200:
            print(f"   ✅ Car rental agent responded successfully")
        else:
            print(f"   ❌ Car rental agent failed ({response.status_code})")
    except Exception as e:
        print(f"   ❌ Car rental agent error: {e}")

    # Test Currency Agent
    print("\n   3c. Testing Currency Agent...")
    try:
        currency_query = "What is the current exchange rate from USD to EUR?"
        response = requests.post(
            f"{agents['Currency Agent']}/chat",
            json={"message": currency_query},
            timeout=30
        )
        if response.status_code == 200:
            print(f"   ✅ Currency agent responded successfully")
        else:
            print(f"   ❌ Currency agent failed ({response.status_code})")
    except Exception as e:
        print(f"   ❌ Currency agent error: {e}")
    
    # Step 4: Test integrated travel planning
    print("\n4. Testing integrated travel planning...")
    try:
        travel_query = f"Plan a 3-day trip to Paris for 2 guests from {check_in} to {check_out} with a mid-range budget. I need both hotel and car rental recommendations."
        
        print(f"   Query: {travel_query}")
        print("   Processing... (this may take 30-60 seconds)")
        
        response = requests.post(
            f"{agents['Travel Planner Agent']}/chat",
            json={"message": travel_query},
            timeout=90
        )
        
        if response.status_code == 200:
            response_data = response.json()
            travel_plan = response_data.get('response', '')
            print(f"   ✅ Travel planner created comprehensive plan")
            print(f"   📋 Plan summary: {travel_plan[:200]}...")
        else:
            print(f"   ❌ Travel planner failed ({response.status_code})")
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Travel planner error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Multi-Agent System Test Completed!")
    print("\nTo run the Streamlit UI:")
    print("   cd travel_planning_system")
    print("   streamlit run streamlit_travel_app.py")

def run_performance_test():
    """Run a performance test with multiple concurrent requests."""
    print("\n⚡ Performance Test")
    print("=" * 30)
    
    agents = {
        "Hotel": "http://localhost:10002",
        "Car Rental": "http://localhost:10003",
        "Currency": "http://localhost:10004"
    }
    
    start_time = time.time()
    
    # Test concurrent requests
    import threading
    results = {}
    
    def test_agent(agent_name, url):
        try:
            response = requests.post(
                f"{url}/chat",
                json={"message": "Quick test query"},
                timeout=15
            )
            results[agent_name] = response.status_code == 200
        except:
            results[agent_name] = False
    
    threads = []
    for agent_name, url in agents.items():
        thread = threading.Thread(target=test_agent, args=(agent_name, url))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Concurrent requests completed in {duration:.2f} seconds")
    for agent_name, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"   {agent_name}: {status}")

if __name__ == "__main__":
    test_system_integration()
    run_performance_test()