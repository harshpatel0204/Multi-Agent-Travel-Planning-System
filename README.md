# A2A Protocol Travel Planning System

A sophisticated multi-agent travel planning system that demonstrates the **A2A (Agent-to-Agent) Protocol** in action. This project showcases how multiple specialized AI agents can collaborate seamlessly to provide comprehensive travel planning services including hotel bookings, car rentals, and currency conversions.

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [System Components](#system-components)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [A2A Protocol Integration](#a2a-protocol-integration)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This project implements a multi-agent travel planning system built to demonstrate modern AI agent orchestration using different frameworks:

- **LangGraph** for the Car Rental and Currency agents
- **CrewAI** for the Hotel Booking agent  
- **Google ADK** for the Travel Planner master agent
- **A2A Protocol** for inter-agent communication
- **Streamlit** for user-friendly web interface

The system showcases how diverse agent frameworks can work together harmoniously through standardized protocols, enabling scalable and maintainable multi-agent systems.

---

## Key Features

### 🎯 Core Capabilities

- **Hotel Search and Booking**: Intelligent hotel discovery and booking assistance across multiple budget ranges
- **Car Rental Management**: Comprehensive car rental search with flexible filtering by location, dates, and vehicle type
- **Currency Conversion**: Real-time currency exchange rate lookups for international travel planning
- **Travel Coordination**: Master travel planner that orchestrates multiple specialized agents
- **Web Interface**: User-friendly Streamlit application for interactive travel planning
- **Health Monitoring**: Built-in health checks for all agent services
- **Inter-Agent Communication**: Seamless agent-to-agent communication via A2A Protocol

### 🔌 Technical Features

- **RESTful API**: FastAPI-based endpoints for each agent
- **Async Processing**: Asynchronous request handling for improved performance
- **Memory Management**: In-memory session and artifact management
- **Error Handling**: Comprehensive error handling and logging
- **Configuration Management**: Environment-based configuration using `.env` files
- **Type Safety**: Full Pydantic model validation for all inputs and outputs

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Streamlit Web Interface (Port 10000)            │
├─────────────────────────────────────────────────────────┤
│                                                          │
├──────────────────┬──────────────────┬──────────────────┤
│                  │                  │                  │
│  Travel Planner  │  Hotel Booking   │  Car Rental      │
│  Agent (ADK)     │  Agent (CrewAI)  │  Agent (LG)      │
│  Port 10001      │  Port 10002      │  Port 10003      │
│                  │                  │                  │
├──────────────────┴──────────────────┴──────────────────┤
│                                                          │
│         Currency Agent (LangGraph)                      │
│                  Port 10004                             │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  External APIs: Serper (Search), Frankfurter (FX)      │
└─────────────────────────────────────────────────────────┘
```

### Agent-to-Agent Communication

Agents communicate via the **A2A Protocol**, which provides:
- Standardized `AgentCard` discovery
- Message format standardization
- Asynchronous request/response handling
- Service registry management

---

## Technology Stack

| Component | Framework/Library | Version |
|-----------|------------------|---------|
| **Travel Planner Agent** | Google ADK | 1.4.2+ |
| **Car Rental Agent** | LangGraph | 0.6.0+ |
| **Currency Agent** | LangGraph | 0.6.0+ |
| **Hotel Agent** | CrewAI | 0.130.0+ |
| **LLM Provider** | LangChain OpenAI | 0.3.3+ |
| **API Framework** | FastAPI | 0.115.13+ |
| **Server** | Uvicorn | 0.34.2+ |
| **Data Validation** | Pydantic | 2.11.7+ |
| **Web UI** | Streamlit | 1.46.0+ |
| **HTTP Client** | HTTPX | 0.28.1+ |
| **A2A Protocol** | A2A SDK | 0.2.13+ |

### Internal Dependencies

- **LangChain Core**: 0.3.64+
- **Nest Asyncio**: 1.6.0+ (for async event loop handling)
- **Python-Jose**: 3.4.0+ (for secure token handling)
- **Requests**: 2.32.4+ (HTTP library)

---

## System Components

### 1. **Travel Planner Agent** (Google ADK)
**Location**: `travel_planner_agent_adk/`

Master orchestrator that coordinates with other specialized agents.

**Capabilities**:
- Agent discovery and card resolution
- Multi-agent orchestration
- Session management
- Artifact handling
- OpenRouter LLM integration

**Key Files**:
- `agent.py`: Core agent implementation with A2A integration
- `agent_executor.py`: FastAPI server (Port 10001)
- `remote_agent_connection.py`: A2A protocol manager

**Environment**: Requires `OPENROUTER_API_KEY`

---

### 2. **Hotel Booking Agent** (CrewAI)
**Location**: `hotel_booking_agent_crewai/`

Specialized agent for hotel search and booking.

**Capabilities**:
- Hotel search by location and dates
- Budget-aware filtering
- Price extraction from search results
- Booking confirmation handling
- Web search integration via Serper

**Key Files**:
- `agent.py`: CrewAI agent configuration
- `agent_executor.py`: FastAPI server (Port 10002)

**Features**:
- HotelSearchTool: Unified hotel discovery
- HotelBookingTool: Booking transaction handling
- Dynamic budget filtering

**Environment**: Requires `SERPER_API_KEY`

---

### 3. **Car Rental Agent** (LangGraph)
**Location**: `car_rental_agent_langgraph/`

Specialized agent for car rental searches and bookings.

**Capabilities**:
- Car rental availability search
- Vehicle type filtering (economy, luxury, SUV)
- Date-based rental management
- Price estimation
- Booking processing

**Key Files**:
- `agent.py`: LangGraph agent with ReAct pattern
- `agent_executor.py`: FastAPI server (Port 10003)

**Features**:
- CarSearchToolInput: Structured search schema
- CarBookingToolInput: Booking schema
- Real-time availability checks

**Environment**: Requires `SERPER_API_KEY`

---

### 4. **Currency Agent** (LangGraph)
**Location**: `currency_agent_langhraph/`

Specialized agent for currency conversions and exchange rates.

**Capabilities**:
- Real-time exchange rate lookup
- Historical exchange rates
- Multi-currency support
- Rate trend analysis

**Key Files**:
- `agent.py`: LangGraph agent using ReAct
- `agent_executor.py`: FastAPI server (Port 10004)

**Features**:
- `get_exchange_rate` tool: Frankfurter API integration
- Structured response format
- Error handling for invalid currencies

**External APIs**: Frankfurter.app (no API key required)

---

### 5. **Streamlit Web Interface**
**Location**: `streamlit_travel_app.py`

User-friendly web application for interactive travel planning.

**Features**:
- Agent health status dashboard
- Interactive travel queries
- Real-time agent status monitoring
- Multi-agent coordination display

**Port**: 8501 (default Streamlit)

---

## Installation & Setup

### Prerequisites

- Python 3.9+
- Conda or virtual environment manager
- 4GB+ RAM
- Internet connection (for API access)

### Step 1: Clone and Navigate

```bash
cd c:\projects\a2a_protocol_fundamentals_python
```

### Step 2: Create Virtual Environment

```bash
# Using conda (recommended)
conda create -n travel_planning python=3.11
conda activate travel_planning

# Or using venv
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

### Step 3: Install Dependencies

```bash
# Install Streamlit and main dependencies
pip install -r travel_planning_system/streamlit_requirements.txt

# Install each agent's dependencies
pip install -r travel_planning_system/car_rental_agent_langgraph/requirements.txt
pip install -r travel_planning_system/currency_agent_langhraph/requirements.txt
pip install -r travel_planning_system/hotel_booking_agent_crewai/requirements.txt
pip install -r travel_planning_system/travel_planner_agent_adk/requirements.txt
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys (Required)
OPENROUTER_API_KEY=your_openrouter_api_key_here
SERPER_API_KEY=your_serper_api_key_here

# Optional: Google GenAI credentials for ADK
GOOGLE_API_KEY=your_google_api_key_here (optional)

# Service Configuration (Optional)
HOTEL_AGENT_URL=http://localhost:10002
CAR_RENTAL_AGENT_URL=http://localhost:10003
CURRENCY_AGENT_URL=http://localhost:10004
TRAVEL_PLANNER_AGENT_URL=http://localhost:10001
```

### API Key Setup

1. **OpenRouter API Key**: Visit [https://openrouter.ai](https://openrouter.ai)
   - Sign up and create an API key
   - Add credit to your account

2. **Serper API Key**: Visit [https://serper.dev](https://serper.dev)
   - Sign up for free tier
   - Create API key for web search functionality

3. **Google API Key** (Optional): Visit [Google Cloud Console](https://console.cloud.google.com)
   - Create a project
   - Enable Google Generative AI API
   - Create credentials

---

## Configuration

### Port Configuration

Each agent runs on a specific port:
- **Travel Planner Agent**: 10001
- **Hotel Booking Agent**: 10002  
- **Car Rental Agent**: 10003
- **Currency Agent**: 10004
- **Streamlit UI**: 8501

To change ports, modify the `uvicorn.run()` call in each agent's `agent_executor.py`:

```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10001)
```

### LLM Configuration

All agents use OpenRouter with the `openai/gpt-4o-mini` model by default.

To change the model in any agent's `agent.py`:

```python
self.model = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
    model="openai/gpt-4o-mini",  # Change this
    temperature=0,
)
```

### External API Configuration

- **Serper Search**: Used for hotel and car rental searches via Google Custom Search
- **Frankfurter.app**: Free exchange rate API (no configuration needed)

---

## Running the System

### Option 1: Run All Agents (Recommended)

```bash
# Terminal 1: Travel Planner Agent
cd travel_planning_system/travel_planner_agent_adk/app
python __main__.py

# Terminal 2: Hotel Booking Agent
cd travel_planning_system/hotel_booking_agent_crewai/app
python __main__.py

# Terminal 3: Car Rental Agent
cd travel_planning_system/car_rental_agent_langgraph/app
python __main__.py

# Terminal 4: Currency Agent
cd travel_planning_system/currency_agent_langhraph/app
python __main__.py

# Terminal 5: Streamlit UI
cd travel_planning_system
streamlit run streamlit_travel_app.py
```

### Option 2: Run Streamlit UI Only

If agents are already running:

```bash
cd travel_planning_system
streamlit run streamlit_travel_app.py
```

The UI will be available at: `http://localhost:8501`

### Option 3: Run Individual Agents

```bash
# Car Rental Agent
cd travel_planning_system/car_rental_agent_langgraph/app
python agent_executor.py

# Or using uvicorn directly
uvicorn agent_executor:app --host 0.0.0.0 --port 10003 --reload
```

---

## Testing

### Run All Tests

```bash
cd travel_planning_system
python test_all_agents.py
```

This will:
1. Check all agent health endpoints
2. Verify agent discovery via agent cards
3. Test end-to-end agent communication
4. Validate response formats

### Individual Agent Tests

```bash
# Test car rental agent
cd travel_planning_system/car_rental_agent_langgraph
python test_car_rental_agent.py

# Test hotel agent
cd travel_planning_system/hotel_booking_agent_crewai
python test_hotel_agent.py

# Test currency agent
cd travel_planning_system/currency_agent_langhraph
python test_currency_agent.py

# Test travel planner
cd travel_planning_system/travel_planner_agent_adk
python test_travel_planner.py
```

### Health Check Endpoints

```bash
# Test via curl
curl http://localhost:10001/health
curl http://localhost:10002/health
curl http://localhost:10003/health
curl http://localhost:10004/health
```

---

## API Documentation

### Hotel Booking Agent

**Base URL**: `http://localhost:10002`

#### Send Message
```http
POST /send_message
Content-Type: application/json

{
  "id": "msg-123",
  "params": {
    "message": {
      "parts": [
        {"text": "Find me a hotel in Paris from 2024-12-15 to 2024-12-20 under $150"}
      ]
    }
  }
}
```

#### Get Agent Card
```http
GET /agent_card
```

Response:
```json
{
  "name": "Hotel_Booking_Agent",
  "description": "Specialized agent for finding and booking hotels...",
  "version": "1.0.0"
}
```

---

### Car Rental Agent

**Base URL**: `http://localhost:10003`

#### Send Message
```http
POST /send_message
Content-Type: application/json

{
  "id": "msg-456",
  "params": {
    "message": {
      "parts": [
        {"text": "I need an economy car rental in Los Angeles from 2024-12-20 to 2024-12-25"}
      ]
    }
  }
}
```

---

### Currency Agent

**Base URL**: `http://localhost:10004`

#### Send Message
```http
POST /send_message
Content-Type: application/json

{
  "id": "msg-789",
  "params": {
    "message": {
      "parts": [
        {"text": "What is the current USD to EUR exchange rate?"}
      ]
    }
  }
}
```

---

### Travel Planner Agent (Master)

**Base URL**: `http://localhost:10001`

#### Send Message
```http
POST /send_message
Content-Type: application/json

{
  "id": "msg-master-001",
  "params": {
    "message": {
      "parts": [
        {"text": "Plan a trip to Paris for 5 days with hotel and car rental"}
      ]
    }
  }
}
```

---

## A2A Protocol Integration

### What is A2A?

The **Agent-to-Agent (A2A) Protocol** is a standardized communication framework that enables autonomous agents to discover, connect to, and interact with each other seamlessly.

### Key A2A Concepts Used

1. **Agent Card Discovery**
   - Each agent exposes its capabilities via an `AgentCard`
   - Contains agent name, description, and metadata
   - Endpoint: `GET /agent_card`

2. **Message Standardization**
   - Structured message format with `SendMessageRequest` and `SendMessageResponse`
   - Type safety via Pydantic models
   - Support for artifacts and tasks

3. **Remote Agent Connections**
   - Travel Planner discovers and connects to other agents
   - Async HTTP client for inter-agent communication
   - Automatic retry and error handling

### Implementation Files

- `travel_planner_agent_adk/app/remote_agent_connection.py`: A2A protocol manager
- `a2a-sdk` dependency: Protocol implementation

### Example: Agent-to-Agent Call

```python
# Reference from travel_planner_agent_adk/app/agent.py
connection = self.remote_agent_connections[agent_name]
response = await connection.send_message(send_message_request)
```

---

## Project Structure

```
a2a_protocol_fundamentals_python/
├── README.md                           # Project documentation
├── LICENSE                             # Apache 2.0 License
│
└── travel_planning_system/
    ├── streamlit_travel_app.py         # Web UI entry point
    ├── streamlit_requirements.txt      # UI dependencies
    ├── test_all_agents.py              # Integration tests
    │
    ├── car_rental_agent_langgraph/
    │   ├── requirements.txt
    │   ├── test_car_rental_agent.py
    │   └── app/
    │       ├── __main__.py
    │       ├── agent.py                # LangGraph agent
    │       ├── agent_executor.py       # FastAPI server
    │       └── simple_executor.py
    │
    ├── currency_agent_langhraph/
    │   ├── requirements.txt
    │   ├── test_currency_agent.py
    │   └── app/
    │       ├── __main__.py
    │       ├── agent.py                # LangGraph agent
    │       ├── agent_executor.py       # FastAPI server
    │       └── simple_executor.py
    │
    ├── hotel_booking_agent_crewai/
    │   ├── requirements.txt
    │   ├── test_hotel_agent.py
    │   └── app/
    │       ├── __main__.py
    │       ├── agent.py                # CrewAI agent
    │       ├── agent_executor.py       # FastAPI server
    │       └── simple_executor.py
    │
    └── travel_planner_agent_adk/
        ├── requirements.txt
        ├── test_travel_planner.py
        └── app/
            ├── __main__.py
            ├── agent.py                # Google ADK agent
            ├── agent_executor.py       # FastAPI server
            ├── simple_executor.py
            └── remote_agent_connection.py  # A2A protocol
```

---

## Contributing

### Development Workflow

1. **Fork or Clone** the repository
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make changes** following code style guidelines
4. **Test thoroughly**: Run all test suites
5. **Commit with clear messages**: `git commit -m "Add detailed description"`
6. **Push to branch**: `git push origin feature/your-feature`
7. **Create Pull Request** with description

### Code Style Guidelines

- Follow PEP 8 conventions
- Use type hints for all functions
- Write docstrings for classes and public methods
- Use Pydantic for data validation
- Add tests for new features

### Testing Requirements

- All new features must include unit tests
- Run `test_all_agents.py` before submitting changes
- Ensure no breaking changes to existing APIs

---

## Troubleshooting

### Common Issues

**1. "OPENROUTER_API_KEY not found"**
- Solution: Ensure `.env` file exists in the project root with valid API key

**2. "Connection refused" errors**
- Solution: Verify all agents are running on correct ports
- Check if other services are using those ports: `netstat -ano | findstr :10001`

**3. "Agent discovery failed"**
- Solution: Ensure Travel Planner Agent is configured with correct agent URLs
- Check agent health: `curl http://localhost:10002/health`

**4. Python import errors**
- Solution: Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version compatibility: `python --version` (requires 3.9+)

**5. Async event loop errors**
- Solution: Ensure `nest_asyncio` is installed
- Run: `pip install nest-asyncio`

---

## Performance Optimization

### Tips for Production

1. **Use process pools**: Run agents with multiple workers
   ```bash
   uvicorn agent_executor:app --workers 4 --port 10001
   ```

2. **Enable caching**: Cache exchange rates and search results

3. **Load balancing**: Deploy agents behind load balancers for scalability

4. **Monitoring**: Implement health checks and logging

5. **Rate limiting**: Add rate limiting for API endpoints

---

## Future Enhancements

- [ ] Database integration for booking history
- [ ] User authentication and authorization
- [ ] Payment gateway integration
- [ ] Email notifications
- [ ] Real-time booking confirmations
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Mobile app integration

---

## References

- [A2A Protocol Documentation](https://github.com/google/a2a)
- [Google ADK Documentation](https://developers.google.com/adk)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

## License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

**Summary**: You are free to use, modify, and distribute this software, provided you include the original license and provide attribution.

---

## Support

For issues, questions, or suggestions:

1. **Check existing issues** in the repository
2. **Review the troubleshooting section** above
3. **Create a detailed GitHub issue** with:
   - Python version and OS
   - Error message and stack trace
   - Steps to reproduce
   - Expected vs. actual behavior

---

## Acknowledgments

This project demonstrates:
- Modern multi-agent AI architecture
- A2A Protocol implementation
- Integration of multiple AI frameworks (LangGraph, CrewAI, Google ADK)
- Production-ready FastAPI services
- Streamlit web UI development

---

**Last Updated**: March 11, 2026  
**Version**: 1.0.0  
**Status**: Production Ready
