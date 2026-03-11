"""Agent executor for currency agent."""

from a2a.types import (
    AgentCard,
    AgentCapabilities, 
    AgentSkill,
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

from agent import CurrencyAgent

import uvicorn

app = FastAPI(title="Currency Agent", version="1.0.0")

# Initialize the currency agent
try:
    currency_agent = CurrencyAgent()
except Exception as e:
    print(f"Error initializing currency agent: {e}")
    currency_agent = None


class MessageRequest(BaseModel):
    """Request model for incoming messages."""

    message: Message


@app.post("/send_message")
async def send_message(request: SendMessageRequest) -> SendMessageResponse:
    """Handle incoming messages and return responses."""
    try:
        if not currency_agent:
            raise HTTPException(status_code=500, detail="Currency agent not initialized")
        
        # Extract the user's question from the message
        user_message = request.params.message
        user_text = ""
        
        if user_message.parts:
            for part in user_message.parts:
                if hasattr(part, 'text') and part.text:
                    user_text += part.text
        
        if not user_text:
            raise HTTPException(status_code=400, detail="No text content found in message")
        
        # Process the request using the currency agent
        response = currency_agent.invoke(user_text, str(request.id))
        
        # Extract content from response
        if isinstance(response, dict) and 'content' in response:
            response_text = response['content']
        else:
            response_text = str(response)
        
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not currency_agent:
        raise HTTPException(status_code=503, detail="Currency agent not available")
    return {"status": "healthy", "agent": "Currency_Agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10004)