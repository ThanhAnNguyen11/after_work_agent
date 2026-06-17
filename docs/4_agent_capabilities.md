# PART 4: AGENT CAPABILITIES

## Overview

The After Work Agent consists of multiple specialized capabilities.

Each capability has a clear purpose, trigger, input, and output.

The goal is to separate business responsibilities from communication style.

---

## Multi-turn Conversation

> ✅ Implemented

The agent maintains awareness of the current conversation context across multiple messages.

Conversation History is the list of messages exchanged in the current session (user and assistant turns).

Agents that use Conversation History must:

* Not repeat activities already recommended in the same session unless the user explicitly asks.
* Understand follow-up questions in context (e.g. "what about something else?" refers to the previous recommendation).
* Carry forward detected intent across turns unless the user signals a new intent.

---

## Chat Session Management

> ✅ Implemented — `localStorage`-only; sessions lost if browser data cleared (no DB backend)

### New Chat

A **New Chat** button at the top of the sidebar:

* Saves the current session (if it contains at least 1 user message) to the Recents list in `localStorage`
* Clears `chatHistory` and fetches a fresh greeting from `/api/users/{id}/conversation-starter`

### Recent Sessions

A **Recents** section at the bottom of the sidebar renders past sessions dynamically from `localStorage` key `aw_sessions_{USER_ID}`. Each entry shows the first user message as the title. Clicking a session restores its full message history and switches to the agent view.

Storage format per session: `{ id, title, messages[], created_at }`. Max 15 sessions stored.

---

## Agent 1 - Activity Recommendation

> ✅ Implemented

### Purpose

Recommend relevant activities to users.

### Trigger

* User asks for recommendations.
* User opens the application.
* User requests activity suggestions.

### Input

* User Profile
* User Interests
* Participation History
* Available Activities
* Conversation History (current session)

### Output

* Recommended Activities

### Multi-turn Behavior

* Do not recommend activities already suggested in the current session unless the user explicitly asks again.
* Treat follow-up messages as refinements, not new standalone queries.
* If the user says "something else", "other options", or "more", exclude previously shown activities from the ranked candidates.

---

## Agent 2 - Activity Extraction

> ✅ Implemented

### Purpose

Convert natural language activity descriptions into structured activity data.

### Trigger

User creates an activity using free text.

### Input

Example:

Football at 18:00.
Need 2 more players.

### Output

Structured activity information.

Example:

{
"activity_type": "football",
"time": "18:00",
"required_players": 2
}

The system can then create the activity automatically.

---

## Agent 3 - Participation Collection

> ✅ Implemented

### Purpose

Collect participation information when activity history is incomplete.

### Trigger

User opens the application and unresolved participation exists.

### Input

* User
* Date
* Existing Participation History

### Output

Participation record.

The system updates Participation History.

---

## Agent 4 - Conversation Starter

> ✅ Implemented

### Purpose

Reduce empty-state experience and proactively engage users.

### Trigger

User opens the application.

### Logic

Priority 1:

If unresolved participation exists:

* Trigger Participation Collection.

Priority 2:

Otherwise:

* Start a contextual conversation.

### Input

* User Profile
* Participation History
* Available Activities

### Output

Conversation starter message.

---

## Agent 5 - Intent Detection

> ✅ Implemented

### Purpose

Understand what the user is currently looking for.

### Possible Intents

* Exercise
* Learning
* Networking
* Relaxation
* Exploration
* Chat — casual conversation or social questions directed at the agent (e.g. "how are you?", "what did you do yesterday?"). Routes to a lightweight response node; the full activity pipeline does not run.

### Input

* Current user message
* Conversation History (current session, last N turns)

### Output

Detected intent.

The detected intent should influence recommendations.

### Multi-turn Behavior

* If the user has not expressed a new intent, carry forward the intent detected in the previous turn.
* If the current message is a follow-up with no clear intent signal (e.g. "what else?", "show me more"), reuse the last detected intent.

---

## Agent 6 - Activity Matching

> 🟡 Partial — interest tag matching implemented; participation history and chat history not yet used as scoring signals

### Purpose

Match activities with user interests, behavior, and intent.

### Input

| Input | Status | Notes |
|---|---|---|
| User Profile (interests) | ✅ | Onboarding interest tags used in scoring |
| Participation History (activity type) | ✅ | Past joined activity types drive behavioral interest score |
| Participation History (location type) | ✅ | On/off-campus preference inferred from history — +0.1 boost to matching activities |
| Chat History | ❌ | Expressed preferences from past conversations not extracted or used |
| User Intent (current session) | ✅ | Intent detected from current message |
| Available Activities | ✅ | All active activities scored |
| Previously Recommended IDs | ✅ | Filtered within current session |

### Output

Ranked activity candidates.

The recommendation agent uses these candidates to generate recommendations.

### Multi-turn Behavior

* Filter out activities that were already presented in the current session before scoring.
* If no new candidates remain after filtering, relax the filter and surface the top candidates again with a note that options are limited.

---

## Agent 7 - 3-Attempt Match Flow

> ✅ Implemented — attempt state persisted in `recommendation_sessions` DB table per user

### Purpose

Handle the case where Agent 6 cannot find a strong match on the first attempt, escalating through up to three structured attempts before exiting gracefully.

### Attempt Flow

Attempt 1: Standard activity matching (Agent 6 output).

Attempt 2: If no strong match found, ask the user targeted filter questions (e.g. preferred time slot, indoor vs outdoor, group vs solo) to narrow the candidate pool and re-run matching.

Attempt 3: If still no match after Attempt 2, shift to a wellbeing-focused conversation — acknowledge that options are limited today, ask how the user is feeling, and offer a supportive, low-pressure response rather than forcing a recommendation.

### Implementation Details

Attempt state is tracked in `recommendation_sessions` (one row per user, auto-reset after 24 h or on successful activity join). The graph entry point is `session_load_node` which hydrates state from DB on every turn.

Rejection is detected via keyword heuristics + optional LLM classifier (`REJECTION` / `NOT_REJECTION`). The `attempt_router` conditional edge routes messages to the appropriate node based on `attempt_number`, `is_rejection`, and `attempt2_substate`.

New files:
- `backend/app/session_utils.py` — all DB read/write for attempt state
- `backend/app/agents/attempt2_filters.py` — parse 4 filter answers from natural language
- `backend/app/agents/wellbeing.py` — wellbeing group detection + empathetic response framing
- `backend/app/org_utils.py` — `apply_attempt2_filters()` for Attempt 2 re-scoring

### Input

* Agent 6 match confidence / candidate count
* User responses to filter questions (Attempt 2)
* User wellbeing signal (Attempt 3)

### Output

* Attempt 1–2: Refined activity recommendations.
* Attempt 3: Empathetic, wellbeing-oriented response with no forced recommendation.
