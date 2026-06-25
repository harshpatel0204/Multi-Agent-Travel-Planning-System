#!/usr/bin/env python3
"""
RoamAI – Conversational AI Travel Planning App
AI asks travel questions one-by-one with real-time streaming (like ChatGPT),
then auto-generates a full travel plan and exports it as a downloadable PDF.
"""

import streamlit as st
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import re

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# Conversational Q&A Flow — 8 Question Slots
# ══════════════════════════════════════════════════════════════════════════════

QUESTION_KEYS = [
    "destination",      # Q0
    "check_in",         # Q1
    "check_out",        # Q2
    "guests",           # Q3
    "budget_category",  # Q4
    "budget_amount",    # Q5
    "car_needed",       # Q6
    "preferences",      # Q7
]


def build_question_prompt(idx: int, answers: dict) -> str:
    """Return the LLM prompt that generates question #idx in context."""
    dest       = answers.get("destination", "their destination")
    check_in   = answers.get("check_in", "")
    check_out  = answers.get("check_out", "")
    guests     = answers.get("guests", "")
    budget_cat = answers.get("budget_category", "")

    prompts = [
        # Q0 – destination
        """You are RoamAI, a warm and enthusiastic AI travel concierge.
Greet the user cheerfully, introduce yourself as RoamAI, and ask them:
where would they like to travel?
Be inviting, exciting, and encouraging. Maximum 3 sentences.""",

        # Q1 – check-in
        f"""You are RoamAI, an enthusiastic AI travel concierge.
The user wants to travel to {dest} — fantastic choice!
Acknowledge their destination with genuine excitement or share a quick fun fact about it (1 sentence).
Then ask: what is their planned arrival / check-in date?
Prompt them to include the month, day, and year. Maximum 2 sentences.""",

        # Q2 – check-out
        f"""You are RoamAI, an enthusiastic AI travel concierge.
The user is traveling to {dest}, arriving on {check_in}.
Briefly acknowledge the check-in date (half a sentence), then ask:
what is their planned departure / check-out date?
Maximum 2 sentences.""",

        # Q3 – guests
        f"""You are RoamAI, an enthusiastic AI travel concierge.
Trip: {dest}, {check_in} → {check_out}. 
Ask how many guests (including themselves) will be traveling.
Keep it short and friendly. Maximum 1–2 sentences.""",

        # Q4 – budget category
        f"""You are RoamAI, an enthusiastic AI travel concierge.
{guests} guest(s) are heading to {dest}!
Ask about their preferred budget level and present exactly these three options:
🟢 Budget (smart savings)  |  🟡 Mid-range (balanced comfort)  |  👑 Luxury (premium experience)
Be encouraging that every budget makes for an amazing adventure. Maximum 2 sentences.""",

        # Q5 – budget amount + currency
        f"""You are RoamAI, an enthusiastic AI travel concierge.
{budget_cat.title() if budget_cat else "Great"} choice! Planning a {budget_cat or ""} trip to {dest} for {guests} guest(s).
Ask: what is their maximum total trip budget, and in which currency would they like prices displayed?
Give a clear example such as: "2000 USD" or "1500 EUR" or "120000 JPY".
Maximum 2 sentences.""",

        # Q6 – car rental
        f"""You are RoamAI, an enthusiastic AI travel concierge.
Almost there — planning a wonderful {budget_cat or ""} trip to {dest}!
Ask: will they need a car rental at the destination?
Simple yes or no. Maximum 1 sentence.""",

        # Q7 – preferences (final question)
        f"""You are RoamAI, an enthusiastic AI travel concierge.
This is the FINAL question before generating the complete travel plan for {dest}!
Tell them you're almost done and one last thing to ask.
Ask if they have any special preferences or requirements —
for example: dietary needs, must-see attractions, accessibility requirements, preferred accommodation type, activity style, etc.
Mention they can say "none" if they have no special requests.
Maximum 3 sentences.""",
    ]
    return prompts[idx]


def build_closing_prompt(answers: dict) -> str:
    """Prompt for the AI's closing message after all questions are answered."""
    dest = answers.get("destination", "your destination")
    return (
        f"You are RoamAI, an enthusiastic AI travel concierge. "
        f"The user has just provided all the information needed for their amazing trip to {dest}! "
        f"Acknowledge their final answer warmly (1 sentence). "
        f"Then announce with excitement that you are NOW generating their complete, personalized travel plan — "
        f"it will include hotel recommendations, a full itinerary, car rental options, budget breakdown, and travel tips. "
        f"Tell them to sit back while the AI agents get to work! "
        f"End with an upbeat emoji. Maximum 3 sentences."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TravelPlannerApp — LLM + Agent Coordinator
# ══════════════════════════════════════════════════════════════════════════════

class TravelPlannerApp:
    """Coordinates LLM and specialist sub-agents for travel planning."""

    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            st.error("❌ OPENROUTER_API_KEY not found. Please check your .env file.")
            st.stop()

        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            model="openai/gpt-4o-mini",
            streaming=True,
        )
        self.hotel_url    = "http://localhost:10002"
        self.car_url      = "http://localhost:10003"
        self.currency_url = "http://localhost:10004"

    # ── Streaming ─────────────────────────────────────────────────────────────

    def stream_llm(self, prompt: str):
        """Yield text chunks for use with st.write_stream() — real-time streaming."""
        try:
            for chunk in self.llm.stream(prompt):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            yield f"\n\n⚠️ Streaming error: {e}"

    def invoke_llm(self, prompt: str) -> str:
        """Invoke LLM synchronously and return full response."""
        try:
            return self.llm.invoke(prompt).content
        except Exception as e:
            return f"❌ LLM error: {e}"

    # ── Agent Health ──────────────────────────────────────────────────────────

    def check_status(self) -> dict:
        status = {}
        for name, url in [
            ("hotel",      self.hotel_url),
            ("car_rental", self.car_url),
            ("currency",   self.currency_url),
        ]:
            try:
                r = requests.get(f"{url}/health", timeout=5)
                status[name] = "🟢 Active" if r.status_code == 200 else "🔴 Error"
            except Exception:
                status[name] = "⚪ Offline"
        return status

    # ── Agent Queries ─────────────────────────────────────────────────────────

    def ask_agent(self, url: str, query: str, timeout: int = 120) -> str:
        try:
            r = requests.post(
                f"{url}/chat",
                json={"message": query},
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            return r.json().get("response", "") if r.status_code == 200 else f"Agent error {r.status_code}"
        except Exception as e:
            return f"Agent unavailable: {e}"

    # ── Plan Generation ───────────────────────────────────────────────────────

    def generate_plan(
        self, answers: dict,
        hotel_resp: str, car_resp: str, currency_resp: str
    ) -> str:
        dest      = answers.get("destination", "")
        check_in  = answers.get("check_in", "")
        check_out = answers.get("check_out", "")
        guests    = answers.get("guests", "")
        budget    = f"{answers.get('budget_category', '')} ({answers.get('budget_amount', '')})"
        car       = answers.get("car_needed", "no")
        prefs     = answers.get("preferences", "none")

        prompt = f"""You are an expert travel planner. Create a comprehensive, detailed, personalized travel plan.

TRIP DETAILS:
- Destination: {dest}
- Dates: {check_in} to {check_out}
- Guests: {guests}
- Budget: {budget}
- Car Rental Needed: {car}
- Special Preferences: {prefs}

AGENT DATA:
Hotel Recommendations: {hotel_resp or "Use your knowledge to suggest top hotels"}
Car Rental Options: {car_resp or "Not requested or unavailable — suggest alternatives"}
Currency & Exchange: {currency_resp or "Use approximate current rates"}

Write the complete travel plan with these exact sections (use ## headers):

## 🌟 Trip Overview
A compelling 2–3 sentence summary of this trip.

## 🏨 Recommended Accommodations
Top 3–5 hotels with names, key features, location highlights, and estimated nightly cost.

## 🚗 Transportation & Car Rental
{"Car rental recommendations, estimated daily rates, and pick-up tips." if "yes" in car.lower() else "Best local transport options: public transit, taxis, rideshare apps, and estimated costs."}

## 💰 Budget Breakdown
Itemized estimates: accommodation, transport, food (per day), activities, misc. Show a total estimate.

## 💱 Currency & Money Tips
Current exchange rates, best payment methods, ATM tips, and money-saving advice for {dest}.

## 📅 Day-by-Day Itinerary
A detailed plan for every day of the trip. Use this format for each day:
**Day 1: [Theme or Date]**
Morning: ...
Afternoon: ...
Evening: ...
(continue for all days)

## ✈️ Essential Travel Tips
5–7 highly specific, practical tips for {dest} based on the user's preferences.

## 📋 Pre-Trip Checklist
Documents required, key bookings to make in advance, and packing essentials.

Be specific, detailed, and enthusiastic. Use clear markdown formatting."""

        return self.invoke_llm(prompt)


# ══════════════════════════════════════════════════════════════════════════════
# PDF Report Generator (requires fpdf2)
# ══════════════════════════════════════════════════════════════════════════════

def generate_pdf_report(
    answers: dict, plan: str,
    hotel_resp: str, car_resp: str, currency_resp: str
) -> bytes | None:
    """Generate a formatted PDF travel report. Returns bytes or None on failure."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    dest      = answers.get("destination", "Travel Plan")
    check_in  = answers.get("check_in", "")
    check_out = answers.get("check_out", "")
    guests    = answers.get("guests", "")
    budget_c  = answers.get("budget_category", "").title()
    budget_a  = answers.get("budget_amount", "")
    prefs     = answers.get("preferences", "")

    def strip_md(text: str) -> str:
        """Strip markdown syntax and problematic characters for clean PDF output."""
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        # Remove emoji / supplementary plane pictographics + variation selectors
        text = re.sub(
            r'[\U0001F000-\U0001FFFF\U00002600-\U000027FF\uFE00-\uFE0F]+',
            '', text
        )
        # Normalise common Unicode punctuation to ASCII equivalents
        text = text.replace('\u2022', '-')   # bullet -> dash
        text = text.replace('\u2013', '-')   # en-dash -> hyphen
        text = text.replace('\u2014', '--')  # em-dash -> double hyphen
        text = text.replace('\u2018', "'").replace('\u2019', "'")  # smart quotes
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2026', '...')  # ellipsis
        text = text.replace('\u00a0', ' ')   # non-breaking space
        return text.strip()

    # ── Resolve a Unicode-capable TTF font ────────────────────────────────────
    # Priority: Windows Arial > Linux DejaVu > macOS Arial
    FONT_CANDIDATES = [
        # (regular, bold, italic)
        ("C:/Windows/Fonts/arial.ttf",   "C:/Windows/Fonts/arialbd.ttf",  "C:/Windows/Fonts/ariali.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        ("/Library/Fonts/Arial.ttf",
         "/Library/Fonts/Arial Bold.ttf",
         "/Library/Fonts/Arial Italic.ttf"),
    ]

    FONT_NAME = None
    font_regular = font_bold = font_italic = None
    for reg, bold, ital in FONT_CANDIDATES:
        import os as _os
        if _os.path.exists(reg) and _os.path.exists(bold):
            font_regular, font_bold, font_italic = reg, bold, ital
            FONT_NAME = "UniFont"
            break

    class PDF(FPDF):
        """PDF subclass using a Unicode TTF font for full character support."""

        def header(self):
            if self.page_no() == 1:
                return
            self.set_font(FONT_NAME or "Helvetica", "B", 8)
            self.set_text_color(130, 130, 130)
            self.cell(
                0, 6, strip_md(f"RoamAI Travel Plan  |  {dest}"),
                align="L", new_x="LMARGIN", new_y="NEXT"
            )
            self.set_draw_color(200, 200, 210)
            self.line(15, self.get_y(), 195, self.get_y())
            self.ln(3)

        def footer(self):
            self.set_y(-15)
            self.set_font(FONT_NAME or "Helvetica", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(
                0, 10,
                f"Generated by RoamAI  |  Page {self.page_no()}",
                align="C"
            )

    pdf = PDF()
    # Register the Unicode font if found; otherwise fall back to built-in Helvetica
    if FONT_NAME and font_regular:
        pdf.add_font(FONT_NAME, style="",  fname=font_regular)
        pdf.add_font(FONT_NAME, style="B", fname=font_bold)
        if font_italic and __import__('os').path.exists(font_italic):
            pdf.add_font(FONT_NAME, style="I", fname=font_italic)
    else:
        FONT_NAME = "Helvetica"  # core font fallback (latin-1 only)
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.set_margins(15, 20, 15)

    # ── COVER PAGE ────────────────────────────────────────────────────────────
    pdf.add_page()

    # Hero gradient background (two layered rectangles)
    pdf.set_fill_color(82, 86, 210)
    pdf.rect(0, 0, 210, 115, "F")
    pdf.set_fill_color(110, 60, 200)
    pdf.rect(0, 55, 210, 60, "F")

    # Brand name
    pdf.set_y(22)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(FONT_NAME, "B", 46)
    pdf.cell(0, 22, "RoamAI", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(FONT_NAME, "", 14)
    pdf.set_text_color(205, 205, 255)
    pdf.cell(0, 8, "Your Personalized AI Travel Plan", align="C", new_x="LMARGIN", new_y="NEXT")

    # Destination hero text
    pdf.set_y(125)
    pdf.set_text_color(25, 25, 25)
    pdf.set_font(FONT_NAME, "B", 30)
    pdf.cell(0, 14, strip_md(dest), align="C", new_x="LMARGIN", new_y="NEXT")

    # Meta info
    pdf.ln(4)
    pdf.set_font(FONT_NAME, "", 12)
    pdf.set_text_color(80, 80, 90)
    pdf.cell(0, 8, f"Dates:  {check_in}  to  {check_out}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 8,
        f"Guests: {guests}   |   Budget: {budget_c} ({budget_a})",
        align="C", new_x="LMARGIN", new_y="NEXT"
    )
    if prefs and prefs.lower() not in ("none", "no", ""):
        pdf.set_font(FONT_NAME, "I", 10)
        pdf.set_text_color(110, 110, 120)
        pdf.cell(0, 7, f"Preferences: {strip_md(prefs[:80])}", align="C", new_x="LMARGIN", new_y="NEXT")

    # Divider
    pdf.ln(6)
    pdf.set_draw_color(180, 180, 200)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())

    # Generated timestamp
    pdf.ln(7)
    pdf.set_font(FONT_NAME, "", 9)
    pdf.set_text_color(140, 140, 150)
    pdf.cell(
        0, 6,
        f"Generated by RoamAI on {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        align="C"
    )

    # ── CONTENT PAGES ─────────────────────────────────────────────────────────
    pdf.add_page()

    def write_pdf_section(title: str, content: str):
        """Write a styled section header + body text."""
        # Section header with left accent bar
        pdf.set_fill_color(235, 235, 252)
        pdf.set_draw_color(120, 80, 220)
        pdf.set_line_width(0.6)
        pdf.set_font(FONT_NAME, "B", 12)
        pdf.set_text_color(75, 55, 170)
        pdf.cell(
            0, 9, f"  {strip_md(title)}",
            align="L", fill=True, border="L",
            new_x="LMARGIN", new_y="NEXT"
        )
        pdf.set_line_width(0.2)
        pdf.set_draw_color(200, 200, 200)
        pdf.ln(2)

        # Body text
        pdf.set_font(FONT_NAME, "", 10)
        pdf.set_text_color(35, 35, 40)

        for line in content.split('\n'):
            line = strip_md(line)
            if not line:
                pdf.ln(2)
                continue

            # Sub-headers: bold short lines ending with colon
            if (line.startswith("**") and line.endswith("**")) or (len(line) < 70 and line.endswith(":")):
                pdf.set_font(FONT_NAME, "B", 10)
                pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
                pdf.set_font(FONT_NAME, "", 10)
            # Bullet points — use ASCII dash (safe in all fonts)
            elif line.startswith("- ") or line.startswith("* "):
                pdf.set_x(22)
                pdf.multi_cell(0, 5.5, f"- {line[2:]}", new_x="LMARGIN", new_y="NEXT")
            # Numbered lists
            elif re.match(r'^\d+\.', line):
                pdf.set_x(22)
                pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)

    # Split plan by ## sections and write each
    section_regex = r'(##\s+[^\n]+)'
    parts = re.split(section_regex, plan)

    if len(parts) <= 1:
        # No sections found — write as a single block
        write_pdf_section("Travel Plan", plan)
    else:
        if parts[0].strip():
            write_pdf_section("Introduction", parts[0])
        for i in range(1, len(parts), 2):
            sec_title   = re.sub(r'^##\s*', '', parts[i]).strip()
            sec_content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            write_pdf_section(sec_title, sec_content)

    return bytes(pdf.output())


# ══════════════════════════════════════════════════════════════════════════════
# UI Rendering Helpers
# ══════════════════════════════════════════════════════════════════════════════

def render_agent_badge(name: str, status_text: str):
    if "🟢" in status_text or "Active" in status_text:
        color, bg = "#10B981", "rgba(16,185,129,0.08)"
        dot_style = "animation:pulse 2s infinite;"
    elif "🔴" in status_text or "Error" in status_text:
        color, bg, dot_style = "#EF4444", "rgba(239,68,68,0.08)", ""
    else:
        color, bg, dot_style = "#9CA3AF", "rgba(156,163,175,0.08)", ""

    clean = status_text.replace('🟢','').replace('🔴','').replace('⚪','').strip()
    st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:0.5rem 0.75rem;border-radius:10px;background:{bg};
                    border:1px solid {color}30;margin-bottom:0.5rem;">
            <span style="font-weight:500;font-size:0.87rem;">{name}</span>
            <span style="color:{color};font-size:0.77rem;font-weight:700;">
                <span style="{dot_style}">●</span>&nbsp;{clean}
            </span>
        </div>""", unsafe_allow_html=True)


def parse_hotel_response(hotel_response: str) -> list | None:
    if not hotel_response or not isinstance(hotel_response, str):
        return None
    cleaned = hotel_response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    for attempt in [
        lambda s: json.loads(s),
        lambda s: json.loads(s[s.find('['):s.rfind(']')+1]) if '[' in s else (_ for _ in ()).throw(ValueError()),
    ]:
        try:
            result = attempt(cleaned)
            if isinstance(result, list):
                return result
        except Exception:
            pass
    return None


def extract_car_options(car_response: str) -> list:
    if not car_response or not isinstance(car_response, str):
        return []
    try:
        parsed = json.loads(car_response)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "results" in parsed:
            return parsed["results"]
    except Exception:
        pass
    dicts = re.findall(r'\{[^\}]+\}', car_response)
    options = []
    for d in dicts:
        try:
            options.append(json.loads(re.sub(r'([,{])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', d)))
        except Exception:
            pass
    return options


def render_hotel_card(hotel: dict) -> str:
    name = hotel.get("name", "Hotel Option")
    desc = hotel.get("description", "No description available.")
    link = hotel.get("link", "#")
    cost = hotel.get("estimated_cost_usd", "N/A")
    return f"""<div class="card-container">
        <div class="card-header-row">
            <h4 class="card-title">🏨 {name}</h4>
            <span class="card-badge">{cost}</span>
        </div>
        <p class="card-desc">{desc}</p>
        <div class="card-footer-row">
            <a href="{link}" target="_blank" class="card-btn">View Details &rarr;</a>
        </div>
    </div>"""


def render_car_card(car: dict) -> str:
    company = car.get("company") or car.get("name") or "Car Rental"
    desc    = car.get("description") or car.get("details") or "No details available."
    cost    = car.get("estimated_cost_usd") or car.get("price") or "N/A"
    link    = car.get("link", "#")
    btn     = f'<a href="{link}" target="_blank" class="card-btn">Book Now &rarr;</a>' if link != "#" else ""
    return f"""<div class="card-container">
        <div class="card-header-row">
            <h4 class="card-title">🚗 {company}</h4>
            <span class="card-badge">{cost}</span>
        </div>
        <p class="card-desc">{desc}</p>
        <div class="card-footer-row">{btn}</div>
    </div>"""


def render_itinerary(plan_text: str):
    if not plan_text:
        st.info("No itinerary content available.")
        return
    pattern = r'(?m)(^(?:##|###)?\s*\*?\*?Day\s+\d+[:\-\*]*.*$)'
    parts   = re.split(pattern, plan_text)
    if len(parts) <= 1:
        st.markdown(plan_text)
        return
    if parts[0].strip():
        st.markdown(parts[0].strip())
    for i in range(1, len(parts), 2):
        header  = parts[i].strip("#*-\n: ")
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        with st.expander(f"📅 {header}", expanded=(i == 1)):
            st.markdown(content)


# ══════════════════════════════════════════════════════════════════════════════
# Session State Initializer
# ══════════════════════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "messages":       [],     # list of {role: "ai"|"user", content: str}
        "answers":        {},     # QUESTION_KEYS[idx] → user's answer string
        "q_idx":          0,      # index of the next question to ask (0–7)
        "chat_done":      False,  # True once all 8 answers collected
        "stream_pending": False,  # True while an AI message is queued to stream
        "pending_prompt": "",     # LLM prompt for the next streamed message
        "plan_data":      None,   # dict with generated plan + agent responses
        "generating":     False,  # True after chat_done, before plan_data ready
        "pdf_bytes":      None,   # cached PDF bytes once generated
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# Main App
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="RoamAI – AI Travel Concierge",
        page_icon="✈️",
        layout="wide",
    )
    init_state()

    # ── Global CSS ────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
    [data-testid="stSidebar"] {
        font-family: 'Outfit', sans-serif !important;
    }
    div[data-testid="stToolbar"] { visibility: hidden; height: 0; position: absolute; }

    /* ── Brand Header ── */
    .brand-header {
        text-align: center;
        padding: 2rem 1.5rem 1.5rem;
        background: linear-gradient(135deg,
            rgba(99,102,241,.07) 0%,
            rgba(139,92,246,.07) 50%,
            rgba(236,72,153,.07) 100%);
        border-radius: 20px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(139,92,246,.12);
        box-shadow: 0 4px 28px rgba(99,102,241,.05);
    }
    .gradient-text {
        background: linear-gradient(135deg, #6366F1, #8B5CF6, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.7rem;
        margin: 0; letter-spacing: -0.04em;
    }
    .subtitle-text {
        color: #8B949E; font-size: 1.02rem;
        margin: 0.4rem 0 0; font-weight: 400;
    }

    /* ── Progress Dots ── */
    .chat-progress {
        display: flex; gap: 8px; justify-content: center;
        align-items: center; margin-bottom: 0.5rem;
    }
    .progress-dot {
        width: 9px; height: 9px; border-radius: 50%;
        transition: all 0.35s ease;
    }
    .dot-done    { background: #8B5CF6; }
    .dot-active  { background: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,.28); animation: pop 1.1s ease infinite; }
    .dot-pending { background: rgba(128,128,128,.2); }
    @keyframes pop { 0%,100%{transform:scale(1)} 50%{transform:scale(1.3)} }

    /* ── Chat Message Styling ── */
    [data-testid="stChatMessage"] {
        border-radius: 14px !important;
        margin-bottom: 0.75rem !important;
        padding: 0.2rem 0.5rem !important;
        transition: all 0.2s ease;
    }
    /* AI / assistant messages */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: linear-gradient(135deg,
            rgba(99,102,241,.055),
            rgba(139,92,246,.055)) !important;
        border: 1px solid rgba(139,92,246,.15) !important;
    }
    /* User messages */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: rgba(128,128,128,.04) !important;
        border: 1px solid rgba(128,128,128,.1) !important;
    }

    /* ── Cards ── */
    .card-container {
        background: rgba(128,128,128,.04);
        border-radius: 14px; border: 1px solid rgba(128,128,128,.08);
        padding: 1.25rem; margin-bottom: 1.1rem;
        display: flex; flex-direction: column;
        height: 230px; transition: all .2s ease;
    }
    .card-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(139,92,246,.07);
        border-color: rgba(139,92,246,.25);
        background: rgba(128,128,128,.06);
    }
    .card-header-row {
        display: flex; justify-content: space-between;
        align-items: flex-start; gap: 8px; margin-bottom: .6rem;
    }
    .card-title  { margin:0!important; font-size:1.05rem!important; font-weight:700!important; }
    .card-badge  {
        background: linear-gradient(135deg,#10B981,#059669);
        color: #fff; padding: .25rem .65rem; border-radius: 20px;
        font-size: .8rem; font-weight: 700; white-space: nowrap;
    }
    .card-desc   {
        font-size: .85rem; color: #8B949E; flex-grow: 1; line-height: 1.45;
        display: -webkit-box; -webkit-line-clamp: 3;
        -webkit-box-orient: vertical; overflow: hidden;
    }
    .card-footer-row { display: flex; }
    .card-btn {
        text-decoration: none !important;
        background: linear-gradient(135deg,#6366F1,#8B5CF6);
        color: #fff !important; padding: .4rem 1.1rem;
        border-radius: 8px; font-size: .8rem; font-weight: 600;
        transition: all .2s ease;
    }
    .card-btn:hover { opacity:.9; transform:translateY(-1px); }

    /* ── Tabs ── */
    div[data-testid="stTabBar"] button      { font-size:1rem!important; font-weight:600!important; }
    div[data-testid="stTabBar"] button[aria-selected="true"] {
        color: #8B5CF6 !important; border-bottom-color: #8B5CF6 !important;
    }

    /* ── Primary Button ── */
    button[kind="primary"] {
        background: linear-gradient(135deg,#6366F1,#8B5CF6) !important;
        color: #fff !important; font-weight: 600 !important;
        border-radius: 10px !important; border: none !important;
        box-shadow: 0 4px 14px rgba(99,102,241,.3) !important;
        transition: all .2s ease !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(99,102,241,.42) !important;
    }

    /* ── Sidebar ── */
    .sidebar-info-card {
        background: rgba(128,128,128,.04);
        border-radius: 12px; padding: 1.1rem;
        border: 1px solid rgba(128,128,128,.08); margin-top: 1rem;
    }
    .sidebar-info-title { font-weight:600; margin-bottom:.5rem; font-size:.93rem; }
    .sidebar-info-item  { font-size:.8rem; color:#8B949E; margin-bottom:.5rem; line-height:1.4; }

    h1,h2,h3,h4,h5,h6 { font-weight: 700 !important; }
    @keyframes pulse { 0%{opacity:.3} 50%{opacity:1} 100%{opacity:.3} }
    </style>
    """, unsafe_allow_html=True)

    # ── Brand Header ──────────────────────────────────────────────────────────
    st.markdown("""
        <div class="brand-header">
            <h1 class="gradient-text">✈️ RoamAI</h1>
            <p class="subtitle-text">
                Your AI-Powered Travel Concierge — chat your way to the perfect trip
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Init LLM Planner (cached per session) ─────────────────────────────────
    if "planner" not in st.session_state:
        try:
            st.session_state.planner = TravelPlannerApp()
        except Exception as e:
            st.error(f"❌ Failed to initialize RoamAI engine: {e}")
            st.stop()
    planner: TravelPlannerApp = st.session_state.planner

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center;font-size:2.5rem;padding:0.6rem 0;'>✈️</div>",
            unsafe_allow_html=True,
        )
        st.markdown("### 🤖 Agent Network Status")
        st.caption("Real-time telemetry of specialist agents:")
        for agent, status_text in planner.check_status().items():
            render_agent_badge(agent.replace('_', ' ').title(), status_text)

        st.markdown("""
            <div class="sidebar-info-card">
                <div class="sidebar-info-title">ℹ️ RoamAI Architecture</div>
                <div class="sidebar-info-item"><b>Hotel Booking Agent</b><br>CrewAI + GPT-4o-mini</div>
                <div class="sidebar-info-item"><b>Car Rental Agent</b><br>LangGraph + GPT-4o-mini</div>
                <div class="sidebar-info-item"><b>Currency Agent</b><br>LangGraph + Frankfurter API</div>
                <div class="sidebar-info-item"><b>RoamAI Orchestrator</b><br>LangChain Coordinator Core</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Start Over", use_container_width=True):
            for k in ["messages", "answers", "q_idx", "chat_done",
                      "stream_pending", "pending_prompt", "plan_data",
                      "generating", "pdf_bytes"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # Conversational Chat UI
    # ══════════════════════════════════════════════════════════════════════════
    total_q = len(QUESTION_KEYS)
    q_idx   = st.session_state.q_idx

    # Progress dots (visible only while chatting)
    if not st.session_state.chat_done:
        dots = "".join(
            f'<div class="progress-dot '
            f'{"dot-done" if i < q_idx else "dot-active" if i == q_idx else "dot-pending"}">'
            f'</div>'
            for i in range(total_q)
        )
        st.markdown(f'<div class="chat-progress">{dots}</div>', unsafe_allow_html=True)
        label = f"Question {min(q_idx + 1, total_q)} of {total_q}"
        st.caption(f"💬 **{label}** — answer each question to generate your personalized travel plan")

    # ── Bootstrap: trigger first AI message on very first load ────────────────
    if not st.session_state.messages and not st.session_state.stream_pending:
        st.session_state.stream_pending = True
        st.session_state.pending_prompt = build_question_prompt(0, {})
        st.rerun()

    # ── Render chat history from session state ────────────────────────────────
    for msg in st.session_state.messages:
        role   = "assistant" if msg["role"] == "ai" else "user"
        avatar = "🤖" if role == "assistant" else "🧳"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

    # ── Stream next AI message (real-time, token by token) ───────────────────
    if st.session_state.stream_pending and st.session_state.pending_prompt:
        with st.chat_message("assistant", avatar="🤖"):
            # st.write_stream() displays tokens as they arrive — just like ChatGPT
            full_response = st.write_stream(
                planner.stream_llm(st.session_state.pending_prompt)
            )
        # Save completed response to history
        st.session_state.messages.append({"role": "ai", "content": full_response})
        st.session_state.stream_pending = False
        st.session_state.pending_prompt = ""
        st.rerun()

    # ── Chat input box (only visible during active Q&A) ───────────────────────
    if not st.session_state.chat_done and not st.session_state.stream_pending:
        current_key = QUESTION_KEYS[st.session_state.q_idx]
        hints = {
            "destination":     "e.g. Paris, Tokyo, Bali, Santorini...",
            "check_in":        "e.g. August 10, 2025",
            "check_out":       "e.g. August 18, 2025",
            "guests":          "e.g. 2",
            "budget_category": "Budget / Mid-range / Luxury",
            "budget_amount":   "e.g. 2000 USD  or  1500 EUR",
            "car_needed":      "yes  or  no",
            "preferences":     "e.g. vegetarian, beach, museums — or 'none'",
        }
        user_input = st.chat_input(hints.get(current_key, "Type your answer here..."))

        if user_input and user_input.strip():
            clean_input = user_input.strip()

            # Record user's answer
            st.session_state.answers[current_key] = clean_input
            st.session_state.messages.append({"role": "user", "content": clean_input})
            st.session_state.q_idx += 1

            if st.session_state.q_idx >= total_q:
                # All 8 questions answered → stream closing message, then generate plan
                st.session_state.chat_done      = True
                st.session_state.generating     = True
                st.session_state.stream_pending = True
                st.session_state.pending_prompt = build_closing_prompt(st.session_state.answers)
            else:
                # Ask the next question (streamed)
                st.session_state.stream_pending = True
                st.session_state.pending_prompt = build_question_prompt(
                    st.session_state.q_idx, st.session_state.answers
                )
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # Plan Generation (runs after chat + closing message are both done)
    # ══════════════════════════════════════════════════════════════════════════
    if (
        st.session_state.chat_done
        and st.session_state.generating
        and not st.session_state.stream_pending
    ):
        answers    = st.session_state.answers
        dest       = answers.get("destination", "your destination")
        car_needed = "yes" in answers.get("car_needed", "").lower()

        # Extract currency from natural-language budget_amount answer
        currency_match = re.search(
            r'\b(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|SGD|AED|MXN)\b',
            answers.get("budget_amount", ""),
            re.IGNORECASE,
        )
        preferred_currency = currency_match.group(1).upper() if currency_match else "USD"

        with st.status("🕵️ RoamAI agents are working on your plan...", expanded=True) as status_box:

            # 1️⃣ Currency Agent
            status_box.write("💱 Fetching exchange rates via **Currency Agent**...")
            if preferred_currency != "USD":
                cq = (f"Convert {answers.get('budget_amount', '')} to USD. "
                      f"Show exchange rates: {preferred_currency} → USD, EUR, GBP.")
            else:
                cq = (f"Provide current USD exchange rates for {dest}'s local currency. "
                      f"Also show USD to EUR and GBP for reference.")
            currency_resp = planner.ask_agent(planner.currency_url, cq, timeout=45)
            status_box.write("✅ Exchange data ready.")

            # 2️⃣ Hotel Agent
            status_box.write("🏨 Sourcing hotels via **Hotel Agent (CrewAI)**...")
            hq = (
                f"Find the top 8 hotels in {dest} for {answers.get('guests', '2')} guests "
                f"from {answers.get('check_in', '')} to {answers.get('check_out', '')} "
                f"with {answers.get('budget_category', 'mid-range')} budget."
            )
            prefs = answers.get("preferences", "")
            if prefs and prefs.lower() not in ("none", "no", ""):
                hq += f" Special preferences: {prefs}"
            hotel_resp = planner.ask_agent(planner.hotel_url, hq, timeout=120)
            status_box.write("✅ Accommodations catalogued.")

            # 3️⃣ Car Rental Agent (optional)
            car_resp = ""
            if car_needed:
                status_box.write("🚗 Sourcing car rentals via **Car Rental Agent (LangGraph)**...")
                car_resp = planner.ask_agent(
                    planner.car_url,
                    f"Find car rental options in {dest} from {answers.get('check_in')} "
                    f"to {answers.get('check_out')}. "
                    f"User preferences: {prefs or 'none'}",
                    timeout=90,
                )
                status_box.write("✅ Rental options sourced.")
            else:
                status_box.write("ℹ️ Car rental not requested — skipping Car Agent.")

            # 4️⃣ Plan Synthesis
            status_box.write("✍️ Synthesizing your personalized travel plan...")
            plan = planner.generate_plan(answers, hotel_resp, car_resp, currency_resp)
            status_box.update(
                label="✨ Your travel plan is ready!", state="complete", expanded=False
            )

        st.session_state.plan_data = {
            "plan":          plan,
            "hotel_resp":    hotel_resp,
            "car_resp":      car_resp,
            "currency_resp": currency_resp,
            "car_needed":    car_needed,
        }
        st.session_state.generating = False
        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # Plan Results — Tabs + PDF Download
    # ══════════════════════════════════════════════════════════════════════════
    if st.session_state.plan_data:
        data    = st.session_state.plan_data
        answers = st.session_state.answers
        dest    = answers.get("destination", "Your Trip")

        st.markdown("---")
        st.markdown(f"### 🗺️ Your RoamAI Travel Plan — {dest}")

        tab_itin, tab_hotels, tab_cars, tab_budget = st.tabs([
            "🗺️ Itinerary", "🏨 Hotels", "🚗 Car Rentals", "💰 Budget & FX",
        ])

        with tab_itin:
            render_itinerary(data["plan"])

        with tab_hotels:
            hotels = parse_hotel_response(data["hotel_resp"])
            if hotels:
                st.markdown("#### 🏨 Curated Accommodations")
                cols = st.columns(2)
                for idx, hotel in enumerate(hotels):
                    with cols[idx % 2]:
                        st.markdown(render_hotel_card(hotel), unsafe_allow_html=True)
            else:
                st.markdown("#### 🏨 Accommodation Options")
                st.markdown(data["hotel_resp"] or "No hotel data returned from agent.")

        with tab_cars:
            if data["car_needed"]:
                car_opts = extract_car_options(data["car_resp"])
                if car_opts:
                    st.markdown("#### 🚗 Rental Car Options")
                    cols = st.columns(2)
                    for idx, car in enumerate(car_opts):
                        with cols[idx % 2]:
                            st.markdown(render_car_card(car), unsafe_allow_html=True)
                else:
                    st.markdown("#### 🚗 Car Rental Options")
                    st.markdown(data["car_resp"] or "No car rental data returned from agent.")
            else:
                st.info("🚗 Car rental was not requested for this trip.")

        with tab_budget:
            st.markdown("#### 💰 Currency & Budget Information")
            st.markdown(data["currency_resp"] or "Currency data unavailable.")

        # ── PDF Download ──────────────────────────────────────────────────────
        st.markdown("---")
        pdf_col, info_col = st.columns([1, 2])

        with pdf_col:
            if st.session_state.pdf_bytes is None:
                # Generate PDF on first click
                if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
                    with st.spinner("Building your PDF report..."):
                        st.session_state.pdf_bytes = generate_pdf_report(
                            answers,
                            data["plan"],
                            data["hotel_resp"],
                            data["car_resp"],
                            data["currency_resp"],
                        )
                    if st.session_state.pdf_bytes is None:
                        st.error(
                            "PDF generation requires `fpdf2`.\n\n"
                            "Run:  `pip install fpdf2`"
                        )
                    st.rerun()
            else:
                # PDF ready — show download button
                safe_dest = dest.replace(' ', '_').lower()
                st.download_button(
                    label="⬇️ Download PDF Travel Report",
                    data=st.session_state.pdf_bytes,
                    file_name=f"roamai_{safe_dest}_travel_plan.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )
                st.success("✅ PDF ready! Click above to download.")

        with info_col:
            st.info(
                "**📄 Your PDF report includes:**\n"
                "- 🎨 Branded cover page with trip summary\n"
                "- 🌟 Trip overview & key highlights\n"
                "- 📅 Complete day-by-day itinerary\n"
                "- 🏨 Hotel recommendations & pricing\n"
                "- 🚗 Car rental options (if requested)\n"
                "- 💰 Full budget breakdown\n"
                "- 💱 Currency & money tips\n"
                "- ✈️ Travel tips & pre-trip checklist"
            )


if __name__ == "__main__":
    main()