# evaluation.md

# After Work Agent - Model Evaluation Suite

## Purpose

This document is used to evaluate different models (qwen/qwen3-5-27b,google/gemma-4-31b-it) against the same scenarios.

Goals:

* Compare recommendation quality
* Compare grounding behavior
* Compare conversation quality
* Compare intent understanding
* Compare instruction following

---

# Evaluation Criteria

Each scenario should be scored from 1 to 5.

| Criteria                 | Description                     |
| ------------------------ | ------------------------------- |
| Grounding                | Uses only available information |
| Recommendation Quality   | Recommendations are relevant    |
| Intent Understanding     | Understands what the user wants |
| Natural Conversation     | Feels human and helpful         |
| Instruction Following    | Follows product rules           |
| Hallucination Resistance | Does not invent facts           |

Maximum Score:

30 points per scenario.

---

# Scenario 1 - Cold Start User

## Context

User Profile:

* Interests: Football, AI

Participation History:

* Empty

Available Activities:

* Football Match (2 slots left)
* AI Sharing Session
* Yoga Class

## User Message

What should I do tonight?

## Expected Behavior

* Acknowledge limited knowledge about user.
* Use interests and available activities.
* Do not invent participation history.
* Recommend existing activities only.

## Failure Examples

Bad:

"You usually play football every Tuesday."

Bad:

"You attended AI Sharing recently."

---

# Scenario 2 - Missing Participation Follow-up

## Context

User Profile:

* Interests: Football

Participation History:

* No record for yesterday

Available Activities:

* Football Match

## User Opens App

## Expected Behavior

Ask:

What did you do yesterday evening?

Do not immediately recommend activities.

## Failure Examples

Bad:

"Here are activities for tonight."

The agent ignored missing participation collection.

---

# Scenario 3 - Exercise Intent

## Context

Available Activities:

* Football Match
* Yoga Class
* AI Sharing Session

## User Message

I want to exercise tonight.

## Expected Behavior

Prioritize:

* Football
* Yoga

Do not prioritize AI Sharing.

---

# Scenario 4 - Learning Intent

## Context

Available Activities:

* Football Match
* Yoga Class
* AI Sharing Session

## User Message

I want to learn something new tonight.

## Expected Behavior

Prioritize:

* AI Sharing Session

Explain why it matches the user's intent.

---

# Scenario 5 - Relaxation Intent

## Context

Available Activities:

* Football Match
* Yoga Class
* Coffee Chat

## User Message

I'm feeling tired today.

## Expected Behavior

Recommend:

* Yoga
* Coffee Chat

Avoid recommending intense activities first.

---

# Scenario 6 - Activity Full

## Context

Available Activities:

* Football Match (FULL)
* Yoga Class

Football status:

inactive

## User Message

What should I do tonight?

## Expected Behavior

Do not recommend Football Match.

Recommend Yoga instead.

---

# Scenario 7 - User Wants New Experiences

## Context

User Interests:

* Football

Participation History:

* Football x10

Available Activities:

* Football Match
* AI Sharing Session
* Board Game Night

## User Message

I want to try something different.

## Expected Behavior

Encourage exploration.

Recommend:

* AI Sharing Session
* Board Game Night

Do not only recommend Football.

---

# Scenario 8 - Networking Intent

## Context

Available Activities:

* Football Match
* AI Sharing Session
* Coffee Chat

## User Message

I want to meet new people.

## Expected Behavior

Recommend activities with social interaction potential.

Explain networking benefits.

---

# Scenario 9 - User Opens App (Normal Case)

## Context

No unresolved participation.

Available Activities:

* Football Match
* AI Sharing Session

## Event

User opens application.

## Expected Behavior

Start a contextual conversation.

Examples:

* Looking for something to do tonight?
* Interested in discovering new activities?

Do not stay silent.

---

# Scenario 10 - Hallucination Test

## Context

User Profile:

* Interests: Football

Participation History:

* Empty

Available Activities:

* Yoga Class

## User Message

What should I do tonight?

## Expected Behavior

Recommend Yoga.

Do not invent:

* Football activities
* Past attendance
* User habits

This scenario is specifically designed to detect hallucinations.
