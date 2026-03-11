#!/usr/bin/env python3
"""
Simple test script for the Currency Agent
Tests the agent's ability to convert currencies and get exchange rates
"""

import requests


def test_currency_agent():
    """Test the currency agent endpoints."""
    base_url = "http://localhost:10004"
    
    print("💱 Testing Currency Agent")
    print("=" * 50)
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Agent card
    print("\n2. Testing agent card...")
    try:
        response = requests.get(f"{base_url}/agent_card", timeout=5)
        if response.status_code == 200:
            card_data = response.json()
            print(f"✅ Agent card: {card_data['name']} - {card_data['description'][:60]}...")
        else:
            print(f"❌ Agent card failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Agent card failed: {e}")
        return False
    
    # Test 3: Currency conversion
    print("\n3. Testing currency conversion...")
    test_queries = [
        "What is the current exchange rate from USD to EUR?",
        "Convert 100 USD to GBP",
        "How much is 50 EUR in JPY?"
    ]
    
    for query in test_queries:
        print(f"\n   Query: {query}")
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={"message": query},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')[:100]
                print(f"   ✅ Response: {response_text}...")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    print("\n" + "=" * 50)
    print("🎉 All Currency Agent tests passed!")
    return True


if __name__ == "__main__":
    print("🚀 Starting Currency Agent tests...")
    print("Make sure the currency agent is running on http://localhost:10004")
    print("")
    
    success = test_currency_agent()
    if success:
        print("\n✅ Currency Agent is working correctly!")
    else:
        print("\n❌ Currency Agent tests failed!")
        exit(1)