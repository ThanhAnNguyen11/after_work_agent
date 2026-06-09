# PART 4: AGENT CAPABILITIES

## Overview

The After Work Agent consists of multiple specialized capabilities.

Each capability has a clear purpose, trigger, input, and output.

The goal is to separate business responsibilities from communication style.

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

### Output

* Recommended Activities

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

User messages.

### Output

Detected intent.

The detected intent should influence recommendations.

---

## Agent 6 - Activity Matching

### Purpose

Match activities with user interests, behavior, and intent.

### Input

* User Profile
* Participation History
* User Intent
* Available Activities

### Output

Ranked activity candidates.

The recommendation agent uses these candidates to generate recommendations.
