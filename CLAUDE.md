# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Running the App Locally

```bash
# Backend (from repo root)
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (from repo root)
streamlit run frontend/app.py --server.port 8501

# Run scenario tests (requires running backend + valid DATABASE_URL in .env)
python3 backend/tests/test_flow.py
```

Required `.env` at repo root (copy from `.env.example`):
- `DATABASE_URL` — PostgreSQL connection string
- `AI_PLATFORM_API_KEY` — VNG Cloud AI key; if missing, mock fallback engine activates
- `BACKEND_URL` — URL frontend JS calls for API (injected into HTML at Streamlit startup)

---

## Architecture

### Backend (`backend/app/`)

FastAPI + SQLAlchemy. Single `main.py` with all endpoints. DB schema auto-created on startup via `Base.metadata.create_all()`.

**LangGraph agent flow** (`agents/graph.py`): every `/api/chat` call runs a compiled state machine:
1. `intent_node` — classifies message as `extract` (create activity) or `recommend`
2. `extraction_node` — parses free-text into structured activity and creates it
3. `discovery_node` — checks participation history for routine traps
4. `social_opp_node` — finds cross-squad peer opportunities
5. `recommendation_node` — scores activities and builds natural-language response

`agents/llm.py` contains the VNG Cloud client and a **mock fallback engine** that returns canned responses when `AI_PLATFORM_API_KEY` is not set — tests work without credentials.

### Frontend (`frontend/app.py`)

Streamlit app (~1900 lines). **Not a typical Streamlit app** — almost all UI is custom HTML injected via `components.declare_component()` (Streamlit's bidirectional iframe protocol).

**Key pattern:**
- `design/*/code.html` = source HTML templates (Airbnb design system, Tailwind + Material Symbols)
- `app.py` reads each template at startup, patches it with real data and JS (string replacements + regex), writes the result to `*_component/index.html`
- `components.declare_component(path=...)` serves the folder as an iframe; child→parent communication via `Streamlit.setComponentValue({action, ...})`
- `*_component/` folders are **generated at runtime** — do not edit them directly; edit the source in `design/`

`_MASCOT_DATA_URI` is a base64-encoded inline image loaded once at module level from `images/mascot.jpg`.

**Navigation:** Streamlit `session_state.page` drives page routing. Inside the homepage iframe, JS `showView()` switches between embedded views (agent, discover, create, profile) without a Streamlit rerun.

**BACKEND_URL** is currently hardcoded as `http://localhost:8000` in two JS injections inside `app.py`. Must be updated to environment variable before cloud deployment (see `docs/6_feature_gaps.md`).

### Data Model

See `docs/3_data_model.md` for spec. Key gap: several spec'd fields (`working_hours`, `skills_to_learn`, `horoscope`, `business_unit`, `group_name`, gamification tables) are **not yet in `models.py`**. What's in the DB is a subset of the spec.

---

## Key Constraints

- When editing frontend UI, edit `frontend/design/*/code.html` — not `*_component/index.html` (generated). Restart Streamlit after changes to regenerate components.
- String replacements in `_build_main_component_html()` are fragile: if you change `design/homepage_discover_afterwork_mascot_logo/code.html`, verify the replacement targets still match (there is a pattern-check script pattern in the session history).
- The agent mock fallback activates automatically when `AI_PLATFORM_API_KEY` is absent — do not rely on it to test real scoring logic.
- DB schema changes require updating both `models.py` and `schemas.py` (Pydantic). `Base.metadata.create_all()` adds new tables/columns on restart but does not run migrations.
