import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, AsyncIterable, List, Dict

import httpx
import nest_asyncio
import requests
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from langchain_openai import ChatOpenAI

from remote_agent_connection import RemoteAgentConnections

load_dotenv()
nest_asyncio.apply()


class TravelPlannerAgent:
    """The Travel Planner agent."""

    def __init__(
            self,
    ):
        self.remote_agent_connections: Dict[str, RemoteAgentConnections] = {}
        self.cards: Dict[str, AgentCard] = {}
        self.agents: str = ""
        self.httpx_client = None  # Will be initialized in _async_init_components
        # Use OpenRouter as the LLM for the agent if possible
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            self.llm = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                model="openai/gpt-4o-mini",
                default_headers={
                    "HTTP-Referer": "http://localhost",  # required by OpenRouter
                    "X-Title": "TravelPlanningSystem",  # optional but good practice
                },
                model_kwargs={},  # ← CRITICAL: empty this to prevent unsupported params
            )
        else:
            raise ValueError("OPENROUTER_API_KEY environment variable not set.")
        # Note: If Google ADK does not support direct LLM override, you may need to wrap OpenAI as a tool or use it as a backend for the agent's LLM.
        self._agent = self.create_agent()
        self._user_id = "travel_planner_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        print(f"🔗 Initializing connections to {len(remote_agent_addresses)} agents...")
        # Create a persistent HTTP client that won't be closed
        self.httpx_client = httpx.AsyncClient(timeout=30)
        
        for address in remote_agent_addresses:
            print(f"🔗 Connecting to agent at {address}...")
            # Use custom agent_card_path instead of default /.well-known/agent.json
            card_resolver = A2ACardResolver(self.httpx_client, address, agent_card_path="agent_card")
            try:
                card = await card_resolver.get_agent_card()
                print(f"✅ Got agent card: {card.name} - {card.description}")
                remote_connection = RemoteAgentConnections(
                    agent_card=card, agent_url=address, httpx_client=self.httpx_client
                )
                self.remote_agent_connections[card.name] = remote_connection
                self.cards[card.name] = card
                print(f"✅ Added agent {card.name} to connections")
            except httpx.ConnectError as e:
                print(f"❌ Failed to get agent card from {address}: {e}")
            except Exception as e:
                print(f"❌ Failed to initialize connection for {address}: {e}")

        print(f"🎯 Connected agents: {list(self.remote_agent_connections.keys())}")
        agent_info = [
            json.dumps({"name": card.name, "description": card.description})
            for card in self.cards.values()
        ]
        print("agent_info:", agent_info)
        self.agents = "\n".join(agent_info) if agent_info else "No agents found"

    @classmethod
    async def create(
            cls,
            remote_agent_addresses: List[str],
    ):
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self) -> Agent:
        return Agent(
            model="gemini-2.5-flash",
            name="Travel_Planner_Agent",
            instruction=self.root_instruction,
            description="This Travel Planner agent orchestrates travel planning and booking tasks.",
            tools=[
                self.send_message,
                self.search_flights,
                self.search_destinations,
                self.create_travel_itinerary,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        return f"""
        **Role:** You are the Travel Planner Agent, an expert travel coordinator. Your primary function is to plan and coordinate travel arrangements including flights, hotels, and car rentals.

        **Core Directives:**

        *   **Travel Planning:** When asked to plan a trip, first determine the destination, dates, and travel preferences from the user.
        *   **Flight Search:** Use the `search_flights` tool to find available flights to the destination.
        *   **Destination Research:** Use the `search_destinations` tool to gather information about the destination.
        *   **Task Delegation:** Use the `send_message` tool to coordinate with specialized agents:
            *   Ask the Hotel_Booking_Agent for hotel recommendations and bookings
            *   Ask the Car_Rental_Agent for car rental options and bookings
            *   Ask the Currency_Agent for currency conversion and exchange rates when dealing with international travel or budget planning
        *   **Budget Planning:** When users mention budget in foreign currencies, use Currency_Agent to convert to their local currency for better understanding
        *   **Itinerary Creation:** Use the `create_travel_itinerary` tool to compile all travel arrangements into a comprehensive itinerary.
        *   **Real-time Information:** All searches use SerperAPI to provide current, up-to-date information.
        *   **User Preferences:** Always consider user preferences for budget, location, and amenities.
        *   **Transparent Communication:** Keep the user informed of all planning steps and decisions.
        *   **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions.
        *   **Readability:** Make sure to respond in a concise and easy to read format (bullet points are good).

        **Today's Date (YYYY-MM-DD):** {datetime.now().strftime("%Y-%m-%d")}

        <Available Agents>
        {self.agents}
        </Available Agents>
        """

    async def stream(
            self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Streams the agent's response to a given query.
        """
        print(f"🎯 Starting stream for query: {query[:100]}...")
        try:
            session = await self._runner.session_service.get_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
            )
            content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
            if session is None:
                print("📝 Creating new session...")
                session = await self._runner.session_service.create_session(
                    app_name=self._agent.name,
                    user_id=self._user_id,
                    state={},
                    session_id=session_id,
                )
            
            print("🔄 Starting runner async...")
            async for event in self._runner.run_async(
                    user_id=self._user_id, session_id=session.id, new_message=content
            ):
                print(f"📦 Received event: {type(event)}, is_final: {event.is_final_response()}")
                if event.is_final_response():
                    print(f"✅ Final response received")
                    response = ""
                    if (
                            event.content
                            and event.content.parts
                            and event.content.parts[0].text
                    ):
                        print(f"📝 Extracting text from {len(event.content.parts)} parts")
                        response = "\n".join(
                            [p.text for p in event.content.parts if p.text]
                        )
                        print(f"📄 Response text: {response[:200]}...")
                    else:
                        print("⚠️  No text content in final response")
                    yield {
                        "is_task_complete": True,
                        "content": response,
                    }
                else:
                    yield {
                        "is_task_complete": False,
                        "updates": "The travel planner agent is thinking...",
                    }
        except Exception as e:
            print(f"💥 Exception in stream method: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            raise

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Sends a task to a remote agent."""
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {agent_name} not found")
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f"Client not available for {agent_name}")

        # Simplified task and context ID management
        state = tool_context.state
        task_id = state.get("task_id", str(uuid.uuid4()))
        context_id = state.get("context_id", str(uuid.uuid4()))
        message_id = str(uuid.uuid4())

        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": task}],
                "messageId": message_id,
                "taskId": task_id,
                "contextId": context_id,
            },
        }

        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )
        send_response: SendMessageResponse = await client.send_message(message_request)
        print("send_response", send_response)

        if not isinstance(
                send_response.root, SendMessageSuccessResponse
        ) or not isinstance(send_response.root.result, Task):
            print("Received a non-success or non-task response. Cannot proceed.")
            return None

        response_content = send_response.root.model_dump_json(exclude_none=True)
        json_content = json.loads(response_content)

        resp = []
        if json_content.get("result", {}).get("artifacts"):
            for artifact in json_content["result"]["artifacts"]:
                if artifact.get("parts"):
                    resp.extend(artifact["parts"])
        return resp

    async def search_flights(self, origin: str, destination: str, date: str, tool_context: ToolContext):
        """Search for flights using SerperAPI."""
        serper_api_key = os.getenv("SERPER_API_KEY")
        if not serper_api_key:
            return "SERPER_API_KEY not found in environment variables"

        search_query = f"flights from {origin} to {destination} on {date}"

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

            # Extract flight information
            results = []
            if "organic" in data:
                for result in data["organic"][:5]:
                    results.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "link": result.get("link", "")
                    })

            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error searching for flights: {str(e)}"

    async def search_destinations(self, destination: str, tool_context: ToolContext):
        """Search for destination information using SerperAPI."""
        serper_api_key = os.getenv("SERPER_API_KEY")
        if not serper_api_key:
            return "SERPER_API_KEY not found in environment variables"

        search_query = f"travel guide {destination} attractions hotels restaurants"

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

            # Extract destination information
            results = []
            if "organic" in data:
                for result in data["organic"][:5]:
                    results.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "link": result.get("link", "")
                    })

            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error searching for destination information: {str(e)}"

    async def create_travel_itinerary(self, destination: str, dates: str, flights: str, hotels: str, car_rentals: str,
                                      tool_context: ToolContext):
        """Create a comprehensive travel itinerary."""
        itinerary = {
            "destination": destination,
            "travel_dates": dates,
            "flights": json.loads(flights) if isinstance(flights, str) else flights,
            "hotels": json.loads(hotels) if isinstance(hotels, str) else hotels,
            "car_rentals": json.loads(car_rentals) if isinstance(car_rentals, str) else car_rentals,
            "created_at": datetime.now().isoformat(),
            "status": "planned"
        }

        return json.dumps(itinerary, indent=2)
    
    async def cleanup(self):
        """Cleanup resources including HTTP client."""
        if self.httpx_client:
            print("🧹 Closing HTTP client connections...")
            await self.httpx_client.aclose()
            self.httpx_client = None


def _get_initialized_travel_planner_agent_sync():
    """Synchronously creates and initializes the TravelPlannerAgent."""

    async def _async_main():
        # Hardcoded URLs for the specialized agents
        agent_urls = [
            "http://localhost:10002",  # Hotel Booking Agent
            "http://localhost:10003",  # Car Rental Agent
            "http://localhost:10004",  # Currency Agent
        ]

        print("initializing travel planner agent")
        travel_planner_instance = await TravelPlannerAgent.create(
            remote_agent_addresses=agent_urls
        )
        print("TravelPlannerAgent initialized")
        return travel_planner_instance.create_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print(
                f"Warning: Could not initialize TravelPlannerAgent with asyncio.run(): {e}. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing TravelPlannerAgent within an async function in your application."
            )
        else:
            raise


root_agent = _get_initialized_travel_planner_agent_sync()