# PART 2: ACTIVITY LIFECYCLE

## Activity Creation

Users can create activities and delete their activities

Example:

Football Match

* Time: 18:00
* Location: Field #3
* Need 2 more players

The system creates an activity record.

---

## Activity Capacity

Each activity contains:

* participant_limit
* current_participants

Example:

Football Match

* participant_limit = 10
* current_participants = 8

---

## Activity Guidelines

Each activity contains preparation information.

Examples:

### Football

* Bring football shoes
* Arrive 10 minutes early
* Field #3

### Yoga

* Bring a towel
* Arrive 5 minutes early

### AI Study Group

* Bring a laptop
* Topic: AI Agents

The user should understand what to expect before joining.

---

## Join Flow

When a user clicks Join:

1. Show activity details
2. Show activity guidelines
3. User confirms participation
4. Create participant record
5. Increase participant count
6. Notify activity host
7. Store participation history

---

## Host Notification

When a participant joins:

Notify the activity host.

Example:

> Nguyen Thanh An joined your Football Match.

---

## Activity Full Handling

When:

current_participants >= participant_limit

Then:

status = inactive

Inactive activities:

* Hidden from recommendations
* Cannot accept new participants
* Remain visible in history

Notify host:

> Football Match is now full.
