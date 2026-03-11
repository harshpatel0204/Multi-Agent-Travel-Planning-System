"""Simple executor for travel planner agent with chat endpoint."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import TravelPlannerAgent
from a2a.types import AgentCard

from a2a.types import AgentCapabilities, AgentSkill

import uvicorn

app = FastAPI(title="Travel Planner Agent", version="1.0.0")

# Initialize the travel planner agent
travel_planner_agent = None

async def initialize_travel_planner():
    """Initialize the travel planner agent with remote connections."""
    global travel_planner_agent
    try:
        agent_urls = [
            "http://localhost:10002",  # Hotel Booking Agent
            "http://localhost:10003",  # Car Rental Agent
            "http://localhost:10004",  # Currency Agent
        ]
        print("🚀 Initializing Travel Planner Agent with remote connections...")
        travel_planner_agent = await TravelPlannerAgent.create(agent_urls)
        print("✅ Travel Planner Agent initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing travel planner agent: {e}")
        travel_planner_agent = None

# FastAPI startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the travel planner agent on startup."""
    await initialize_travel_planner()

# FastAPI shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup travel planner agent on shutdown."""
    global travel_planner_agent
    if travel_planner_agent:
        print("🔄 Shutting down Travel Planner Agent...")
        await travel_planner_agent.cleanup()
        print("✅ Travel Planner Agent shutdown complete")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint for travel planning requests."""
    print(f"🎯 Received chat request: {request.message}")
    
    if not travel_planner_agent:
        print("❌ Travel planner agent not initialized")
        raise HTTPException(status_code=500, detail="Travel planner agent not initialized")
    
    try:
        print("🔄 Starting travel planner agent stream...")
        session_id = "default_session"
        response_text = ""
        
        # Stream the response and collect it
        async for response_chunk in travel_planner_agent.stream(request.message, session_id):
            print(f"📦 Received response chunk: {response_chunk}")
            if response_chunk.get("is_task_complete"):
                response_text = response_chunk.get("content", "")
                print(f"✅ Task completed, response: {response_text[:100]}...")
                break
        
        print(f"📝 Returning response: {response_text[:100]}...")
        return ChatResponse(response=response_text)
    except Exception as e:
        print(f"💥 Exception in chat endpoint: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not travel_planner_agent:
        raise HTTPException(status_code=503, detail="Travel planner agent not available")
    return {"status": "healthy", "agent": "Travel_Planner_Agent"}


@app.get("/agent_card")
async def get_agent_card() -> AgentCard:
    """Return the agent card for this travel planner agent."""
    
    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False
    )
    
    skills = [
        AgentSkill(
            id="travel_planning",
            name="Travel Planning",
            description="Coordinate complete travel planning including flights, hotels, and car rentals",
            tags=["travel", "coordination", "planning"],
            input_modes=["text"],
            output_modes=["text"]
        ),
        AgentSkill(
            id="flight_search",
            name="Flight Search", 
            description="Search for flights between destinations",
            tags=["travel", "flights", "search"],
            input_modes=["text"],
            output_modes=["text"]
        ),
        AgentSkill(
            id="destination_research",
            name="Destination Research",
            description="Research destination information and attractions",
            tags=["travel", "research", "destinations"],
            input_modes=["text"],
            output_modes=["text"]
        )
    ]
    
    return AgentCard(
        name="Travel_Planner_Agent",
        description="Master travel coordinator that orchestrates hotel booking and car rental agents using A2A protocol.",
        version="1.0.0",
        url="http://localhost:10001",
        capabilities=capabilities,
        skills=skills,
        default_input_modes=["text"],
        default_output_modes=["text"]
    )


if __name__ == "__main__":
    print("🎯 Starting Travel Planner Agent (Google ADK + A2A Protocol)")
    print("📍 Server will be available at: http://localhost:10001")
    print("🔗 Health check: http://localhost:10001/health")
    print("💬 Chat endpoint: http://localhost:10001/chat")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10001)