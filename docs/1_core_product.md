# PART 1: CORE PRODUCT & FEATURES

## Product Vision & Goals

**Product name:** ALPACA
**Platform:** Chat Agent on GreenNode AgentBase
**Target users:** All VNG Starters across subsidiaries at VNG Campus Q7, especially newly onboarding employees

**Vision:** Help Starters find activities before/after work hours to improve wellbeing and build cross-team connections. Use AI to record behavior and recommend the most suitable activities per Starter.

| Goal | Description |
|---|---|
| **Wellbeing** | Physical & mental health activities — gym, yoga, running, swimming |
| **Bonding** | Cross-team / cross-BU social connection — board games, coffee chat, football |
| **Mentality** | Learning, growth, skill-building — AI sessions, language study, public speaking |

Primary users: All VNG Starters at VNG Campus Q7. Focus: new onboarding employees (first 30 days on platform).

---

## 1. Authentication & Session Management

> ✅ Implemented

### Register

Users create an account using:

* Domain
* Password

The domain must be unique. After registration, user proceeds to First Login Onboarding.

### Login

Users log in using Domain + Password. After login, an authenticated session is created.

### Session Persistence

Users remain logged in across page refreshes and browser restarts.

* Access token generated after login.
* Session stored securely.
* Automatically restored on application startup.

### Logout

* Session cleared.
* Authentication token removed.
* Redirected to login page.

---

## 2. First Login Onboarding

### 2.1 Required Profile Fields

> ✅ Implemented

Required on first login:

* Full Name
* Business Unit (PY / ZA / Game / GreenNode / Other)
* Group (TEP / BIZ / OPS)
* Department (PCT / Data Platform / Partnership / Business)
* Squad — optional (Consumer Solutions / Flight Solutions / Hotel Solutions)

### 2.2 Interest Selection

> ✅ Implemented

Users select one or more interests across categories:

**Sports:** Badminton, Football, Running, Gym, Swimming, Taekwondo

**Learning:** AI, Product, English

**Entertainment:** Movies, Board Games, Coffee Chat, Karaoke

Declared interests are initial recommendation signals only. Over time, actual participation behavior outweighs them.

---

## 3. Activity Pool

> 🟡 Partial — browse, filter tabs, on-campus venue dropdown, and DB field all done; `location_type` not yet used as a recommendation signal

Activities come from two sources and two location types:

| | On-Campus | Off-Campus |
|---|---|---|
| **Platform-managed** | Fixed classes (Yoga, Body Combat, Zumba) — users JOIN only, cannot edit/delete | — |
| **User-created** | Starter books a campus venue (football field, badminton court, meeting room) | Starter proposes activity outside campus (dinner, hiking, coffee catch-up) |

The recommendation engine draws from all three groups simultaneously.

### On-Campus Platform Activities

Curated and managed by the platform. Users can JOIN but cannot modify or delete.

Examples: Gym classes, swimming pool, yoga studio, running club, rooftop events.

### On-Campus User-Created Activities

Created by Starters using a campus venue. Creator becomes the host and manages the activity.

Examples: Football match at Field #3, Badminton at Court B, AI sharing session in Meeting Room 5.

### Off-Campus User-Created Activities

Created by Starters for activities outside VNG campus. Creator becomes the host.

Examples: Dinner together, weekend hiking, learn Mandarin, coffee catch-up.

---

## 4. Activity Management

### 4.1 Activity Types

> ✅ Implemented

Two sources:

* **Fixed Activities** — configured by file (Yoga, Body Combat, Zumba, Running Club)
* **User-Generated Activities** — created by employees (Football at 18:00, Boardgame Night, AI Sharing Session)

### 4.2 Activity Cards

> ✅ Implemented

Each card shows: Activity Name, Activity Type, Time, Location, Host, Remaining Slots, Join Button, Difficulty badge (if set).

### 4.3 Create Activity

> ✅ Implemented

Any Starter can create an activity at any time.

Required fields: Activity name, Category (Wellbeing / Bonding / Mentality), Location type (On-campus / Off-campus), Date & time, Location, Max participants, Open to (same BU only / all VNG Starters).

* **On-campus** → Location field is a dropdown of campus venues (football field, badminton court, yoga studio, meeting rooms, etc.)
* **Off-campus** → Location field is free text

Optional fields: Difficulty level (Beginner / Intermediate / Advanced / All Levels).

### 4.4 Delete Own Activity

> ✅ Implemented — delete icon on card (own activities only)

---

## 5. Chat Sessions

> ✅ Implemented — stored in `localStorage`; no backend/DB persistence (clears on browser data clear)

Each conversation with the agent is a **session**. Users can:

* Start a **New Chat** — saves current session to Recents, clears conversation, fetches a fresh greeting
* View **Recent Sessions** — sidebar list of past sessions identified by first user message; click to restore full message history

Session data stored in `localStorage` under `aw_sessions_{USER_ID}`. Max 15 sessions; oldest dropped when limit exceeded.

---

## 6. Activity Discovery

> ✅ Implemented

Users can browse activities or ask the agent:

* "What should I do tonight?"
* "Any activities for AI enthusiasts?"
* "Anything happening after work?"

The agent recommends based on available activities, user interests, and participation history.

---

## 6. Recommendation Engine

### 6.1 Match Criteria

| Criterion | Status | Description |
|---|---|---|
| **Interest & Hobby Alignment** | ✅ | Based on onboarding interest tags; behavioral score gradually replaces declared interests after 3+ joined activities |
| **Participation History** | ✅ | Past joined activities used via `activity_relevance` ratio and `UserBehavioralInterest` behavioral score |
| **Chat History** | 🟡 | Memories extracted from past conversations fed to recommendation LLM + lightweight score boost (+0.1 / -0.1 per liked/disliked type) |
| **Query Keyword Match** | ✅ | When user explicitly names an activity type (e.g. "yoga", "bơi lội"), that activity type receives a +0.4 score boost — strong enough to override general scoring. Keyword → type mapping covers Vietnamese and English terms. |
| **Location Type Preference** | ✅ | Inferred from participation history — activities matching user's historically preferred location type (on/off-campus) receive a +0.1 score boost |
| **Weekend Context** | ✅ | On Saturday/Sunday, off-campus activities receive a +0.15 score boost; on-campus user-created activities are excluded from candidates (gym and swimming only) |
| **BU Preference** | ✅ | Activities with `open_to="same_bu"` are hidden from users outside that BU |
| **Time-Based Filtering** | ✅ | Activities that have already ended are excluded from candidates; 15-minute grace period for recently-started activities |
| **Fixed Activity Social Score** | ✅ | Gym/studio classes receive `social_connection = 0.3` baseline (neutral) since real participants exist but are not tracked in DB. Prevents systematic disadvantage in social-weighted scoring. |
| **Seniority Preference** | ❌ | Not implemented — no seniority data available |

### 6.2 Framing Principle

> ✅ Implemented — system prompt establishes curated, conversational framing; agent never dumps lists or exposes scores

Each recommendation set is a well-thought, curated selection — not a dump of options. The agent communicates that every Top 5 is the result of careful matching logic, to preserve perceived value and avoid the feeling of endless suggestions.

### 6.3 3-Attempt Matching Flow

> ✅ Implemented — `RecommendationSession` DB model tracks attempt state across stateless agent turns

If the user rejects all Top 5, the system transitions warmly into the next attempt with a bridging message.

**Attempt 1 — Full Profile Match**

* Run full match engine across all criteria
* Output Top 5 ranked activities with brief natural-language rationale per match
* If user selects one → Join flow
* If ALL 5 rejected → warm bridging message → Attempt 2
  * Example: *"Let me ask you a couple more things so I can find something that really fits you right now."*

**Attempt 2 — Personalized Filter Layer**

Agent asks 3–4 follow-up questions:

| Dimension | Example question |
|---|---|
| Energy level | "How's your energy right now — high, medium, or low?" |
| Social preference | "Do you feel like being around people or keeping it solo today?" |
| Environment | "Indoor or outdoor?" |
| Time available | "How much time do you have — 30 mins, 1–2 hours, or a full evening?" |
| Hobby angle | "Anything specific you've been wanting to try lately?" |

* Re-run match engine with filter answers applied
* Output new Top 5 (must differ from Attempt 1 set)
* If ALL 5 rejected → warm bridging message → Attempt 3

**Attempt 3 — Root Cause / Wellbeing Intervention**

Agent shifts tone: stops pushing activities, starts listening.

Opening: *"Sometimes when nothing feels right, there's usually something deeper going on. Mind if I ask you a few questions?"*

| Group | Symptoms | Psychology-Based Approach |
|---|---|---|
| 1. Work overload / Burnout | Too much on plate, no mental space | Gentle solo low-intensity (walking, light yoga) |
| 2. Social isolation | Feeling unseen, disconnected | Small familiar-BU group activity |
| 3. Career anxiety | Unsure of path, low motivation | Mentality/learning track with a senior Starter |
| 4. Physical fatigue | Body needs rest, not stimulation | Physical recovery (swimming, slow run) |
| 5. Emotional stress | Personal issues bleeding into work | Quiet creative or outdoor solo activity |

* Agent provides 2–3 short, empathetic pieces of advice
* Final Top 5 framed as: *"I think these might actually help with what you're going through."*
* If ALL 5 rejected → Pivot to Activity Creation

### 6.4 Weekend Rules

> ✅ Implemented

On Saturday and Sunday, the recommendation pipeline applies different rules:

- **Off-campus activities are prioritized** — user-created off-campus activities receive a +0.15 score boost
- **On-campus options are restricted** — user-created on-campus activities are excluded from candidates; only gym classes and swimming (platform-managed FixedActivities) remain available
- The agent leads with outdoor and social activities over structured on-campus sessions

### 6.5 Temporal Query Support

> 🟡 Partial — day detection works; one minor edge case remains ("tuần tới" parsing)

Users can ask about activities on specific future days. Supported formats:

| Input | Resolves to |
|---|---|
| "tomorrow" / "ngày mai" | next calendar day |
| "monday" … "sunday" | next occurrence of that weekday |
| "thứ 2" … "thứ 7" | Monday … Saturday (Vietnamese) |
| "chủ nhật" | Sunday (Vietnamese) |
| "cuối tuần" / "weekend" | coming Saturday |

When a specific day is detected, only activities scheduled on that day are shown.

**Known gaps:**

- **"tuần tới" not parsed separately** — "thứ 2" and "thứ 2 tuần tới" both resolve to the next occurrence of Monday (using `days_ahead <= 0 → +7` logic). If today is Monday, "thứ 2" correctly goes to next Monday. But if today is Thursday, "thứ 2 tuần này" (this week's already-passed Monday) and "thứ 2 tuần tới" (next Monday) both give the same result. In practice this is rarely a problem since past days are filtered out anyway.
- ~~No specific-day filter for gym classes in default case~~ — **fixed**: when no specific day is detected, gym classes are now filtered to today's weekday only.

### 6.6 Time-Based Candidate Filtering

> ✅ Implemented

The candidate pool is always filtered by current time before scoring:

- **Dynamic activities**: excluded if `end_time < now - 15 minutes`. The 15-minute grace period keeps recently-started activities visible so users can still join.
- **Fixed activities (gym classes, studio sessions)**: excluded if their `end_time` has passed on the current day. Classes on future weekdays are unaffected — a yoga class at 12:00–13:00 on Monday is still shown on Sunday even though "13:00" is before the current hour.

This ensures the agent never recommends activities the user can no longer attend.

### 6.7 Known Scoring Gaps

The following issues are identified as systematic — not one-off bugs — and require redesign of specific scoring or filtering rules before they are resolved:

| Gap | Root Cause | Status |
|---|---|---|
| **No query-keyword boost** | `user_intent` is coarse (exercise/learning/…). All subtypes score equally — yoga and badminton get identical weights when user says "yoga". | ✅ Fixed — `+0.4` boost for matched keywords |
| **Gym classes not filtered by today's weekday in default case** | `has_specific_day=False` path loads all active gym classes with no weekday restriction | ✅ Fixed — default case now filters to today's weekday |
| **LLM unaware of target day** | `target_day` is computed in `load_user_context` but not passed to the recommendation LLM prompt | ✅ Fixed — `target_day` passed through AgentState → user_prompt |
| **FixedActivity social_connection always 0** | No participant list exists for gym/studio classes in DB | ✅ Fixed — baseline `0.3` for gym classes |
| **`day_info` for gym classes = full weekday schedule** | Logged as `gc.weekday` ("Monday, Wednesday, Friday"), not the specific target day | ✅ Fixed — `day_info` now uses `effective_weekday` (the specific recommended day) |
| **"tuần tới" not distinguished from day name alone** | Temporal parser uses only `days_ahead <= 0 → +7`; does not detect "tuần tới" keyword | ❌ Out of scope — edge case affects only when today = target weekday |

---

**Post-Attempt-3 Fallback**

> "You know yourself best — maybe the perfect activity just doesn't exist yet. Why not create it? I'll help you set it up and find people who'd love to join."

User enters Activity Creation flow as host. Treated as a positive outcome, not a failure.

---

## 7. Participation Tracking

> ✅ Implemented

When a user joins an activity, the system stores: User, Activity, Date, Join Timestamp.

This becomes participation history, used to improve future recommendations.

---

## 8. Participation Follow-up

> ✅ Implemented

If participation for a day has not been recorded, between 21:00 on the same day and 16:00 on the following day, the agent asks:

> "What did you do yesterday evening?"

Responses: Joined recommended activity / Joined another activity / No activity.

The answer is stored as participation history. The same day is never asked twice.

---

## 9. Post-Match Connection Mechanic

> ❌ Not implemented — notifications exist but no icebreaker prompt or warm introduction message

After confirming participation, the system sends a warm notification to BOTH participant and host containing:

* A friendly message introducing both parties
* Each person's display name (internal domain)
* A light icebreaker prompt or fun fact about the shared activity

**Purpose:** Reduce the "who messages first" barrier and maximize the probability the activity actually happens in real life.

---

## 10. Reminder & Completion Tracking

> ❌ Not implemented — entire 5-touchpoint reminder sequence missing

| # | Trigger | Recipient | Message |
|---|---|---|---|
| 1 | Match confirmed + invite not sent within 2h | Both | Remind to send or accept invite |
| 2 | Day before activity, attendance not confirmed | Both | Confirm attendance reminder |
| 3 | Morning of activity day | Both | "Good luck / have fun" + check-in prompt |
| 4 | After expected end time | Both | Prompt to mark completed + emoji reaction |
| 5 | 3 days after activity | Participant | "Did you connect with [name] again?" → suggest next activity |

All reminders are conversational chat messages — not push notifications.

---

## 11. Stickiness & Incentive System

> ❌ Not implemented — no DB models, no logic for any gamification feature

No leaderboard in v1 — all incentives are personal and non-comparative.

| Incentive | Description | Milestone |
|---|---|---|
| **Activity Streak** | Consecutive weeks with at least 1 completed activity | Agent congratulates at 3, 5, 10-streak |
| **Explorer Badge** | Complete activity at a new on-campus location | One badge per new venue |
| **Connector Score** | +1 per activity completed with someone from a different BU | Shown as "Connected with N BUs" on profile |
| **Host Karma** | +1 each time a participant completes a host's activity | Unlocks priority access to popular on-campus slots |
| **New Starter Bonus** | First 30 days on platform | Double karma on all completed activities |

