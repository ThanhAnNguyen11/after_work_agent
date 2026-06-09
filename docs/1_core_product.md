# PART 1: CORE PRODUCT & FEATURES

## 1. Authentication & User Onboarding

## Authentication & Session Management

### Register

Users can create an account using:

* Domain
* Password

The domain must be unique.

After successful registration:

* User account is created.
* User proceeds to First Login Onboarding.

---

### Login

Users log in using:

* Domain
* Password

After successful login:

* Create authenticated session.
* Redirect user to the application.

---

### Session Persistence

Users should remain logged in across page refreshes and browser restarts.

The system should:

* Generate access token after login.
* Store session securely.
* Automatically restore session on application startup.

Users should not need to log in every time they open the application.

---

### Logout

When the user logs out:

* Clear session.
* Remove stored authentication token.
* Redirect to login page.

---

## First Login Onboarding

If the user logs in for the first time:

The system requires profile completion.

Required fields:

* Full Name
* Business Unit
* Group
* Department
* Squad (optional)

### Business Unit

Examples:

* PY
* ZA
* Game
* GreenNode
* Other

### Group

Examples:

* TEP
* BIZ
* OPS

### Department

Examples:

* PCT
* Data Platform
* Partnership
* Business

### Squad (Optional)

Examples:

* Consumer Solutions
* Flight Solutions
* Hotel Solutions

Users may leave this field empty if their department does not have squads.

---

## Interest Selection

During onboarding, users select interests.

### Sports

* Football
* Running
* Gym
* Badminton

### Learning

* AI
* Product
* English

### Entertainment

* Movies
* Board Games
* Coffee Chat

Users can select multiple interests.

These interests are only used as initial recommendation signals.

Over time, actual participation behavior should outweigh declared interests.

---

## 2. Activities Management

The system supports two activity sources.

### Fixed Activities

Configured by administrators.

Examples:

* Yoga
* Body Combat
* Zumba
* Running Club

### User Generated Activities

Created by employees.

Examples:

* Football at 18:00
* Boardgame Night
* AI Sharing Session

---

## 3. Activity Discovery

Users can:

* Browse activities
* Ask the agent:

  * What should I do tonight?
  * Any activities for AI enthusiasts?
  * Anything happening after work?

The agent recommends activities based on:

* Available activities
* User interests
* Participation history

---

## 4. Activity Cards

Each activity card contains:

* Activity Name
* Activity Type
* Time
* Location
* Host
* Remaining Slots
* Join Button

---

## 5. Participation Tracking

When a user joins an activity:

Store:

* User
* Activity
* Date
* Join Timestamp

This becomes participation history.

Participation history is later used to improve recommendations.

---

## 6. Participation Follow-up

If participation for a day has not been recorded:

Between:

* 21:00 on the same day
* 16:00 on the following day

When the user opens the application:

The agent asks:

> What did you do yesterday evening?

Possible responses:

* Joined recommended activity
* Joined another activity
* No activity

The answer is stored as participation history.

The same day must never be asked twice.

Hello World!
Lalala
hiiii
