import os
import json
import requests
from collections.abc import AsyncIterable
from datetime import date
from typing import Any, Literal, List, Dict
from pydantic import BaseModel, HttpUrl

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

memory = MemorySaver()


class CarSearchToolInput(BaseModel):
    """Input schema for the car search tool."""

    location: str = Field(
        ...,
        description="The location/city to search for car rentals in.",
    )
    pickup_date: str = Field(
        ...,
        description="Pickup date in YYYY-MM-DD format.",
    )
    return_date: str = Field(
        ...,
        description="Return date in YYYY-MM-DD format.",
    )
    car_type: str = Field(
        default="any",
        description="Type of car (e.g., 'economy', 'luxury', 'suv', 'any').",
    )


@tool(args_schema=CarSearchToolInput)
def search_car_rentals(location: str, pickup_date: str, return_date: str, car_type: str = "any") -> list:
    """Search for car rental options in a specific location using web search."""
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        return []
    
    search_query = (
        f"car rental {location} from {pickup_date} to {return_date}"
    )
    if car_type != "any":
        search_query += f" {car_type} car"
    
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": serper_api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": search_query,
        "num": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        results = []
        if "organic" in data:
            for result in data["organic"][:5]:
                price_usd = None
                snippet = result.get("snippet", "")
                import re
                price_match = re.search(r"\$([0-9]+[,.]?[0-9]*)", snippet)
                if price_match:
                    price_usd = f"${price_match.group(1)} USD"
                results.append({
                    "name": result.get("title", ""),
                    "description": snippet,
                    "link": result.get("link", ""),
                    "estimated_cost_usd": price_usd if price_usd else "N/A"
                })
        return results
    except Exception as e:
        return []


class CarBookingToolInput(BaseModel):
    """Input schema for the car booking tool."""

    company: str = Field(
        ...,
        description="The car rental company name.",
    )
    location: str = Field(
        ...,
        description="The pickup location.",
    )
    pickup_date: str = Field(
        ...,
        description="Pickup date in YYYY-MM-DD format.",
    )
    return_date: str = Field(
        ...,
        description="Return date in YYYY-MM-DD format.",
    )
    car_type: str = Field(
        default="economy",
        description="Type of car to rent.",
    )


@tool(args_schema=CarBookingToolInput)
def book_car_rental(company: str, location: str, pickup_date: str, return_date: str, car_type: str = "economy") -> str:
    """Book a car rental for specified dates and location."""
    # In a real implementation, this would integrate with car rental booking APIs
    booking_id = f"CR{date.today().strftime('%Y%m%d')}{hash(company) % 10000:04d}"
    
    booking = {
        "booking_id": booking_id,
        "company": company,
        "location": location,
        "pickup_date": pickup_date,
        "return_date": return_date,
        "car_type": car_type,
        "status": "confirmed",
        "booking_date": date.today().isoformat()
    }
    
    return json.dumps(booking, indent=2)
class CarRentalAgency(BaseModel):
    name: str
    description: str
    link: HttpUrl
    estimated_cost_usd: str

class ResponseFormat(BaseModel):
    status: Literal["input_required", "completed", "error"] = "input_required"
    results: List[Dict] = Field(default_factory=list)
    message: str = ""

SYSTEM_INSTRUCTION = (
    "You are a car rental booking specialist. "
    "Your primary purpose is to help users find and book car rentals using the available tools. "
    "When presenting car rental options, you MUST put the list of car rental options as a list of dictionaries in the 'results' field of the response, and NOT in the 'message' field. "
    "The 'message' field should only contain a short summary or be left empty. Do NOT put the options as a string in the message. "
    "The 'results' field should look like this:\n"
    "'results': [\n"
    "  {\n"
    "    'name': 'Car Rental in Paris from $23/day - KAYAK',\n"
    "    'description': 'Looking for car rentals in Paris? ...',\n"
    "    'link': 'https://www.kayak.com/Cheap-Paris-Car-Rentals.36014.cars.ksp',\n"
    "    'estimated_cost_usd': '$23 USD'\n"
    "  },\n"
    "  ...\n"
    "]\n"
    "If you cannot find any options, return an empty list []. "
    "If the user asks about anything other than car rentals, politely state that you cannot help with that topic and can only assist with car rental queries. "
    "Set response status to input_required if the user needs to provide more information. "
    "Set response status to error if there is an error while processing the request. "
    "Set response status to completed if the request is complete."
)

class CarRentalAgent:
    """CarRentalAgent - a specialized assistant for car rental booking."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set.")
        
        self.model = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            model="openai/gpt-4o-mini",
            # model="openai/gpt-4o-mini",
            default_headers={
                "HTTP-Referer": "http://localhost",  # required by OpenRouter
                "X-Title": "TravelPlanningSystem",  # optional but good practice
            },
            model_kwargs={},  # ← CRITICAL: empty this to prevent unsupported params
        )
        self.tools = [search_car_rentals, book_car_rental]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=SYSTEM_INSTRUCTION,
        )

    def invoke(self, query, context_id):
        try:
            print(f"🚗 CarRentalAgent.invoke called with query: {query}, context_id: {context_id}")
            config: RunnableConfig = {"configurable": {"thread_id": context_id}}
            today_str = f"Today's date is {date.today().strftime('%Y-%m-%d')}."
            augmented_query = f"{today_str}\n\nUser query: {query}"
            
            print(f"🔄 Calling self.graph.invoke with augmented query...")
            response = self.graph.invoke({"messages": [("user", augmented_query)]}, config)
            print(f"📦 Graph response received: {type(response)}")
            print(f"📦 Response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            
            # Extract the final message content
            if "messages" not in response:
                print(f"❌ No 'messages' key in response: {response}")
                return "Error: No messages in response"
                
            messages = response["messages"]
            print(f"📧 Number of messages: {len(messages)}")
            
            if not messages:
                print(f"❌ Empty messages list")
                return "Error: Empty messages list"
                
            final_message = messages[-1]
            print(f"📧 Final message type: {type(final_message)}")
            print(f"📧 Final message: {final_message}")
            
            if hasattr(final_message, 'content'):
                response_text = final_message.content
                print(f"✅ Extracted content: {response_text}")
            else:
                response_text = str(final_message)
                print(f"✅ Converted to string: {response_text}")
            
            print(f"🎯 Final response: {response_text}")
            return response_text
        except Exception as e:
            print(f"💥 Exception in CarRentalAgent.invoke: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            raise

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        today_str = f"Today's date is {date.today().strftime('%Y-%m-%d')}."
        augmented_query = f"{today_str}\n\nUser query: {query}"
        inputs = {"messages": [("user", augmented_query)]}
        config: RunnableConfig = {"configurable": {"thread_id": context_id}}

        for item in self.graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Searching for car rental options...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing car rental information...",
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        messages = current_state.values.get("messages", [])
        
        if messages:
            final_message = messages[-1]
            if hasattr(final_message, 'content'):
                response_text = final_message.content
            else:
                response_text = str(final_message)
            
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response_text,
            }
        
        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": (
                "We are unable to process your request at the moment. "
                "Please try again."
            ),
        }