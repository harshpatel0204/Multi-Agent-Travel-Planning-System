"""Main entry point for the hotel booking agent."""

import uvicorn
from simple_executor import app

if __name__ == "__main__":
    print("🏨 Starting Hotel Booking Agent (CrewAI + Groq Llama-3 70B)")
    print("📍 Server will be available at: http://localhost:10002")
    print("🔗 Health check: http://localhost:10002/health")
    print("💬 Chat endpoint: http://localhost:10002/chat")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10002)