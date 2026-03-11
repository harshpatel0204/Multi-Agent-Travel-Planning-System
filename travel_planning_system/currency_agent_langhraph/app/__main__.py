"""Main entry point for the hotel booking agent."""

import uvicorn
from simple_executor import app

if __name__ == "__main__":
    print("🚗 Starting Currency Agent (LangGraph + OpenAI)")
    print("📍 Server will be available at: http://localhost:10004")
    print("🔗 Health check: http://localhost:10004/health")
    print("💬 Chat endpoint: http://localhost:10004/chat")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10004)