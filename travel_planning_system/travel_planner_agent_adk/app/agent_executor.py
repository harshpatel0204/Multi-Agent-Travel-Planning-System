"""Agent executor for travel planner agent."""

from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskArtifact,
    TaskArtifactPart,
)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import TravelPlannerAgent

import uvicorn

app = FastAPI(title="Travel Planner Agent", version="1.0.0")

# Initialize the travel planner agent
travel_planner_agent = TravelPlannerAgent()


class MessageRequest(BaseModel):
    """Request model for incoming messages."""

    message: Message


@app.post("/send_message")
async def send_message(request: SendMessageRequest) -> SendMessageResponse:
    """Handle incoming messages and return responses."""
    try:
        # Extract the user's question from the message
        user_message = request.params.message
        user_text = ""
        
        if user_message.parts:
            for part in user_message.parts:
                if hasattr(part, 'text') and part.text:
                    user_text += part.text
        
        if not user_text:
            raise HTTPException(status_code=400, detail="No text content found in message")
        
        # Process the request using the travel planner agent
        session_id = str(request.id)
        response_text = ""
        
        # Stream the response and collect it
        async for response_chunk in travel_planner_agent.stream(user_text, session_id):
            if response_chunk.get("is_task_complete"):
                response_text = response_chunk.get("content", "")
                break
        
        # Create response artifacts
        artifact_part = TaskArtifactPart(
            type="text",
            text=response_text
        )
        
        artifact = TaskArtifact(
            type="text/plain",
            parts=[artifact_part]
        )
        
        # Create the task result
        task = Task(
            artifacts=[artifact]
        )
        
        # Create a success response
        success_response = SendMessageSuccessResponse(
            result=task
        )
        
        return SendMessageResponse(
            id=request.id,
            root=success_response
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.get("/agent_card")
async def get_agent_card() -> AgentCard:
    """Return the agent card for this travel planner agent."""
    return AgentCard(
        name="Travel_Planner_Agent",
        description="Master travel coordinator that orchestrates hotel booking and car rental agents using A2A protocol.",
        version="1.0.0"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "Travel_Planner_Agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10001)