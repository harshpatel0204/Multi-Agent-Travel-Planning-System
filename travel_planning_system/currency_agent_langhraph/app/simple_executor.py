"""Simple executor for currency agent with chat endpoint."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import CurrencyAgent
from a2a.types import AgentCard, AgentCapabilities, AgentSkill

import uvicorn

app = FastAPI(title="Currency Agent", version="1.0.0")

# Initialize the currency agent
try:
    currency_agent = CurrencyAgent()
except Exception as e:
    print(f"Error initializing currency agent: {e}")
    currency_agent = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint for currency conversion requests."""
    print(f"💱 Received chat request: {request.message}")
    
    if not currency_agent:
        print("❌ Currency agent not initialized")
        raise HTTPException(status_code=500, detail="Currency agent not initialized")
    
    try:
        print("🔄 Calling currency_agent.invoke...")
        response = currency_agent.invoke(request.message, "default_context")
        print(f"📦 Raw response from agent: {type(response)} - {response}")
        
        # Extract content from the response if it's a dict
        if isinstance(response, dict) and 'content' in response:
            response_text = str(response['content'])
            print(f"📝 Extracted content from dict: {response_text}")
        else:
            response_text = str(response)
            print(f"📝 Converting response to string: {response_text}")
            
        print(f"✅ Returning response: {response_text[:100]}...")
        return ChatResponse(response=response_text)
    except Exception as e:
        print(f"💥 Exception in chat endpoint: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not currency_agent:
        raise HTTPException(status_code=503, detail="Currency agent not available")
    return {"status": "healthy", "agent": "Currency_Agent"}


@app.get("/agent_card")
async def get_agent_card() -> AgentCard:
    """Return the agent card for this currency agent."""
    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False
    )
    
    skills = [
        AgentSkill(
            id="currency_conversion",
            name="Currency Conversion",
            description="Convert between different currencies using real-time exchange rates",
            tags=["finance", "currency", "conversion"],
            input_modes=["text"],
            output_modes=["text"]
        ),
        AgentSkill(
            id="exchange_rates",
            name="Exchange Rates",
            description="Get current or historical exchange rates between currencies",
            tags=["finance", "exchange", "rates"],
            input_modes=["text"],
            output_modes=["text"]
        )
    ]
    
    return AgentCard(
        name="Currency_Agent",
        description="Specialized agent for currency conversion and exchange rate information using real-time data.",
        version="1.0.0",
        url="http://localhost:10004",
        capabilities=capabilities,
        skills=skills,
        default_input_modes=["text"],
        default_output_modes=["text"]
    )


if __name__ == "__main__":
    print("💱 Starting Currency Agent (LangGraph + OpenAI)")
    print("📍 Server will be available at: http://localhost:10004")
    print("🔗 Health check: http://localhost:10004/health")
    print("💬 Chat endpoint: http://localhost:10004/chat")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10004)