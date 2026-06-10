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
- **Frontend**: Streamlit (served behind nginx reverse proxy on port 8080)
- **Database**: PostgreSQL (vDB Relational on VNG Cloud) — schema auto-created on startup via `Base.metadata.create_all()`
- **Agentic Flow**: LangGraph
- **AI Integration**: VNG Cloud AI Platform (`google/gemma-4-31b-it` via OpenAI-compatible API)
- **Deployment**: GreenNode AgentBase (two runtimes: backend + frontend, both on port 8080)
- **Local Testing**: Built-in **Mock Fallback Engine** when `AI_PLATFORM_API_KEY` is not configured.

---

## 📁 Project Structure

```
after-work-agent/
├── requirements.txt         # Core dependencies
├── Dockerfile               # Production multi-process docker package
├── entrypoint.sh            # Runs backend & frontend servers in parallel
├── README.md                # Main readme
├── .env                     # Sensitive config (not committed — see .gitignore)
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
│   │   ├── database.py      # SQLAlchemy engine & schema init
│   │   ├── models.py        # Database models (PostgreSQL)
│   │   ├── schemas.py       # Pydantic serialization schemas
│   │   ├── org_utils.py     # Org closeness and recommendation scoring calculations
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── llm.py       # VNG Cloud AI Platform client / Mock Fallback Engine
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

### Prerequisites

Copy `.env.example` to `.env` and fill in your credentials:
```
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<dbname>
AI_PLATFORM_API_KEY=<your-vng-cloud-api-key>
AI_PLATFORM_MODEL=google/gemma-4-31b-it
AI_PLATFORM_API_BASE=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
BACKEND_URL=http://localhost:8000
```

### Option A: Running Locally

1. Create a virtual environment and install requirements:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Start the FastAPI backend:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

3. Open a second terminal and run the Streamlit frontend:
   ```bash
   streamlit run frontend/app.py --server.port 8501
   ```

### Option B: Running with Docker

1. Build backend and frontend images:
   ```bash
   docker build --platform linux/amd64 -t after-work-agent-backend .
   docker build --platform linux/amd64 -f frontend/Dockerfile -t after-work-agent-frontend ./frontend
   ```

2. Run backend (port 8080):
   ```bash
   docker run -p 8080:8080 --env-file .env after-work-agent-backend
   ```

3. Run frontend (port 8080, proxied via nginx):
   ```bash
   docker run -p 8081:8080 --env-file .env after-work-agent-frontend
   ```

### Option C: Deployed on GreenNode AgentBase

- **Frontend**: `https://endpoint-ed2a7b49-8ce2-43bd-9f35-b59c33696a09.agentbase-runtime.aiplatform.vngcloud.vn`
- **Backend API**: `https://endpoint-00afda81-2e11-49f5-8ba5-e63fe76a86d3.agentbase-runtime.aiplatform.vngcloud.vn`

---

## 🧪 Running Automated Tests

To verify that the system is fully functional, run the automated scenario runner:
```bash
python3 backend/tests/test_flow.py
```
This requires a running backend and a configured `.env` with a valid `DATABASE_URL`. It seeds simulation profiles and verifies that all five scenarios are correctly resolved by the LangGraph agents.
