# PART 3: DATA MODEL

## User

> 🟡 Partial — core fields exist; `business_unit` and `group_name` stored under different column names; extended profile fields missing

* user_id ✅
* domain ✅
* password_hash ✅ (stored as `password` in DB)
* full_name ✅
* business_unit ❌ (stored as `title` in DB — not a BU code)
* group_name ❌ (stored as `company` in DB)
* org_group ✅ (extra field in DB, not in spec)
* department ✅
* squad ✅
* interests ✅
* created_at ✅

Example:

```json
{
  "domain": "annt7",
  "full_name": "Nguyen Thanh An",
  "business_unit": "PY",
  "group_name": "TEP",
  "department": "PCT",
  "squad": "Consumer Solutions",
  "interests": ["Football", "AI", "Movies"]
}
```

---

## Activity

> 🟡 Partial — most core fields exist; `host_department` missing; `activity_name` stored as `title`; status enum is narrower than spec

* activity_id ✅ (stored as `id`)
* activity_name ✅ (stored as `title`)
* activity_type ✅
* location_type (`on_campus` / `off_campus`) ✅
* difficulty ✅ (extra field — Beginner / Intermediate / Advanced / All Levels)
* host_user_id ✅
* host_department ❌
* start_time ✅
* end_time ✅ (extra field in DB, not in spec)
* location ✅
* participant_limit ✅
* current_participants ✅
* status 🟡 (exists, but only `active`/`inactive` — full enum not implemented)
* guidelines ✅
* description ✅ (extra field in DB, not in spec)
* created_at ✅

---

## Activity Participants

> ✅ Implemented (as `ActivityParticipant`)

* activity_id ✅
* user_id ✅
* joined_at ✅

---

## Participation History

> ✅ Implemented (as `UserExperience`)

* user_id ✅
* activity_id ✅ (also supports `gym_class_id` for fixed activities)
* participation_date ✅
* source (join / self_reported) ✅
* created_at ✅

---

## Extended User Fields (Onboarding v2)

> ❌ Not implemented — none of these fields exist in the DB

Additional fields collected during first-login onboarding:

* working_hours ❌ — user's typical availability windows (list of time slots)
* skills_to_learn ❌ — list of skills user wants to develop (self-growth dimension)
* date_of_birth ❌ — used to derive horoscope profile
* horoscope_sign ❌ — derived from date_of_birth (Western zodiac)
* horoscope_energy_state ❌ — current planetary energy applied at time of recommendation (e.g. `mercury_retrograde`, `full_moon`, `default`)

Example:

```json
{
  "working_hours": ["18:00-21:00 weekdays", "09:00-12:00 weekends"],
  "skills_to_learn": ["public speaking", "data analysis"],
  "date_of_birth": "1998-06-04",
  "horoscope_sign": "Gemini",
  "horoscope_energy_state": "mercury_retrograde"
}
```

---

## Activity Streak

> ❌ Not implemented — model does not exist in DB

* user_id ❌
* current_streak ❌ — consecutive weeks with at least 1 completed activity
* longest_streak ❌
* last_activity_week ❌ — ISO week string of last completed activity (e.g. "2026-W24")
* updated_at ❌

---

## User Badge

> ❌ Not implemented — model does not exist in DB

* badge_id ❌
* user_id ❌
* badge_type ❌ — one of: `EXPLORER` / `STREAK_3` / `STREAK_5` / `STREAK_10`
* earned_at ❌
* context ❌ — free text describing context (e.g. "First time at Yoga Studio")

---

## User Gamification

> ❌ Not implemented — model does not exist in DB

Aggregate gamification stats per user:

* user_id ❌
* connector_score ❌ — number of distinct BUs connected via completed activities
* host_karma ❌ — karma points earned as a host
* is_new_starter ❌ — boolean (true if user is within first 30 days on platform)
* new_starter_expires_at ❌ — date when New Starter Bonus expires

---

## Additional DB Models (Not in Spec)

The following models exist in `backend/app/models.py` but are not documented in this spec:

* **`Memory`** — stores per-user agent memory (used by LangGraph agent for conversational context)
* **`RecommendationLog`** — tracks which activities were shown to and joined by a user (recommendation audit trail)
* **`UserBehavioralInterest`** — derived interest tracking updated based on user activity participation patterns
* **`ParticipationJournal`** — journal prompts tied to participation follow-up feature
* **`Notification`** — user notifications
* **`FixedActivity`** — gym classes and other fixed-schedule activities (separate from user-created `Activity`)
* **`Session`** — auth tokens for user sessions
