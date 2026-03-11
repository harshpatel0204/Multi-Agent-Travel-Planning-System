"""Simple executor for hotel booking agent with chat endpoint."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import HotelBookingAgent
from a2a.types import AgentCard, AgentCapabilities, AgentSkill

import uvicorn

app = FastAPI(title="Hotel Booking Agent", version="1.0.0")

# Initialize the hotel booking agent
try:
    hotel_booking_agent = HotelBookingAgent()
except Exception as e:
    print(f"Error initializing hotel booking agent: {e}")
    hotel_booking_agent = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str

@app.post("/")
async def root():
    """Root endpoint to confirm the server is running."""
    return {"message": "Hotel Booking Agent is running. Use /chat to interact."}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint for hotel booking requests."""
    if not hotel_booking_agent:
        raise HTTPException(status_code=500, detail="Hotel booking agent not initialized")
    
    try:
        response = hotel_booking_agent.invoke(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not hotel_booking_agent:
        raise HTTPException(status_code=503, detail="Hotel booking agent not available")
    return {"status": "healthy", "agent": "Hotel_Booking_Agent"}


@app.get("/agent_card")
async def get_agent_card() -> AgentCard:
    """Return the agent card for this hotel booking agent."""
    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False
    )
    
    skills = [
        AgentSkill(
            id="hotel_search",
            name="Hotel Search",
            description="Search for hotels in specified locations and dates",
            tags=["travel", "accommodation", "search"],
            input_modes=["text"],
            output_modes=["text"]
        ),
        AgentSkill(
            id="hotel_booking", 
            name="Hotel Booking",
            description="Book hotel reservations",
            tags=["travel", "accommodation", "booking"],
            input_modes=["text"],
            output_modes=["text"]
        )
    ]
    
    return AgentCard(
        name="Hotel_Booking_Agent",
        description="Specialized agent for hotel research and booking using SerperAPI for real-time information.",
        version="1.0.0",
        url="http://localhost:10002",
        capabilities=capabilities,
        skills=skills,
        default_input_modes=["text"],
        default_output_modes=["text"]
    )


if __name__ == "__main__":
    print("🏨 Starting Hotel Booking Agent (CrewAI + OpenAI)")
    print("📍 Server will be available at: http://localhost:10002")
    print("🔗 Health check: http://localhost:10002/health")
    print("💬 Chat endpoint: http://localhost:10002/chat")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10002)