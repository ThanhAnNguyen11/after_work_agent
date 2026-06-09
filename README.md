# After Work Agent 🤖

A complete hackathon MVP for an intelligent **After Work Activity Discovery Agent**. It helps employees discover meaningful after-work events (football, running, board games, yoga, zumba, and knowledge-sharing sessions), break routine traps, expand their internal social network beyond immediate squads, and automatically register new events proposed in chat channels.

---

## North Star

Help employees discover and join after-work activities happening inside the company.

The goal is to make activities easier to discover, easier to join, and help employees connect with more communities.

---

## 🌟 Key Product Capabilities

1. **Intelligent Recommendations (Scenario 1)**: Suggests activities matching user profile interests, attendance history, scheduled classes, and organizational peers.
2. **Activity Extraction Agent (Scenario 2)**: Parses free-text channel announcements (e.g., *"Football at 6PM. Need 2 more players."*) to automatically create and register dynamic activities in the database.
3. **Routine Breaker / Discovery Agent (Scenario 3)**: Detects repetition loops in user history (e.g., fitness-only routines) and recommends novelty categories (e.g., board game socials).
4. **New Hire Onboarding (Scenario 4)**: Welcomes new employees with department/squad matching recommendations to accelerate team integration.
5. **Peer Matching / Missing Players Alert (Scenario 5)**: When an activity is short of participants, the agent automatically identifies and displays matching candidate profiles who might want to join, highlighting interests and organizational distance.

---

## 🛠 Tech Stack
- **Backend**: FastAPI (Python), SQLAlchemy
- **Frontend**: Streamlit
- **Database**: SQLite
- **Agentic Flow**: LangGraph
- **AI Integration**: OpenRouter API (`qwen/qwen-2.5-72b-instruct` or custom selection)
- **Local Testing**: Built-in **Mock Fallback Engine** that emulates Qwen3 model agent responses when no API Key is configured.

---

## 📁 Project Structure

```
after-work-agent/
├── requirements.txt         # Core dependencies
├── Dockerfile               # Production multi-process docker package
├── entrypoint.sh            # Runs backend & frontend servers in parallel
├── README.md                # Main readme
├── database.db              # SQLite Database (Auto-created on startup)
├── docs/                    # Product specs & agent behavior
│   ├── 1_core_product.md    # Auth, onboarding, interests & core features
│   ├── 2_activity_lifecycle.md # Creation, guidelines, join flow & full capacity
│   ├── 3_data_model.md      # Database tables and fields specification
│   ├── 4_agent_capabilities.md # Agent inputs/outputs (6 agents)
│   └── 5_system_prompts.md  # Agent identity, tone & grounding rules
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI server & endpoints
│   │   ├── database.py      # SQLAlchemy engine & SQLite seeding script
│   │   ├── models.py        # SQLite Database models
│   │   ├── schemas.py       # Pydantic serialization schemas
│   │   ├── org_utils.py     # Org closeness and recommendation scoring calculations
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── llm.py       # OpenRouter client / Mock Fallback Engine
│   │       ├── extraction.py# Activity Extraction Agent
│   │       ├── discovery.py # Discovery Agent (Routine Breaking)
│   │       ├── social_opp.py# Social Opportunity Agent (Cross-squad connection)
│   │       ├── recommendation.py # Recommendation Agent (Formats NL output)
│   │       └── graph.py     # Compiled LangGraph state machine
│   └── tests/
│       └── test_flow.py     # Automates checking of Scenarios 1-5
└── frontend/
    ├── app.py               # Streamlit application with custom premium layout
    └── api_client.py        # Streamlit REST client connecting to FastAPI
```


---

## 📚 Documentation

1. [Core Product & Features](docs/1_core_product.md)
2. [Activity Lifecycle](docs/2_activity_lifecycle.md)
3. [Data Model](docs/3_data_model.md)
4. [Agent Capabilities](docs/4_agent_capabilities.md)
5. [Agent Behavior](docs/5_system_prompts.md)

---

## 🚀 Running the App

### Option A: Running with Docker (Recommended)

1. Build the docker image:
   ```bash
   docker build -t after-work-agent .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 -p 8501:8501 -e OPENROUTER_API_KEY="your-api-key" after-work-agent
   ```
   *(If you don't have an OpenRouter API key, omit the environment variable. The system will automatically fall back to its internal Mock Engine so you can demonstrate the hackathon MVP immediately!)*

3. Access the interfaces:
   - **Streamlit Frontend Dashboard**: [http://localhost:8501](http://localhost:8501)
   - **FastAPI backend endpoints API**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option B: Running Locally

1. Create a virtual environment and install requirements:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Start the FastAPI backend:
   ```bash
   # Run from root folder
   uvicorn backend.app.main:app --reload --port 8000
   ```

3. Open a second terminal window and run the Streamlit frontend:
   ```bash
   streamlit run frontend/app.py --server.port 8501
   ```

---

## 🧪 Running Automated Tests

To verify that the system is fully functional, run the automated scenario runner:
```bash
python3 backend/tests/test_flow.py
```
This executes the SQLite database migrations, seeds simulation profiles (including mock gym classes, football host players, and a gym routine history), and verifies that all five scenarios are correctly resolved by the LangGraph agents.
