# PART 4: AGENT CAPABILITIES

## Overview

The After Work Agent consists of multiple specialized capabilities.

Each capability has a clear purpose, trigger, input, and output.

The goal is to separate business responsibilities from communication style.

---

## Multi-turn Conversation

The agent maintains awareness of the current conversation context across multiple messages.

Conversation History is the list of messages exchanged in the current session (user and assistant turns).

Agents that use Conversation History must:

* Not repeat activities already recommended in the same session unless the user explicitly asks.
* Understand follow-up questions in context (e.g. "what about something else?" refers to the previous recommendation).
* Carry forward detected intent across turns unless the user signals a new intent.

---

## Agent 1 - Activity Recommendation

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

### Purpose

Understand what the user is currently looking for.

### Possible Intents

* Exercise
* Learning
* Networking
* Relaxation
* Exploration

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

### Purpose

Match activities with user interests, behavior, and intent.

### Input

* User Profile
* Participation History
* User Intent
* Available Activities
* Previously Recommended Activity IDs (current session)

### Output

Ranked activity candidates.

The recommendation agent uses these candidates to generate recommendations.

### Multi-turn Behavior

* Filter out activities that were already presented in the current session before scoring.
* If no new candidates remain after filtering, relax the filter and surface the top candidates again with a note that options are limited.
