"""Main entry point for the travel planner agent."""

import uvicorn
from simple_executor import app

if __name__ == "__main__":
    print("🎯 Starting Travel Planner Agent (Google ADK + A2A Protocol)")
    print("📍 Server will be available at: http://localhost:10001")
    print("🔗 Health check: http://localhost:10001/health")
    print("💬 Chat endpoint: http://localhost:10001/chat")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10001)