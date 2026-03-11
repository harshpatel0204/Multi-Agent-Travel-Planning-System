#!/usr/bin/env python3
"""
Standalone Streamlit Travel Planning App
Uses the same logic as simple_travel_planner.py but with a user-friendly interface.
"""

import streamlit as st
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import re

# Load environment variables
load_dotenv()

class TravelPlannerApp:
    """Travel planner app with the same logic as simple_travel_planner.py."""
    
    def __init__(self):
        """Initialize the travel planner app."""
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            st.error("OPENROUTER_API_KEY not found in environment variables")
            st.stop()
        
        # Use the correct OpenRouter API base (the .ai domain).
        # The older "openrouter.io" endpoint returns 405 Method Not Allowed when
        # used for /chat/completions, which was causing errors in the UI.
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            model="openai/gpt-4o-mini",
        )
        # Agent endpoints
        self.hotel_agent_url = "http://localhost:10002"
        self.car_rental_agent_url = "http://localhost:10003"
        self.currency_agent_url = "http://localhost:10004"
        
    def check_agent_status(self):
        """Check if the other agents are running."""
        agents_status = {}
        
        # Check hotel agent
        try:
            response = requests.get(f"{self.hotel_agent_url}/health", timeout=5)
            if response.status_code == 200:
                agents_status["hotel"] = "✅ Running"
            else:
                agents_status["hotel"] = "❌ Not responding"
        except:
            agents_status["hotel"] = "❌ Not reachable"
        
        # Check car rental agent
        try:
            response = requests.get(f"{self.car_rental_agent_url}/health", timeout=5)
            if response.status_code == 200:
                agents_status["car_rental"] = "✅ Running"
            else:
                agents_status["car_rental"] = "❌ Not responding"
        except:
            agents_status["car_rental"] = "❌ Not reachable"
        
        # Check currency agent
        try:
            response = requests.get(f"{self.currency_agent_url}/health", timeout=5)
            if response.status_code == 200:
                agents_status["currency"] = "✅ Running"
            else:
                agents_status["currency"] = "❌ Not responding"
        except:
            agents_status["currency"] = "❌ Not reachable"
        
        return agents_status
    
    def ask_hotel_agent(self, query):
        """Ask the hotel booking agent for recommendations."""
        try:
            payload = {"message": query}
            response = requests.post(
                f"{self.hotel_agent_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # The hotel agent returns {"response": "actual_response"}
                return response_data.get("response", "No response from hotel agent")
            else:
                return f"Hotel agent error: {response.status_code}"
                
        except Exception as e:
            return f"Error communicating with hotel agent: {e}"
    
    def ask_car_rental_agent(self, query):
        """Ask the car rental agent for recommendations."""
        try:
            payload = {"message": query}
            response = requests.post(
                f"{self.car_rental_agent_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # The car rental agent returns {"response": "actual_response"}
                return response_data.get("response", "No response from car rental agent")
            else:
                return f"Car rental agent error: {response.status_code}"
                
        except Exception as e:
            return f"Error communicating with car rental agent: {e}"
    
    def ask_currency_agent(self, query):
        """Ask the currency agent for exchange rates."""
        try:
            payload = {"message": query}
            response = requests.post(
                f"{self.currency_agent_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data.get("response", "No response from currency agent")
            else:
                return f"Currency agent error: {response.status_code}"
                
        except Exception as e:
            return f"Error communicating with currency agent: {e}"
    
    def plan_trip(self, destination, check_in, check_out, budget, guests, car_needed, preferred_currency="USD", budget_amount=1000):
        """Plan a complete trip by coordinating with other agents."""
        # Check agent status
        status = self.check_agent_status()
        
        # Ask currency agent for exchange rates and budget conversion
        currency_response = ""
        if preferred_currency != "USD":
            currency_query = f"Convert {budget_amount} {preferred_currency} to USD for travel budget planning. Also provide current exchange rates for {preferred_currency} to major currencies (USD, EUR, GBP)."
            currency_response = self.ask_currency_agent(currency_query)
            print(f"Currency response: {currency_response}")
        else:
            # If already USD, still get some exchange rates for the destination
            currency_query = f"Provide current exchange rates from USD to local currency for {destination}. Also show rates to EUR and GBP for reference."
            currency_response = self.ask_currency_agent(currency_query)
            print(f"Currency response: {currency_response}")
        
        # Ask hotel agent for recommendations
        hotel_query = f"Find top 10 budget-friendly hotels in {destination} for {guests} guests from {check_in} to {check_out}"
        if budget != "any":
            hotel_query += f" with {budget} budget (approximately {budget_amount} {preferred_currency})"
        
        hotel_response = self.ask_hotel_agent(hotel_query)
        print(f"Hotel response CREWAI: {hotel_response}")
        
        # Ask a car rental agent for recommendations (if needed)
        car_response = ""
        if car_needed:
            car_query = f"Find car rental options in {destination} from {check_in} to {check_out}"
            car_response = self.ask_car_rental_agent(car_query)
        print(f"Car response LANGGRAPH: {car_response}")
        
        # Create a comprehensive travel plan
        plan_prompt = f"""
        You are a travel planning expert. Create a comprehensive travel plan based on the following information:
        
        Destination: {destination}
        Check-in: {check_in}
        Check-out: {check_out}
        Budget: {budget} (approximately {budget_amount} {preferred_currency})
        Guests: {guests}
        Car Rental Needed: {car_needed}
        Preferred Currency: {preferred_currency}
        
        Hotel Recommendations:
        {hotel_response}
        
        Car Rental Options:
        {car_response if car_response else "No car rental requested"}
        
        Currency Information:
        {currency_response}
        
        Please create a detailed travel itinerary that includes:
        1. Summary of the trip
        2. Top hotel recommendations with prices and features
        3. Car rental options and recommendations (if requested)
        4. Currency exchange information and budget breakdown
        5. Estimated total cost breakdown (in both {preferred_currency} and USD)
        6. Travel tips and recommendations
        7. Day-by-day itinerary suggestions
        
        Format the response clearly with sections, bullet points, and markdown formatting.
        """
        
        try:
            response = self.llm.invoke(plan_prompt)
            print(f"Plan response ADK: {response.content}")
            return hotel_response, car_response, currency_response, status
        except Exception as e:
            return f"Error creating travel plan: {e}", "", "", status

def display_options(title, options_json, option_type="hotel"):
    st.subheader(title)
    
    # If the response is already a string (plain text), display it directly
    if isinstance(options_json, str):
        # Check if it's a JSON string
        try:
            options = json.loads(options_json)
            # If it's a list of dictionaries, process them
            if isinstance(options, list):
                for opt in options:
                    if isinstance(opt, dict):
                        name = opt.get("name") or opt.get("company") or "Option"
                        desc = opt.get("description", "")
                        link = opt.get("link", "")
                        cost = opt.get("estimated_cost_usd", "N/A")
                        st.markdown(f"**{name}**")
                        if link:
                            st.markdown(f"[View Details]({link})")
                        st.write(desc)
                        st.write(f"Estimated Cost: {cost}")
                        st.markdown('---')
                    else:
                        st.write(opt)
            # If it's a dictionary, display it
            elif isinstance(options, dict):
                name = options.get("name") or options.get("company") or "Option"
                desc = options.get("description", "")
                link = options.get("link", "")
                cost = options.get("estimated_cost_usd", "N/A")
                st.markdown(f"**{name}**")
                if link:
                    st.markdown(f"[View Details]({link})")
                st.write(desc)
                st.write(f"Estimated Cost: {cost}")
            else:
                st.write(options)
        except json.JSONDecodeError:
            # If it's not JSON, display as plain text
            st.write(options_json)
    else:
        # If it's already a Python object (dict/list), process it
        try:
            if isinstance(options_json, list):
                for opt in options_json:
                    if isinstance(opt, dict):
                        name = opt.get("name") or opt.get("company") or "Option"
                        desc = opt.get("description", "")
                        link = opt.get("link", "")
                        cost = opt.get("estimated_cost_usd", "N/A")
                        st.markdown(f"**{name}**")
                        if link:
                            st.markdown(f"[View Details]({link})")
                        st.write(desc)
                        st.write(f"Estimated Cost: {cost}")
                        st.markdown('---')
                    else:
                        st.write(opt)
            elif isinstance(options_json, dict):
                name = options_json.get("name") or options_json.get("company") or "Option"
                desc = options_json.get("description", "")
                link = options_json.get("link", "")
                cost = options_json.get("estimated_cost_usd", "N/A")
                st.markdown(f"**{name}**")
                if link:
                    st.markdown(f"[View Details]({link})")
                st.write(desc)
                st.write(f"Estimated Cost: {cost}")
            else:
                st.write(options_json)
        except Exception as e:
            st.write(f"Error displaying options: {e}")
            st.write(options_json)

def extract_car_options(car_response):
    # If already a list, return as is
    if isinstance(car_response, list):
        return car_response
    # If the results is a non-empty list, return it
    if isinstance(car_response, dict) and "results" in car_response and isinstance(car_response["results"], list) and car_response["results"]:
        return car_response["results"]
    # Try to extract dicts from the message string
    if isinstance(car_response, dict) and "message" in car_response:
        msg = car_response["message"]
        # Find all JSON-like dicts in the message
        dicts = re.findall(r'\{[^\}]+\}', msg)
        options = []
        for d in dicts:
            try:
                # Add missing quotes for keys if needed (optional, for robustness)
                d_fixed = re.sub(r'([,{])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', d)
                options.append(json.loads(d_fixed))
            except Exception:
                pass
        return options
    return []

def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Multi-Agent Travel Planner",
        page_icon="✈️",
        layout="wide"
    )
    
    st.title("✈️ Multi-Agent Travel Planning System")
    st.markdown("---")
    
    # Initialize the travel planner
    try:
        planner = TravelPlannerApp()
        st.success("✅ Travel planner initialized successfully!")
    except Exception as e:
        st.error(f"❌ Failed to initialize travel planner: {e}")
        st.stop()
    
    # Sidebar for agent status
    with st.sidebar:
        st.header("🤖 Agent Status")
        status = planner.check_agent_status()
        for agent, status_text in status.items():
            st.write(f"{agent.replace('_', ' ').title()}: {status_text}")
        
        st.markdown("---")
        st.header("ℹ️ About")
        st.markdown("""
        This app uses a multi-agent system:
        - **Hotel Booking Agent** (CrewAI + OpenAI)
        - **Car Rental Agent** (LangGraph + OpenAI)  
        - **Currency Agent** (LangGraph + OpenAI)
        - **Travel Planner** (Coordinates all agents)
        """)
    
    # Main form
    st.header("📋 Plan Your Trip")
    
    with st.form("travel_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            destination = st.text_input("Destination", placeholder="e.g., Paris, Tokyo, New York")
            budget = st.selectbox("Budget Range", ["budget", "mid-range", "luxury", "any"])
            guests = st.number_input("Number of Guests", min_value=1, max_value=10, value=2)
        
        with col2:
            check_in = st.date_input("Check-in Date", min_value=datetime.now().date())
            check_out = st.date_input("Check-out Date", min_value=check_in + timedelta(days=1))
            car_needed = st.checkbox("Need Car Rental", value=True)
        
        # Currency preferences
        st.subheader("💰 Currency Preferences")
        col3, col4 = st.columns(2)
        with col3:
            preferred_currency = st.selectbox(
                "Preferred Currency", 
                ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"],
                index=0
            )
        with col4:
            budget_amount = st.number_input(
                f"Budget Amount ({preferred_currency})",
                min_value=0,
                value=1000,
                step=100
            )
        
        # Additional preferences
        st.subheader("Additional Preferences")
        preferences = st.text_area(
            "Special Requirements or Preferences",
            placeholder="e.g., Near city center, family-friendly, accessible rooms, etc.",
            height=100
        )
        
        submitted = st.form_submit_button("🚀 Plan My Trip", type="primary")
    
    # Process the form
    if submitted:
        if not destination:
            st.error("Please enter a destination")
            return
        
        if check_out <= check_in:
            st.error("Check-out date must be after check-in date")
            return
        
        with st.spinner("🤖 Coordinating with travel agents..."):
            hotel_response, car_response, currency_response, agent_status = planner.plan_trip(
                destination=destination,
                check_in=check_in.strftime("%Y-%m-%d"),
                check_out=check_out.strftime("%Y-%m-%d"),
                budget=budget,
                guests=guests,
                car_needed=car_needed,
                preferred_currency=preferred_currency,
                budget_amount=budget_amount
            )
            # Generate the LLM plan summary
            plan_prompt = f"""
            You are a travel planning expert. Create a comprehensive travel plan based on the following information:
            Destination: {destination}
            Check-in: {check_in}
            Check-out: {check_out}
            Budget: {budget}
            Guests: {guests}
            Car Rental Needed: {car_needed}
            Hotel Recommendations:
            {hotel_response}
            Car Rental Options:
            {car_response if car_needed else 'No car rental requested'}
            Please create a detailed travel itinerary that includes:
            1. Summary of the trip
            2. Top hotel recommendations with prices and features
            3. Car rental options and recommendations (if requested)
            4. Estimated total cost breakdown
            5. Travel tips and recommendations
            6. Day-by-day itinerary suggestions
            Format the response clearly with sections, bullet points, and markdown formatting.
            """
            try:
                plan = planner.llm.invoke(plan_prompt).content
            except Exception as e:
                plan = f"Error creating travel plan: {e}"

        st.success("✅ Travel plan generated successfully!")
        st.subheader("🤖 Agent Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"Hotel Agent: {agent_status['hotel']}")
        with col2:
            st.write(f"Car Rental Agent: {agent_status['car_rental']}")
        with col3:
            st.write(f"Currency Agent: {agent_status['currency']}")
        st.subheader("📋 Your Travel Plan")
        st.markdown("---")
        display_options("🏨 Hotel Recommendations", hotel_response, option_type="hotel")
        if car_needed:
            car_options = extract_car_options(car_response)
            display_options("🚗 Car Rental Options", car_options, option_type="car")
        if currency_response:
            st.subheader("💰 Currency Information")
            st.write(currency_response)
            st.markdown("---")
        st.subheader("📝 AI-Generated Travel Plan Summary")
        st.markdown(plan)
        st.download_button(
            label="📥 Download Travel Plan",
            data=f"Hotel Recommendations:\n{hotel_response}\n\nCar Rental Options:\n{car_response}\n\nAI-Generated Plan:\n{plan}",
            file_name=f"travel_plan_{destination}_{check_in.strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )

if __name__ == "__main__":
    main()