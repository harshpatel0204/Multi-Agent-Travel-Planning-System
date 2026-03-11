"""Simple executor for car rental agent with chat endpoint."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import CarRentalAgent
from a2a.types import AgentCard, AgentCapabilities, AgentSkill

import uvicorn

app = FastAPI(title="Car Rental Agent", version="1.0.0")

# Initialize the car rental agent
try:
    car_rental_agent = CarRentalAgent()
except Exception as e:
    print(f"Error initializing car rental agent: {e}")
    car_rental_agent = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint for car rental requests."""
    print(f"🚗 Received chat request: {request.message}")
    
    if not car_rental_agent:
        print("❌ Car rental agent not initialized")
        raise HTTPException(status_code=500, detail="Car rental agent not initialized")
    
    try:
        print("🔄 Calling car_rental_agent.invoke...")
        response = car_rental_agent.invoke(request.message, "default_context")
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
    if not car_rental_agent:
        raise HTTPException(status_code=503, detail="Car rental agent not available")
    return {"status": "healthy", "agent": "Car_Rental_Agent"}


@app.get("/agent_card")
async def get_agent_card() -> AgentCard:
    """Return the agent card for this car rental agent."""
    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False
    )
    
    skills = [
        AgentSkill(
            id="car_search",
            name="Car Rental Search",
            description="Search for car rental options in specified locations and dates",
            tags=["travel", "transportation", "search"],
            input_modes=["text"],
            output_modes=["text"]
        ),
        AgentSkill(
            id="car_booking",
            name="Car Rental Booking", 
            description="Book car rental reservations",
            tags=["travel", "transportation", "booking"],
            input_modes=["text"],
            output_modes=["text"]
        )
    ]
    
    return AgentCard(
        name="Car_Rental_Agent",
        description="Specialized agent for car rental research and booking using SerperAPI for real-time information.",
        version="1.0.0",
        url="http://localhost:10003",
        capabilities=capabilities,
        skills=skills,
        default_input_modes=["text"],
        default_output_modes=["text"]
    )


if __name__ == "__main__":
    print("🚗 Starting Car Rental Agent (LangGraph + OpenAI)")
    print("📍 Server will be available at: http://localhost:10003")
    print("🔗 Health check: http://localhost:10003/health")
    print("💬 Chat endpoint: http://localhost:10003/chat")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10003)