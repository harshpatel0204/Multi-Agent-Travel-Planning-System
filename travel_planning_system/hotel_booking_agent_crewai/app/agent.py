import os
import json
import requests
from datetime import date
from typing import Type

from crewai import LLM, Agent, Crew, Process, Task,LLM
from crewai.tools import BaseTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class HotelSearchToolInput(BaseModel):
    """Input schema for HotelSearchTool."""

    location: str = Field(
        ...,
        description="The location/city to search for hotels in.",
    )
    check_in: str = Field(
        ...,
        description="Check-in date in YYYY-MM-DD format.",
    )
    check_out: str = Field(
        ...,
        description="Check-out date in YYYY-MM-DD format.",
    )
    budget: str = Field(
        default="any",
        description="Budget range (e.g., 'budget', 'mid-range', 'luxury', 'any').",
    )


class HotelSearchTool(BaseTool):
    name: str = "Hotel Search Tool"
    description: str = (
        "Search for hotels in a specific location with check-in and check-out dates. "
        "Use this to find available hotels and their details."
    )
    args_schema: Type[BaseModel] = HotelSearchToolInput

    def _run(self, location: str, check_in: str, check_out: str, budget: str = "any") -> str:
        """Search for hotels using web search."""
        serper_api_key = os.getenv("SERPER_API_KEY")
        print(f"SERPER_API_KEY: {'found' if serper_api_key else 'not found'}")  # Debug statement
        if not serper_api_key:
            return "SERPER_API_KEY not found in environment variables"
        
        # Bias search toward MakeMyTrip, Goibibo, Booking.com
        search_query = (
            f"Budget friendly hotels in {location} from {check_in} to {check_out}"
        )
        if budget != "any":
            search_query += f" {budget} hotels"
        
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
            
            # Extract hotel information
            results = []
            if "organic" in data:
                for result in data["organic"][:5]:
                    # Try to extract the price in USD from the snippet if possible
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
                        "location": location,
                        "check_in": check_in,
                        "check_out": check_out,
                        "budget": budget,
                        "estimated_cost_usd": price_usd if price_usd else "N/A"
                    })
            
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error searching for hotels: {str(e)}"


class HotelBookingToolInput(BaseModel):
    """Input schema for HotelBookingTool."""

    hotel_name: str = Field(
        ...,
        description="The name of the hotel to book.",
    )
    check_in: str = Field(
        ...,
        description="Check-in date in YYYY-MM-DD format.",
    )
    check_out: str = Field(
        ...,
        description="Check-out date in YYYY-MM-DD format.",
    )
    guests: int = Field(
        default=1,
        description="Number of guests.",
    )


class HotelBookingTool(BaseTool):
    name: str = "Hotel Booking Tool"
    description: str = (
        "Book a hotel room for specified dates and guests. "
        "Use this to make hotel reservations."
    )
    args_schema: Type[BaseModel] = HotelBookingToolInput

    def _run(self, hotel_name: str, check_in: str, check_out: str, guests: int = 1) -> str:
        """Simulate a hotel booking process."""
        # In a real implementation, this would integrate with hotel booking APIs
        booking_id = f"HB{date.today().strftime('%Y%m%d')}{hash(hotel_name) % 10000:04d}"
        
        booking = {
            "booking_id": booking_id,
            "hotel_name": hotel_name,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "status": "confirmed",
            "booking_date": date.today().isoformat()
        }
        
        return json.dumps(booking, indent=2)


class HotelBookingAgent:
    """Agent that handles hotel booking tasks."""

    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    def __init__(self):
        """Initializes the HotelBookingAgent."""
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set.")
        
        # Set environment variables for OpenRouter.  Use the .ai domain
        # for the API base; the .io URL returns 405 on POST requests and was
        # causing `Error code: 405` exceptions when the LLM was invoked.
        os.environ["OPENAI_API_KEY"] = openrouter_api_key
        os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"
        
        # CrewAI LLM configuration for OpenRouter
        self.llm = LLM(
            # model="gpt-4o-mini",
            model="openai/gpt-4o-mini",
            api_key=openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost",  # required by OpenRouter
                "X-Title": "TravelPlanningSystem",  # optional but good practice
            },
            # model_kwargs={},  # ← CRITICAL: empty this to prevent unsupported params
        )

        self.hotel_booking_assistant = Agent(
            role="Hotel Booking Specialist",
            goal="Find and book the best hotels for travelers based on their preferences and requirements.",
            backstory=(
                "You are an expert hotel booking specialist with years of experience in the travel industry. "
                "You have extensive knowledge of hotels worldwide and can find the perfect accommodation "
                "for any traveler's needs. You use advanced search tools to find current availability and "
                "pricing, and you can handle bookings efficiently. You always prioritize customer satisfaction "
                "and provide detailed information about each hotel option."
            ),
            verbose=True,
            allow_delegation=False,
            tools=[HotelSearchTool(), HotelBookingTool()],
            llm=self.llm,
        )

    def _build_crew(self, question: str):
        """Build the crew and task for a hotel booking question."""
        task_description = (
            f"MANDATORY: You MUST use the Hotel Search Tool to search for hotels for the user's request: '{question}'. "
            f"Today's date is {date.today().strftime('%Y-%m-%d')}. "
            f"If the user request doesn't contain enough information (location, dates), ask for missing details first. "
            f"If the user provides location and dates, immediately use the Hotel Search Tool with those parameters. "
            f"Always use tools when available rather than just explaining what you would do."
        )

        hotel_booking_task = Task(
            description=task_description,
            expected_output="""
                    [
                    {
                        "name": "Name of the  hotel",
                        "description": "A description of the hotel in no more than 40 words",
                        "link": "https://...(URL)",
                        "estimated_cost_usd": "$10"
                    },
                    ...
                ]
            """,
            agent=self.hotel_booking_assistant,
        )

        crew = Crew(
            agents=[self.hotel_booking_assistant],
            tasks=[hotel_booking_task],
            process=Process.sequential,
            verbose=True,
        )
        return crew

    def invoke(self, question: str) -> str:
        """Synchronous entry point (use only outside an async event loop)."""
        crew = self._build_crew(question)
        result = crew.kickoff()
        print(f"Hotel response CREWAI: {result.raw}")
        return result.raw

    async def invoke_async(self, question: str) -> str:
        """Async entry point — safe to call from FastAPI / any async context."""
        crew = self._build_crew(question)
        result = await crew.kickoff_async()
        print(f"Hotel response CREWAI (async): {result.raw}")
        return result.raw