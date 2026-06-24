#!/usr/bin/env python3
"""
Standalone Streamlit Travel Planning App (RoamAI)
Features a modern production-like UI, real-time agent coordination logging, and beautiful tabs.
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
    """Travel planner app engine coordinating specialist sub-agents."""
    
    def __init__(self):
        """Initialize the travel planner app and connections."""
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            st.error("OPENROUTER_API_KEY not found in environment variables")
            st.stop()
        
        # Use the correct OpenRouter API base (the .ai domain).
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
        """Check status of sub-agents."""
        agents_status = {}
        
        # Check hotel agent
        try:
            response = requests.get(f"{self.hotel_agent_url}/health", timeout=5)
            if response.status_code == 200:
                agents_status["hotel"] = "🟢 Active"
            else:
                agents_status["hotel"] = "🔴 Error"
        except:
            agents_status["hotel"] = "⚪ Offline"
        
        # Check car rental agent
        try:
            response = requests.get(f"{self.car_rental_agent_url}/health", timeout=5)
            if response.status_code == 200:
                agents_status["car_rental"] = "🟢 Active"
            else:
                agents_status["car_rental"] = "🔴 Error"
        except:
            agents_status["car_rental"] = "⚪ Offline"
        
        # Check currency agent
        try:
            response = requests.get(f"{self.currency_agent_url}/health", timeout=5)
            if response.status_code == 200:
                agents_status["currency"] = "🟢 Active"
            else:
                agents_status["currency"] = "🔴 Error"
        except:
            agents_status["currency"] = "⚪ Offline"
        
        return agents_status
    
    def ask_hotel_agent(self, query):
        """Ask the hotel booking agent for recommendations."""
        try:
            payload = {"message": query}
            response = requests.post(
                f"{self.hotel_agent_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            
            if response.status_code == 200:
                response_data = response.json()
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
                timeout=90
            )
            
            if response.status_code == 200:
                response_data = response.json()
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
                timeout=45
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data.get("response", "No response from currency agent")
            else:
                return f"Currency agent error: {response.status_code}"
        except Exception as e:
            return f"Error communicating with currency agent: {e}"

def render_agent_badge(name, status_text):
    """Render a styled badge representing agent status."""
    if "🟢" in status_text or "Active" in status_text:
        color = "#10B981"  # Emerald green
        bg = "rgba(16, 185, 129, 0.08)"
        dot_style = "animation: pulse 2s infinite;"
    elif "🔴" in status_text or "Error" in status_text:
        color = "#EF4444"  # Rose red
        bg = "rgba(239, 68, 68, 0.08)"
        dot_style = ""
    else:
        color = "#9CA3AF"  # Slate gray
        bg = "rgba(156, 163, 175, 0.08)"
        dot_style = ""
        
    st.markdown(f"""
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.65rem 0.85rem;
            border-radius: 10px;
            background: {bg};
            border: 1px solid {color}30;
            margin-bottom: 0.6rem;
        ">
            <span style="font-weight: 500; font-size: 0.9rem; color: inherit;">{name}</span>
            <span style="
                color: {color};
                font-size: 0.8rem;
                font-weight: 700;
                display: flex;
                align-items: center;
                gap: 5px;
            ">
                <span style="{dot_style}">●</span> {status_text.replace('🟢', '').replace('🔴', '').replace('⚪', '').strip()}
            </span>
        </div>
    """, unsafe_allow_html=True)

def render_hotel_card(hotel):
    """Render an HTML card for a hotel suggestion."""
    name = hotel.get("name", "Hotel Option")
    desc = hotel.get("description", "No description available.")
    link = hotel.get("link", "#")
    cost = hotel.get("estimated_cost_usd", "N/A")
    
    return f"""
    <div class="card-container">
        <div class="card-header-row">
            <h4 class="card-title">🏨 {name}</h4>
            <span class="card-badge">{cost}</span>
        </div>
        <p class="card-desc">{desc}</p>
        <div class="card-footer-row">
            <a href="{link}" target="_blank" class="card-btn">View Details &rarr;</a>
        </div>
    </div>
    """

def render_car_card(car):
    """Render an HTML card for a car rental suggestion."""
    company = car.get("company") or car.get("name") or "Car Rental"
    desc = car.get("description") or car.get("details") or "No details available."
    cost = car.get("estimated_cost_usd") or car.get("price") or "N/A"
    link = car.get("link", "#")
    
    btn_html = f'<a href="{link}" target="_blank" class="card-btn">Book Now &rarr;</a>' if link != "#" else ''
    
    return f"""
    <div class="card-container">
        <div class="card-header-row">
            <h4 class="card-title">🚗 {company}</h4>
            <span class="card-badge">{cost}</span>
        </div>
        <p class="card-desc">{desc}</p>
        <div class="card-footer-row">
            {btn_html}
        </div>
    </div>
    """

def parse_hotel_response(hotel_response):
    """Parse hotel recommendations from agent response."""
    if not hotel_response:
        return None
    if isinstance(hotel_response, list):
        return hotel_response
    if isinstance(hotel_response, str):
        cleaned = hotel_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except Exception:
            pass
            
        try:
            start_idx = cleaned.find('[')
            end_idx = cleaned.rfind(']')
            if start_idx != -1 and end_idx != -1:
                return json.loads(cleaned[start_idx:end_idx+1])
        except Exception:
            pass
            
        try:
            dicts = re.findall(r'\{[^\}]+\}', cleaned)
            options = []
            for d in dicts:
                try:
                    d_fixed = re.sub(r'([,{])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', d)
                    options.append(json.loads(d_fixed))
                except Exception:
                    pass
            if options:
                return options
        except Exception:
            pass
    return None

def extract_car_options(car_response):
    """Extract list of car rental dictionaries."""
    if not car_response:
        return []
    if isinstance(car_response, list):
        return car_response
    if isinstance(car_response, dict) and "results" in car_response and isinstance(car_response["results"], list):
        return car_response["results"]
    if isinstance(car_response, dict) and "message" in car_response:
        msg = car_response["message"]
        dicts = re.findall(r'\{[^\}]+\}', msg)
        options = []
        for d in dicts:
            try:
                d_fixed = re.sub(r'([,{])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', d)
                options.append(json.loads(d_fixed))
            except Exception:
                pass
        return options
    if isinstance(car_response, str):
        # Try JSON parsing
        try:
            parsed = json.loads(car_response)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "results" in parsed:
                return parsed["results"]
        except Exception:
            pass
        # Try regex extract
        dicts = re.findall(r'\{[^\}]+\}', car_response)
        options = []
        for d in dicts:
            try:
                d_fixed = re.sub(r'([,{])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', d)
                options.append(json.loads(d_fixed))
            except Exception:
                pass
        return options
    return []

def render_itinerary(plan_text):
    """Parse day-by-day sections of the itinerary and render expanders."""
    if not plan_text:
        st.info("No itinerary content available.")
        return
        
    pattern = r'(?m)(^(?:##|###)?\s*\*?\*?Day\s+\d+[:\-\*]*.*$)'
    parts = re.split(pattern, plan_text)
    
    if len(parts) <= 1:
        st.markdown(plan_text)
        return
        
    if parts[0].strip():
        st.markdown(parts[0].strip())
        
    for i in range(1, len(parts), 2):
        header = parts[i].strip("#*-\n: ")
        content = parts[i+1].strip() if i+1 < len(parts) else ""
        with st.expander(f"📅 {header}", expanded=(i==1)):
            st.markdown(content)

def main():
    """Main Streamlit app entry point."""
    st.set_page_config(
        page_title="RoamAI - Autonomous Travel Concierge",
        page_icon="✈️",
        layout="wide"
    )
    
    # Custom CSS Injector for modern look
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
        
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
            font-family: 'Outfit', sans-serif !important;
        }
        
        div[data-testid="stToolbar"] {
            visibility: hidden;
            height: 0%;
            position: absolute;
        }
        
        .main-title-container {
            text-align: center;
            padding: 2.2rem 1.5rem;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.06) 0%, rgba(139, 92, 246, 0.06) 50%, rgba(236, 72, 153, 0.06) 100%);
            border-radius: 20px;
            margin-bottom: 2rem;
            border: 1px solid rgba(139, 92, 246, 0.12);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
        }
        
        .gradient-text {
            background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #EC4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 2.6rem;
            margin: 0;
            letter-spacing: -0.04em;
        }
        
        .subtitle-text {
            color: #8B949E;
            font-size: 1.05rem;
            margin: 0.4rem 0 0 0;
            font-weight: 400;
        }
        
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
            border-radius: 10px !important;
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
            transition: all 0.2s ease-in-out;
        }
        
        .stForm {
            background: rgba(128, 128, 128, 0.03) !important;
            border: 1px solid rgba(128, 128, 128, 0.08) !important;
            border-radius: 16px !important;
            padding: 1.8rem !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.02) !important;
        }
        
        button[kind="primaryFormSubmit"], button[kind="primary"] {
            background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%) !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 10px !important;
            border: none !important;
            padding: 0.55rem 2.2rem !important;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
            transition: all 0.2s ease !important;
            width: auto !important;
        }
        
        button[kind="primaryFormSubmit"]:hover, button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(99, 102, 241, 0.4) !important;
            opacity: 0.95;
        }
        
        .sidebar-info-card {
            background: rgba(128, 128, 128, 0.04);
            border-radius: 12px;
            padding: 1.1rem;
            border: 1px solid rgba(128, 128, 128, 0.08);
            margin-top: 1rem;
        }
        
        .sidebar-info-title {
            font-weight: 600;
            margin-bottom: 0.5rem;
            font-size: 0.95rem;
            color: inherit;
        }
        
        .sidebar-info-item {
            font-size: 0.8rem;
            color: #8B949E;
            margin-bottom: 0.5rem;
            line-height: 1.4;
        }
        
        .card-container {
            background: rgba(128, 128, 128, 0.04);
            border-radius: 14px;
            border: 1px solid rgba(128, 128, 128, 0.08);
            padding: 1.25rem;
            margin-bottom: 1.1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 230px;
            transition: all 0.2s ease;
        }
        
        .card-container:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(139, 92, 246, 0.06);
            border-color: rgba(139, 92, 246, 0.25);
            background: rgba(128, 128, 128, 0.06);
        }
        
        .card-header-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
            margin-bottom: 0.6rem;
        }
        
        .card-title {
            margin: 0 !important;
            font-size: 1.05rem !important;
            font-weight: 700 !important;
            line-height: 1.3 !important;
            color: inherit !important;
        }
        
        .card-badge {
            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
            color: white;
            padding: 0.25rem 0.65rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 700;
            white-space: nowrap;
        }
        
        .card-desc {
            font-size: 0.85rem;
            color: #8B949E;
            margin-bottom: 0.8rem;
            line-height: 1.45;
            flex-grow: 1;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .card-footer-row {
            display: flex;
            justify-content: flex-start;
            align-items: center;
        }
        
        .card-btn {
            text-decoration: none !important;
            background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
            color: white !important;
            padding: 0.4rem 1.1rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            text-align: center;
            box-shadow: 0 3px 8px rgba(99, 102, 241, 0.15);
            transition: all 0.2s ease;
        }
        
        .card-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 12px rgba(99, 102, 241, 0.25);
            opacity: 0.95;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-weight: 700 !important;
        }
        
        div[data-testid="stTabBar"] button {
            font-size: 1rem !important;
            font-weight: 600 !important;
            padding: 0.4rem 0.8rem !important;
        }
        
        div[data-testid="stTabBar"] button[aria-selected="true"] {
            color: #8B5CF6 !important;
            border-bottom-color: #8B5CF6 !important;
        }
        
        @keyframes pulse {
            0% { opacity: 0.3; }
            50% { opacity: 1; }
            100% { opacity: 0.3; }
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Custom Gradient Branding Header
    st.markdown("""
        <div class="main-title-container">
            <h1 class="gradient-text">✈️ RoamAI</h1>
            <p class="subtitle-text">Autonomous Multi-Agent Travel Planner & Concierge</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize Travel Planner
    try:
        planner = TravelPlannerApp()
    except Exception as e:
        st.error(f"❌ Failed to initialize travel planner engine: {e}")
        st.stop()
        
    # Sidebar: System monitor and configurations
    with st.sidebar:
        st.markdown("<div style='text-align: center; padding-bottom: 1.2rem;'><img src='https://cdn-icons-png.flaticon.com/512/826/826070.png' width='60'></div>", unsafe_allow_html=True)
        st.markdown("### 🤖 Agent Network Status")
        st.markdown("Real-time telemetry of autonomous travel specialists:")
        
        status = planner.check_agent_status()
        for agent, status_text in status.items():
            name = agent.replace('_', ' ').title()
            render_agent_badge(name, status_text)
            
        st.markdown("""
            <div class="sidebar-info-card">
                <div class="sidebar-info-title">ℹ️ RoamAI Architecture</div>
                <div class="sidebar-info-item"><b>Hotel Booking Agent</b><br/>CrewAI + GPT-4o-mini</div>
                <div class="sidebar-info-item"><b>Car Rental Agent</b><br/>LangGraph + GPT-4o-mini</div>
                <div class="sidebar-info-item"><b>Currency Agent</b><br/>LangGraph + Frankfurter API</div>
                <div class="sidebar-info-item"><b>RoamAI Orchestrator</b><br/>LangChain Coordinator Core</div>
            </div>
        """, unsafe_allow_html=True)
        
    # Main Form
    st.markdown("### 📋 Create Travel Request")
    with st.form("travel_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            destination = st.text_input("Destination City / Country", placeholder="e.g. Paris, Tokyo, Maui")
            budget = st.selectbox("Budget Category", ["budget", "mid-range", "luxury", "any"])
            guests = st.number_input("Guests Count", min_value=1, max_value=10, value=2)
            
        with col2:
            check_in = st.date_input("Arrival Date", min_value=datetime.now().date())
            check_out = st.date_input("Departure Date", min_value=check_in + timedelta(days=1))
            car_needed = st.checkbox("Require Rental Car", value=True)
            
        # Currency preferences
        st.markdown("#### 💰 Currency Settings")
        col3, col4 = st.columns(2)
        with col3:
            preferred_currency = st.selectbox(
                "FX Display Currency",
                ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"],
                index=0
            )
        with col4:
            budget_amount = st.number_input(
                f"Maximum Budget ({preferred_currency})",
                min_value=0,
                value=1000,
                step=100
            )
            
        # Additional preferences
        st.markdown("#### ✨ Personal Requests")
        preferences = st.text_area(
            "Special Requirements / Custom Directives",
            placeholder="e.g. Vegetarian cuisine nearby, quiet rooms, close to historical monuments...",
            height=100
        )
        
        submitted = st.form_submit_button("🚀 Plan My Trip", type="primary")
        
    # Coordination and generation process
    if submitted:
        if not destination:
            st.error("Please specify a target destination.")
            return
            
        if check_out <= check_in:
            st.error("Departure date must be after arrival date.")
            return
            
        # Real-time orchestration log
        status_placeholder = st.empty()
        with status_placeholder.container():
            with st.status("🕵️ RoamAI Coordinator organizing specialist agents...", expanded=True) as status_box:
                
                status_box.write("🔄 Synchronizing communication link to multi-agent network...")
                agent_status = planner.check_agent_status()
                
                status_box.write("💰 Converting budget limits & FX indexes via **Currency Agent (LangGraph)**...")
                currency_response = ""
                if preferred_currency != "USD":
                    currency_query = f"Convert {budget_amount} {preferred_currency} to USD for travel budget planning. Also provide current exchange rates for {preferred_currency} to major currencies (USD, EUR, GBP)."
                    currency_response = planner.ask_currency_agent(currency_query)
                else:
                    currency_query = f"Provide current exchange rates from USD to local currency for {destination}. Also show rates to EUR and GBP for reference."
                    currency_response = planner.ask_currency_agent(currency_query)
                status_box.write("✅ Exchange indexes and budget bounds set.")
                
                status_box.write("🏨 Querying accommodations matched to budget via **Hotel Agent (CrewAI)**...")
                hotel_query = f"Find top 10 budget-friendly hotels in {destination} for {guests} guests from {check_in} to {check_out}"
                if budget != "any":
                    hotel_query += f" with {budget} budget (approximately {budget_amount} {preferred_currency})"
                if preferences:
                    hotel_query += f". Special preferences: {preferences}"
                hotel_response = planner.ask_hotel_agent(hotel_query)
                status_box.write("✅ Accommodation options cataloged.")
                
                car_response = ""
                if car_needed:
                    status_box.write("🚗 Sourcing car rental parameters via **Car Rental Agent (LangGraph)**...")
                    car_query = f"Find car rental options in {destination} from {check_in} to {check_out}"
                    if preferences:
                        car_query += f". User requirements: {preferences}"
                    car_response = planner.ask_car_rental_agent(car_query)
                    status_box.write("✅ Car rental catalogue completed.")
                else:
                    status_box.write("ℹ️ Car rental omitted per user configuration.")
                    
                status_box.write("✍️ Synthesizing personal master travel plan & itinerary...")
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
                    plan = planner.llm.invoke(plan_prompt).content
                except Exception as e:
                    plan = f"Error creating travel plan: {e}"
                    
                status_box.update(label="✨ Master travel plan successfully generated!", state="complete", expanded=False)
                
        # Tabbed visual panels
        st.markdown("### 🗺️ Your Personalized RoamAI Itinerary")
        tab_itinerary, tab_hotels, tab_cars, tab_budget = st.tabs([
            "🗺️ Personal Itinerary", 
            "🏨 Hotel Options", 
            "🚗 Car Rentals", 
            "💰 Rates & FX"
        ])
        
        with tab_itinerary:
            render_itinerary(plan)
            
        with tab_hotels:
            hotels = parse_hotel_response(hotel_response)
            if hotels:
                st.markdown("#### 🏨 Curated Accommodations")
                cols = st.columns(2)
                for idx, hotel in enumerate(hotels):
                    col = cols[idx % 2]
                    with col:
                        st.markdown(render_hotel_card(hotel), unsafe_allow_html=True)
            else:
                st.markdown("#### 🏨 Accommodation Output")
                st.markdown(hotel_response)
                
        with tab_cars:
            if car_needed:
                car_options = extract_car_options(car_response)
                if car_options:
                    st.markdown("#### 🚗 Sourced Rental Cars")
                    cols = st.columns(2)
                    for idx, car in enumerate(car_options):
                        col = cols[idx % 2]
                        with col:
                            st.markdown(render_car_card(car), unsafe_allow_html=True)
                else:
                    st.markdown("#### 🚗 Rental Options Output")
                    st.markdown(car_response if car_response else "No car rental offers returned from agent.")
            else:
                st.info("Car rental service was not selected in configurations.")
                
        with tab_budget:
            st.markdown("#### 💰 Budget Conversions & FX rates")
            st.markdown(currency_response if currency_response else "No currency rates obtained.")
            
        # Download option
        st.markdown("---")
        st.download_button(
            label="📥 Download Markdown Travel Plan",
            data=f"# RoamAI Master Travel Plan: {destination}\n\n## Summary & Itinerary\n{plan}\n\n## Accommodation Matches\n{hotel_response}\n\n## Car Rental Matches\n{car_response if car_needed else 'N/A'}",
            file_name=f"roamai_plan_{destination.replace(' ', '_').lower()}.md",
            mime="text/markdown"
        )

if __name__ == "__main__":
    main()