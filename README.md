# 🏭 FSE Production Event Processing Dashboard

> Full Stack Engineering Practical Assessment — Production Event Processing Dashboard + MQTT Device Integration

A production-grade, function-based modular monolith that ingests factory COUNT/VOID events via **REST API** and **MQTT**, applies strict business rules, stores everything in **PostgreSQL**, and exposes a live responsive dashboard.

---

## 📚 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Setup](#-setup)
- [Running the Application](#-running-the-application)
- [REST API Reference](#-rest-api-reference)
- [MQTT Integration](#-mqtt-integration)
- [Business Rules](#-business-rules)
- [Automated Tests](#-automated-tests)
- [Frontend Dashboard](#-frontend-dashboard)
- [Database Schema](#-database-schema)
- [Change Request (FSE-01)](#-change-request-fse-01)
- [Assumptions](#-assumptions)
- [Author](#-author)

---

## ✨ Features

### Backend
- **Modular monolith** — one Django project, cleanly split into `events`, `state`, and `mqtt_integration` apps.
- **Single source of truth** — REST and MQTT both call the same `process_event()` function.
- **Event lifecycle** — COUNT / VOID / DUPLICATE / CONFLICT / PENDING_REFERENCE / REJECTED / VOIDED.
- **Quantity validation** — COUNT quantity must be an integer between **1 and 500** (Change Request FSE-01).
- **Idempotent MQTT challenges** — the same `challenge_id` is never processed twice.
- **Full audit trail** — every submission (including rejects) is stored in `SubmissionAttempt`.
- **Transaction safety** — batch events are wrapped in `@transaction.atomic`.

### Frontend
- Responsive single-file dashboard (mobile + desktop).
- Live summary cards (7 indicators).
- Source filter (LINE-01, etc.).
- Pending / Exceptions tabs.
- Bulk + single **Acknowledge** actions.
- MQTT connectivity indicator (ONLINE / OFFLINE).
- Submit event form (single or batch JSON).
- Auto-refresh every 5 seconds.

### MQTT
- Connects to a factory broker with QoS 1.
- Subscribes to `fse-01/{candidate_id}/challenge`.
- Publishes to `fse-01/{candidate_id}/response`.
- Publishes heartbeat to `fse-01/{candidate_id}/status` every 30 s.
- Automatic reconnect on disconnect.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Database | PostgreSQL (production) / SQLite (development) |
| MQTT | paho-mqtt (v3.1.1, QoS 1) |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Testing | Django TestCase + DRF APIClient |
| Version Control | Git + GitHub |

---

## 🏗️ Architecture
nfig/ # Django project root
├── manage.py
├── README.md
├── TECHNICAL_EXPLANATION.md
├── AI_USAGE.md
├── requirements.txt
├── .gitignore
│
├── config/ # Django settings package
│ ├── settings.py
│ ├── urls.py
│ ├── asgi.py
│ └── wsgi.py
│
├── events/ # Core event domain
│ ├── models.py # ProductionSource, ProductionEvent,
│ │ # SubmissionAttempt, MqttChallenge, SystemStatus
│ ├── services.py # process_event() — the heart of the app
│ ├── serializers.py
│ ├── views.py # POST /api/events
│ ├── urls.py
│ ├── admin.py
│ └── tests.py
│
├── state/ # Dashboard state
│ ├── services.py # get_summary(), get_pending(),
│ │ # get_exceptions(), get_mqtt_status()
│ ├── views.py # GET /api/state, POST /api/ack, GET /api/mqtt-status
│ ├── urls.py
│ └── tests.py
│
├── mqtt_integration/ # MQTT device integration
│ ├── services.py # handle_challenge()
│ ├── management/
│ │ └── commands/
│ │ └── mqtt_worker.py # python manage.py mqtt_worker
│ └── tests.py
│
└── templates/
└── dashboard/
└── index.html # Single-file responsive dashboard

text

---

## ✅ Prerequisites

- **Python** 3.11 or newer
- **pip** and **venv**
- **PostgreSQL** 14+ (for production)
- **Git**

---

## 🛠️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/fse_assignment.git
cd fse_assignment/config
2. Create and activate a virtual environment
bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
3. Install dependencies
bash
pip install -r requirements.txt
If requirements.txt is missing:

bash
pip install django djangorestframework psycopg2-binary paho-mqtt python-dotenv
pip freeze > requirements.txt
4. Configure the database
Option A — SQLite (quick start):

In config/settings.py:

python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
Option B — PostgreSQL (recommended):

python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'fse_db',
        'USER': 'postgres',
        'PASSWORD': '<your-password>',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
Create the database:

bash
psql -U postgres -c "CREATE DATABASE fse_db;"
5. Run migrations
bash
python manage.py makemigrations
python manage.py migrate
6. Create an admin user
bash
python manage.py createsuperuser
▶️ Running the Application
You need two terminals running simultaneously.

Terminal 1 — Django server
bash
python manage.py runserver
Dashboard → http://127.0.0.1:8000/

Admin panel → http://127.0.0.1:8000/admin/

REST API → http://127.0.0.1:8000/api/

Terminal 2 — MQTT worker
bash
python manage.py mqtt_worker
Expected output:

text
Connecting to 152.42.238.142:1883...
Connected with result code 0
Subscribed to challenge topic
🌐 REST API Reference
POST /api/events
Accepts one event object or a JSON array of events.

Single event:

json
{
  "source_id": "LINE-01",
  "event_id": "EV-101",
  "type": "COUNT",
  "quantity": 5,
  "event_time": "2026-10-09T10:30:00Z"
}
Batch:

json
[
  {
    "source_id": "LINE-01",
    "event_id": "EV-101",
    "type": "COUNT",
    "quantity": 5,
    "event_time": "2026-10-09T10:30:00Z"
  },
  {
    "source_id": "LINE-01",
    "event_id": "EV-102",
    "type": "VOID",
    "target_event_id": "EV-101",
    "event_time": "2026-10-09T10:35:00Z"
  }
]
Response:

json
{
  "results": [
    { "event_id": "EV-101", "status": "ACCEPTED", "message": "Event processed" },
    { "event_id": "EV-102", "status": "ACCEPTED", "message": "Void processed" }
  ]
}
Status codes: ACCEPTED, DUPLICATE, CONFLICT, PENDING_REFERENCE, REJECTED.

GET /api/state
Query parameters:

view — summary (default) | pending | exceptions

source_id — optional filter (e.g. LINE-01)

Example:

text
GET /api/state?view=summary&source_id=LINE-01
Response (view=summary):

json
{
  "net_total": 450,
  "processed_events": 3,
  "pending_ack": 2,
  "unresolved": 0,
  "duplicates": 0,
  "conflicts": 0,
  "rejected_submissions": 1
}
Response (view=pending):

json
{
  "pending": [
    {
      "event_id": "EV-200",
      "source_id": "LINE-01",
      "type": "VOID",
      "target_event_id": "EV-100",
      "event_time": "2026-10-09T10:30:00Z",
      "status": "PENDING_REFERENCE"
    }
  ]
}
Response (view=exceptions):

json
{
  "exceptions": [
    { "event_id": "EV-501", "source_id": "LINE-01", "type": "COUNT", "status": "REJECTED" }
  ]
}
POST /api/ack
Acknowledge one or more events.

Request:

json
{ "event_ids": ["EV-101", "EV-102"] }
Response:

json
{
  "results": [
    { "event_id": "EV-101", "status": "ACKED" },
    { "event_id": "EV-102", "status": "ALREADY_ACKED" }
  ]
}
Possible statuses: ACKED, ALREADY_ACKED, NOT_FOUND.

GET /api/mqtt-status
json
{ "status": "ONLINE" }
Possible values: ONLINE, OFFLINE.

📡 MQTT Integration
Setting	Value
Broker	152.42.238.142
Port	1883
Protocol	MQTT 3.1.1
QoS	1
Client ID	fse-01-{candidate_id}-worker
Candidate ID	17
Topics
Direction	Topic
Subscribe	fse-01/17/challenge
Publish	fse-01/17/response
Publish	fse-01/17/status
Challenge payload (from simulator)
json
{
  "protocol_version": "1.0",
  "candidate_id": "17",
  "challenge_id": "CH-7e1c4a42",
  "command": "PROCESS_EVENTS",
  "sent_at": "2026-10-09T10:45:00Z",
  "expires_at": "2026-10-09T10:45:15Z",
  "events": [
    {
      "source_id": "LINE-01",
      "event_id": "EV-101",
      "type": "COUNT",
      "quantity": 5,
      "target_event_id": null,
      "event_time": "2026-10-09T10:30:00Z"
    }
  ]
}
Response payload
json
{
  "protocol_version": "1.0",
  "candidate_id": "17",
  "challenge_id": "CH-7e1c4a42",
  "status": "COMPLETED",
  "processed_at": "2026-10-09T10:45:02Z",
  "results": [
    { "event_id": "EV-101", "status": "ACCEPTED", "message": "Event processed" }
  ],
  "state": {
    "net_total": 5,
    "processed_events": 1,
    "pending_ack": 1,
    "unresolved": 0,
    "duplicates": 0,
    "conflicts": 0,
    "rejected_submissions": 0
  }
}
Error codes: CANDIDATE_MISMATCH, UNSUPPORTED_PROTOCOL, CHALLENGE_EXPIRED, CHALLENGE_CONFLICT, VALIDATION_ERROR, INTERNAL_ERROR.

📏 Business Rules
COUNT
Adds its quantity only after successful processing.

Quantity must be an integer between 1 and 500 (Change Request).

A COUNT can be reversed only once.

VOID
Must reference an existing COUNT via target_event_id.

If the COUNT does not exist yet, the VOID is stored as PENDING_REFERENCE and resolved automatically when the COUNT arrives.

If multiple pending VOIDs target the same COUNT, the first stored valid VOID wins; the rest are rejected.

Duplicates
Same event_id + same normalized data → DUPLICATE (recorded, not reprocessed).

Same event_id + different data → CONFLICT (recorded, original preserved).

Transactions
Batches are wrapped in @transaction.atomic — the whole batch rolls back on failure.

unique_together = (source_id, event_id) prevents double counting at the DB level.

Order
Items in a batch are processed and returned in the order submitted.

An invalid item is REJECTED while valid items in the same batch still succeed.

🧪 Automated Tests
Run all tests:

bash
python manage.py test
Coverage:

Test	What it verifies
test_count_event_accepted	COUNT stored correctly
test_duplicate_event_no_double_counting	Duplicates do not double-count
test_void_before_count_pending_reference	PENDING → auto-resolved
test_repeated_acknowledgement	ACKED → ALREADY_ACKED
test_conflict_same_id_different_data	CONFLICT detected
test_state_summary_api	Summary returns correct values
test_quantity_exceeds_500	Change Request validation
test_quantity_less_than_1	Change Request validation
test_challenge_processed_once	MQTT challenge idempotency
test_candidate_mismatch	Wrong candidate rejected
🎨 Frontend Dashboard
Open http://127.0.0.1:8000/

Sections:

Header — MQTT status, Candidate ID, Source filter, Refresh.

Summary — 7 indicator cards:

Net Total

Processed

Pending Ack

Unresolved

Duplicates

Conflicts

Rejected Submissions (Change Request)

Tabs — Events | Pending | Exceptions.

Submit Event — JSON textarea + Submit button.

Actions:

Source filter — type LINE-01 to filter all views.

Acknowledge — single or bulk select on Pending tab.

Auto-refresh — summary every 5 s, MQTT status every 3 s.

🗄️ Database Schema
ProductionSource
Field	Type
source_id	CharField, unique
display_name	CharField, nullable
ProductionEvent
Field	Type
source_id	CharField
event_id	CharField
type	COUNT / VOID
quantity	Integer, nullable
target_event_id	CharField, nullable
event_time	DateTime
status	ACCEPTED / PENDING_REFERENCE / DUPLICATE / CONFLICT / REJECTED / VOIDED
acknowledged_at	DateTime, nullable
created_at	DateTime, auto
Constraint: unique_together = (source_id, event_id)

SubmissionAttempt
Field	Type
raw_payload	JSONField
source_id	CharField, nullable
event_id	CharField, nullable
classification	DUPLICATE / CONFLICT / REJECTED
error_reason	TextField, nullable
received_at	DateTime, auto
MqttChallenge
Field	Type
challenge_id	CharField, unique
request_digest	CharField
serialized_result	JSONField
received_at	DateTime
status	COMPLETED / FAILED
SystemStatus
Field	Type
key	CharField, unique
value	CharField
updated_at	DateTime, auto
🔄 Change Request (FSE-01)
The following features were added on top of the original assessment:

#	Feature	Location
01	COUNT quantity must be an integer in [1, 500] — else REJECTED	events/services.py
01	Rejected submissions recorded in PostgreSQL	SubmissionAttempt
01	REST + MQTT consistency preserved	same process_event()
02	New summary field rejected_submissions	state/services.py
02	Respects optional source_id filter	state/services.py
02	Includes MQTT response state object	mqtt_integration/services.py
03	Production Source Filter input	templates/dashboard/index.html
03	Applies to Summary / Pending / Exceptions	Frontend
03	Loading / empty / error states	Frontend
04	Rejected Submissions indicator card	Frontend
No rewrite was required — the modular monolith was extended, existing rules preserved.

💡 Assumptions
event_id is globally unique per source_id.

Server receipt time is authoritative for audit; device clocks may drift.

SQLite is used for quick development; PostgreSQL is the production target.

The MQTT simulator is trusted; challenge validity is enforced server-side.

The dashboard polls the API every few seconds; no WebSocket / SSE is used.

👤 Author
Rahul Ghosh
Candidate ID: 17
FSE-01 Full Stack Engineering Assessment


