# Technical Explanation

> FSE-01 | Production Event Processing Dashboard + MQTT Device Integration

This document explains **how and why** the system is built the way it is. It focuses on entity modeling, function ownership, transactional guarantees, and the reasoning behind each major design decision.

---

## 📑 Table of Contents

- [1. Entity Model](#1-entity-model)
- [2. Function Ownership](#2-function-ownership)
- [3. Why REST and MQTT Call the Same Service](#3-why-rest-and-mqtt-call-the-same-service)
- [4. Where Database Transactions Are Used](#4-where-database-transactions-are-used)
- [5. Duplicate Strategy](#5-duplicate-strategy)
- [6. Pending VOID Resolution](#6-pending-void-resolution)
- [7. Quantity Validation (Change Request)](#7-quantity-validation-change-request)
- [8. Rejected Submissions Tracking](#8-rejected-submissions-tracking)
- [9. Modularity and Future Migration](#9-modularity-and-future-migration)
- [10. Assumptions](#10-assumptions)
- [11. What a Live Walkthrough Would Cover](#11-what-a-live-walkthrough-would-cover)

---

## 1. Entity Model

Five tables model the domain. Each has a single responsibility.

### `ProductionSource`
Represents a physical production line (e.g., `LINE-01`).
- **Key:** `source_id` (unique)
- **Purpose:** Groups events by origin. Enables per-source filtering.

### `ProductionEvent`
The central fact table. One row = one COUNT or VOID action.
- **Key:** composite unique `(source_id, event_id)` — an `event_id` is globally unique per source.
- **Fields:**
  - `type` — `COUNT` or `VOID`
  - `quantity` — only for COUNT, integer 1–500
  - `target_event_id` — only for VOID
  - `event_time` — device-reported ISO 8601 timestamp
  - `status` — `ACCEPTED`, `PENDING_REFERENCE`, `DUPLICATE`, `CONFLICT`, `REJECTED`, `VOIDED`
  - `acknowledged_at` — set when a reviewer acknowledges the event
  - `created_at` — server receipt time (auto)

### `SubmissionAttempt`
An **append-only audit log**. Every submission — even duplicates, conflicts, and rejects — is stored here.
- **Why:** "Every step remains traceable" (assessment page 1). No history is ever deleted.
- **Fields:** `raw_payload` (JSON), `source_id`, `event_id`, `classification`, `error_reason`, `received_at`.

### `MqttChallenge`
Idempotency guard for MQTT challenges.
- **Key:** `challenge_id` (unique)
- **Purpose:** If the simulator resends the same `challenge_id`, the stored response is returned without reprocessing.
- **Fields:** `challenge_id`, `request_digest`, `serialized_result`, `received_at`, `status`.

### `SystemStatus`
A tiny key-value store for runtime flags.
- **Key:** `key` (unique)
- **Purpose:** Lets the MQTT worker (a separate OS process) publish its connectivity state to the database so the REST API and dashboard can read it.
- **Currently stores:** `mqtt_status` = `ONLINE` / `OFFLINE`.

---

## 2. Function Ownership

Each function has exactly one responsibility.

| Function | File | Owner of |
|---|---|---|
| `process_event(event_data)` | `events/services.py` | The entire COUNT/VOID business rule engine |
| `_process_count(...)` | `events/services.py` | COUNT acceptance and pending-VOID resolution |
| `_process_void(...)` | `events/services.py` | VOID acceptance, pending state, double-void rejection |
| `_make_json_safe(data)` | `events/services.py` | Converting datetime → ISO strings before JSONField storage |
| `get_summary(source_id)` | `state/services.py` | Aggregated read model for the dashboard |
| `get_pending(source_id)` | `state/services.py` | Listing unresolved VOIDs |
| `get_exceptions(source_id)` | `state/services.py` | Listing REJECTED / CONFLICT rows |
| `get_mqtt_status()` | `state/services.py` | Reading MQTT status from `SystemStatus` |
| `set_mqtt_status(value)` | `mqtt_integration/services.py` | Writing MQTT status to `SystemStatus` |
| `handle_challenge(payload)` | `mqtt_integration/services.py` | MQTT challenge orchestration (calls `process_event`) |

**Key insight:** The word "own" means "is the only place that logic lives." Changing a business rule in one place never requires editing a route or a handler.

---

## 3. Why REST and MQTT Call the Same Service

### The rule
Counting, voiding, deduplication, and conflict detection are **transport-agnostic**. A COUNT with quantity=5 means exactly the same thing whether it arrives over HTTP or MQTT.

### What we could have done (and didn't)
We could have written two separate handlers:
- one in `events/views.py` for REST
- one in `mqtt_integration/services.py` for MQTT

That would have been a **bug farm**: any rule change would need to be duplicated, and any drift would produce inconsistent behaviour.

### What we did
EST → EventIngestView.post() ┐
├──→ process_event() ──→ DB
MQTT → handle_challenge() → loop ┘

text

Both paths pass through **one** function. If we add a rule (say, "reject COUNT > 500"), it takes effect in REST, MQTT, and the MQTT simulator's expected response — automatically.

### Evidence in the code
- `events/views.py` calls `process_event(serializer.validated_data)`.
- `mqtt_integration/services.py` calls `process_event(e)` inside a loop.
- The MQTT response's `state` object is built with `get_summary()` — the same function used by `GET /api/state`.

---

## 4. Where Database Transactions Are Used

### `process_event()` — the atomic boundary

```python
@transaction.atomic
def process_event(event_data):
    ...
Every call to process_event is a single transaction. If any step inside raises, the whole call is rolled back.

Batch handling
EventIngestView loops over incoming events and calls process_event once per event. Each event is its own transaction. This means:

An invalid item is REJECTED while valid items in the same batch still succeed.

That is exactly what the assessment requires (page 3, section 5.2). If we had wrapped the entire batch in a single transaction, one bad item would roll back the whole batch — wrong behaviour.

Database-level constraints
Beyond application transactions, the database itself enforces:

unique_together = (source_id, event_id) on ProductionEvent — prevents double insertion even under concurrent requests.

unique=True on MqttChallenge.challenge_id — prevents duplicate challenge records.

unique=True on SystemStatus.key — one row per status key.

Where we did NOT use transactions
get_summary() and other read functions are read-only. They do not need @transaction.atomic.

5. Duplicate Strategy
When a new event arrives with an event_id that already exists for the same source_id, we compare its normalized data against the stored event.

Two outcomes
Condition	Result	What we do
Same type, same quantity, same target	DUPLICATE	Record in SubmissionAttempt, do not reprocess
Same type, different quantity or target	CONFLICT	Record in SubmissionAttempt, keep the original
Why this matters
Deduplication prevents double counting when a device retries after a network drop.

Conflict detection surfaces a real problem: two different devices claiming the same event_id with different data. The supervisor sees this in the Exceptions tab.

Audit safety: the original row is never overwritten.

Where the strategy lives
Duplicate / conflict checks are the first thing process_event() does after validation.

Both outcomes create a SubmissionAttempt row, so the dashboard's duplicates and conflicts counters can be derived.

6. Pending VOID Resolution
The problem
A VOID can arrive before its target COUNT (e.g., a network reorder). We must not drop the VOID.

The solution
When a VOID arrives and the target COUNT does not yet exist:

Store it as PENDING_REFERENCE.

Return PENDING_REFERENCE to the caller.

When a COUNT later arrives:

Insert the COUNT.

Query for pending VOIDs targeting this event_id.

Pick the first stored valid VOID (ordered by event_time).

Mark that VOID ACCEPTED and the COUNT VOIDED.

Handling multiple pending VOIDs
If three VOIDs target the same COUNT while it's still missing:

The first stored valid VOID wins.

The others are rejected with message = "COUNT already voided" and recorded in SubmissionAttempt.

Why ordering by event_time?
Because the assessment says: "If several pending VOID events target one COUNT, the first stored valid VOID wins." Using event_time (then insertion order as a tiebreaker via .first() on an ordered queryset) matches that rule.

Where it lives
Lookup and resolution: _process_count() in events/services.py.

Pending storage: _process_void() in events/services.py.

7. Quantity Validation (Change Request)
The new rule
A COUNT event must have an integer quantity between 1 and 500 (inclusive).

Where it's enforced
Immediately after the type check in process_event():

python
if event_type == 'COUNT':
    if not isinstance(quantity, int):
        # → REJECTED
    if quantity < 1 or quantity > 500:
        # → REJECTED
Why it's here and not in the serializer
Putting it in the serializer would leave the MQTT path unguarded. Because process_event() is the single source of truth, the rule applies to both transports automatically.

What happens on rejection
A SubmissionAttempt row is created with classification='REJECTED' and error_reason='quantity must be between 1 and 500'.

ProductionEvent is not created.

net_total is not incremented.

The API returns {"status": "REJECTED", "message": "quantity must be between 1 and 500"}.

The dashboard's rejected_submissions counter increments.

8. Rejected Submissions Tracking
The new field
GET /api/state?view=summary now returns a 7th field:

json
"rejected_submissions": 3
How it's computed
In state/services.py:

python
rejected_qs = SubmissionAttempt.objects.filter(classification='REJECTED')
if source_id:
    rejected_qs = rejected_qs.filter(source_id=source_id)
rejected_count = rejected_qs.count()
Why SubmissionAttempt and not ProductionEvent?
Because rejected items never create a ProductionEvent. They only exist as audit entries. This is the correct table to count them from.

What is excluded
DUPLICATE and CONFLICT classifications (they have their own counters).

PENDING_REFERENCE rows (tracked separately as unresolved).

Persistence
The value is read fresh from PostgreSQL/SQLite on every request. Nothing is cached, nothing is hardcoded.

9. Modularity and Future Migration
Current shape
Three Django apps, each self-contained:

App	Responsibility	Public surface
events	Domain model + business logic	process_event(), models
state	Read model + ack	get_summary(), ack_events()
mqtt_integration	Device I/O	handle_challenge()
Why this shape
Each app owns its own models.py, services.py, views.py.

Cross-app imports go through services.py, never through views.py.

Changing a rule in events/services.py does not require touching any view.

How we would split MQTT into a microservice
If load ever demanded it:

Keep events and state in the Django monolith.

Extract mqtt_integration into a standalone Python process.

The MQTT process would call POST /api/events on the monolith (or use a shared internal library).

No database is shared; the MQTT process only needs the challenge cache (MqttChallenge) if it stays local, or that too moves to the monolith.

Because the MQTT worker already calls the same process_event() function, the migration is a transport swap, not a rewrite.

What we deliberately avoided
Kafka, RabbitMQ, Redis, Celery.

A separate MQTT microservice.

Two databases.

Kubernetes.

The assessment explicitly says these are not required. Over-engineering would have hurt clarity.

10. Assumptions
Where the assessment was silent or ambiguous, we made these explicit choices:

event_id uniqueness is per source.
Enforced via unique_together = (source_id, event_id). Two different sources can have the same event_id independently.

Server receipt time is authoritative for audit.
event_time comes from the device; created_at comes from the server. Both are stored. For disputes, the server time wins.

Device clock drift is tolerated.
We do not reject events whose event_time is in the future or far in the past. The simulator's test data must be accepted.

The MQTT simulator is trusted to send well-formed JSON.
Malformed payloads are caught by exception handling in the worker, but we do not attempt to sanitize hostile input. This is a synthetic assessment environment.

challenge_id is globally unique.
Used as the primary deduplication key for MQTT challenges.

SQLite is acceptable for local development.
unique_together and JSON fields work identically in SQLite and PostgreSQL. Production uses PostgreSQL.

Acknowledgment is not idempotent for ALREADY_ACKED.
Repeating an ack returns ALREADY_ACKED but does not change the timestamp. This matches the spec.

The dashboard polls every 5 seconds.
No WebSocket. The assessment does not require real-time push.

source_id filtering is exact-match.
?source_id=LINE-01 matches LINE-01 exactly. No fuzzy matching.

Rejected COUNT does not create a ProductionEvent.
This preserves the "no double counting" rule and keeps net_total clean.

11. What a Live Walkthrough Would Cover
The examiner is expected to ask: "What is your entity model? Which function owns a COUNT? Why do REST and MQTT call the same service? Where are transactions used?"

A concise live answer:

Entity model — five tables, one row per domain fact; ProductionEvent is the fact table, SubmissionAttempt is the audit log.

Which function owns a COUNT — _process_count() inside events/services.py, called only from process_event().

Why REST and MQTT call the same service — to keep business rules in one place, prevent drift, and let new rules (like the 1–500 quantity rule) propagate automatically.

Where transactions are used — @transaction.atomic on process_event(); one transaction per event, not per batch, so valid items in a batch still succeed.

How to change a rule in one function — edit process_event() or _process_count(); REST, MQTT, and the dashboard pick it up without any other file changing.

How to demonstrate the rule change didn't break other modules — run python manage.py test; all tests still pass; hit POST /api/events and mqtt_worker manually to see the new behaviour.

📌 Summary
Concern	Where it lives	Why
Business rules	events/services.py::process_event	Single source of truth
Aggregations	state/services.py::get_summary	Read model, no duplication
MQTT orchestration	mqtt_integration/services.py::handle_challenge	Transport-specific, calls domain logic
Audit trail	SubmissionAttempt	Append-only, never deleted
Idempotency	MqttChallenge	Prevents challenge replay
Transaction boundary	@transaction.atomic on process_event	Per-event isolation
Duplicate / conflict	process_event pre-check	DB constraint + app-level check
Pending VOID	_process_count / _process_void	Auto-resolved when COUNT arrives
Quantity rule	process_event validation	Change Request FSE-01
Rejected counter	state/services.py::get_summary	Reads from SubmissionAttempt
Modularity	Three Django apps, services.py boundaries	Enables future microservice split
text





