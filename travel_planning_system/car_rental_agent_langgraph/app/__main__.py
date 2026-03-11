"""Main entry point for the car rental agent."""

import uvicorn
from simple_executor import app

if __name__ == "__main__":
    print("🚗 Starting Car Rental Agent (LangGraph + OpenAI)")
    print("📍 Server will be available at: http://localhost:10003")
    print("🔗 Health check: http://localhost:10003/health")
    print("💬 Chat endpoint: http://localhost:10003/chat")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10003)