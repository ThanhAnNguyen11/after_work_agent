# PART 4: AGENT RESPONSIBILITIES

## Agent 1 - Activity Recommendation

Input:

* User Profile
* Interests
* Participation History
* Available Activities

Output:

Recommended activities.

---

## Agent 2 - Activity Extraction

Input:

> Football at 18:00. Need 2 more players.

Output:

```json
{
  "activity_type": "football",
  "time": "18:00",
  "required_players": 2
}
```

The system automatically creates the activity.

---

## Agent 3 - Participation Collection

If yesterday's participation is unresolved:

Ask:

> What did you do yesterday evening?

Extract activity information and update participation history.
