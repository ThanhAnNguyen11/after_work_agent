# PART 3: DATA MODEL

## User

* user_id

* domain

* password_hash

* full_name

* business_unit

* group_name

* department

* squad

* interests

* created_at

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

* activity_id

* activity_name

* activity_type

* source (fixed / user_created)

* host_user_id

* host_department

* start_time

* location

* participant_limit

* current_participants

* status

* guidelines

* created_at

---

## Activity Participants

* activity_id
* user_id
* joined_at

---

## Participation History

* user_id
* activity_id
* participation_date
* source (join / self_reported)
* created_at
