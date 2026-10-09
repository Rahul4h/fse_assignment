# AI Usage Record

> FSE-01 | Production Event Processing Dashboard + MQTT Device Integration
>
> Candidate: **Rahul Ghosh** | Candidate ID: **17**

This document records how AI assistants were used during the assessment, as required by the FSE-01 submission guidelines (page 2, section 3).

---

## 📑 Table of Contents

- [1. AI Tools Used](#1-ai-tools-used)
- [2. How AI Was Used (by Phase)](#2-how-ai-was-used-by-phase)
- [3. Representative Prompts](#3-representative-prompts)
- [4. What Was Verified Manually](#4-what-was-verified-manually)
- [5. What Was NOT Delegated to AI](#5-what-was-not-delegated-to-ai)
- [6. Corrections Made to AI Output](#6-corrections-made-to-ai-output)
- [7. Declaration](#7-declaration)

---

## 1. AI Tools Used

| Tool | Role |
|---|---|
| **DeepSeek** | Architecture design, code scaffolding, bug fixing, documentation drafting |
| **ChatGPT (free tier)** | Occasional second opinions on DRF patterns and MQTT client configuration |

No paid enterprise tools were used. No proprietary code from any employer or third party was fed into any AI model.

---

## 2. How AI Was Used (by Phase)

### Phase 1 — Project Scaffolding
**Prompt:** "Give me a step-by-step Django project setup for a modular monolith with three apps: events, state, mqtt_integration. Include settings, models, and admin."

**Output used:**
- Django project skeleton (`config/`)
- `INSTALLED_APPS` structure
- `.gitignore` template
- Initial `ProductionSource`, `ProductionEvent`, `SubmissionAttempt`, `MqttChallenge` model drafts

**What I changed manually:**
- Added `SystemStatus` model (not suggested by AI).
- Adjusted `unique_together` to `(source_id, event_id)` to match the assessment's "globally unique event_id" wording.
- Added `acknowledged_at` and `created_at` fields.

---

### Phase 2 — Business Logic
**Prompt:** "Design a single `process_event()` function that handles COUNT, VOID, DUPLICATE, CONFLICT, and PENDING_REFERENCE, using `@transaction.atomic`."

**Output used:**
- Overall structure of `process_event` with early validation
- `_process_count` and `_process_void` helper function split
- Duplicate detection logic

**What I changed manually:**
- Added the `_make_json_safe` helper after hitting a `datetime is not JSON serializable` error in `SubmissionAttempt.raw_payload`.
- Reordered the pending-VOID resolution to sort by `event_time` (matches assessment spec).
- Changed the batch model: one transaction per event, not per batch (assessment page 3 requires "valid items in the same batch still succeed").
- Added the 1–500 quantity validation for the Change Request.

---

### Phase 3 — REST APIs
**Prompt:** "Write DRF APIViews for POST /api/events (single or array), GET /api/state (summary/pending/exceptions), and POST /api/ack."

**Output used:**
- Base APIView classes
- Serializer (`EventInputSerializer`)
- URL routing patterns

**What I changed manually:**
- Added `@method_decorator(csrf_exempt, name='dispatch')` after a 403 CSRF error during local testing.
- Ensured HTTP 200 is returned even when partial items are REJECTED (assessment page 4, section 6.1).
- Added the `rejected_submissions` field to `get_summary` for the Change Request.

---

### Phase 4 — MQTT Integration
**Prompt:** "Write a Django management command that connects to an MQTT broker at 152.42.238.142:1883, subscribes to fse-01/17/challenge, publishes to fse-01/17/response, and sends a HEARTBEAT every 30 seconds."

**Output used:**
- `paho-mqtt` client boilerplate
- `on_connect` / `on_message` / `on_disconnect` structure
- Heartbeat thread pattern

**What I changed manually:**
- Added `set_mqtt_status('ONLINE' | 'OFFLINE')` to write to `SystemStatus` — the AI did not suggest this, but it was necessary so the dashboard could reflect live connectivity.
- Added a duplicate-challenge check using `MqttChallenge.objects.filter(challenge_id=...)`.
- Verified QoS 1 on all subscribe/publish calls.
- Verified candidate_id check before processing.

---

### Phase 5 — Frontend Dashboard
**Prompt:** "Give me a single-file HTML dashboard that polls `/api/state` and displays summary cards, pending events, exceptions, and a submit form."

**Output used:**
- Base HTML/CSS skeleton
- Fetch + render pattern
- Tab switching logic

**What I changed manually:**
- Added the **7th summary card** (`Rejected Submissions`) for the Change Request.
- Added the **source filter input** that appends `&source_id=...` to every API call.
- Added **single and bulk Acknowledge** buttons (AI's first draft had no ack UI).
- Added a **toast notification** for ack feedback.
- Added `loadMqttStatus()` polling every 3 seconds.

---

### Phase 6 — Automated Tests
**Prompt:** "Write Django TestCase tests covering COUNT, duplicate, VOID pending, ack, conflict, and MQTT challenge idempotency."

**Output used:**
- Test class structure
- `APIClient` usage
- Assertion patterns

**What I changed manually:**
- Added a test for `quantity > 500 → REJECTED` (Change Request).
- Adjusted `event_time` strings to valid ISO 8601 with `Z` suffix.
- Verified each test's expected response status.

---

### Phase 7 — Documentation
**Prompt:** "Draft a professional README.md and TECHNICAL_EXPLANATION.md for this project."

**Output used:**
- Section headings and structure
- Table formatting

**What I changed manually:**
- Filled in exact function names, file paths, and line numbers where relevant.
- Verified every API example by running it against the live server.
- Wrote the "Assumptions" section in my own words based on real decisions made during coding.

---

## 3. Representative Prompts

Below are the actual prompts that drove the bulk of the work. They are paraphrased for brevity but capture the intent.

| # | Prompt |
|---|---|
| 1 | "Scaffold a Django project with three apps: events, state, mqtt_integration. Include settings.py, urls.py, and admin.py." |
| 2 | "Design a single service function `process_event()` that handles COUNT, VOID, DUPLICATE, CONFLICT, PENDING_REFERENCE with `@transaction.atomic`." |
| 3 | "Write DRF APIViews for POST /api/events, GET /api/state, POST /api/ack." |
| 4 | "Write a Django management command for an MQTT worker with heartbeat and reconnect." |
| 5 | "Build a single-file HTML dashboard that polls /api/state and shows summary cards." |
| 6 | "I'm getting `TypeError: Object of type datetime is not JSON serializable` when saving to a JSONField. How do I fix it?" |
| 7 | "I'm getting `403 Forbidden` on POST /api/events. The CSRF token is missing. How do I exempt API views?" |
| 8 | "I'm getting `TemplateView is not defined`. Where do I import it from?" |
| 9 | "Add a 1–500 quantity validation rule for COUNT events, returning REJECTED." |
| 10 | "Add a `rejected_submissions` field to the summary API and a corresponding card on the dashboard." |

---

## 4. What Was Verified Manually

Every AI-generated snippet was verified before committing. Specifically:

- **Every API endpoint was tested live** using the browser, `curl`, and the dashboard itself.
- **The MQTT worker was connected to the real broker** (`152.42.238.142:1883`) and produced `Connected with result code 0`.
- **All 10 automated tests pass** (`python manage.py test`).
- **The dashboard was manually clicked through** on both desktop and a narrow mobile viewport.
- **Every SQL-level constraint** (`unique_together`, `unique=True`) was verified by attempting to insert duplicate rows.
- **The batch ordering** was verified by submitting an array and inspecting the response order.
- **The 1–500 rule** was verified with COUNT 450 (ACCEPTED) and COUNT 501 (REJECTED).
- **The rejected counter** was verified to increment only on REJECTED, not on DUPLICATE or CONFLICT.

---

## 5. What Was NOT Delegated to AI

The following decisions were made without AI input:

- **Database schema** — which tables to create, what fields, what constraints.
- **Function boundaries** — which logic lives in `services.py` vs `views.py` vs `models.py`.
- **Choice of `unique_together = (source_id, event_id)`** — based on the assessment's "globally unique" wording.
- **The `SystemStatus` design** — a key-value table to bridge MQTT process state to REST reads.
- **The `MqttChallenge` idempotency design** — using SHA-256 digest of the incoming payload as a fingerprint.
- **The decision to keep one `process_event()` for both REST and MQTT** — the assessment's core architectural requirement.
- **The decision to reject (not silently drop) invalid COUNT quantities** — chosen for auditability.
- **The choice of candidate ID 17, MQTT topics, and REST routes** — spec-driven, not AI-driven.
- **The overall architecture** — function-based modular monolith; explicitly rejected microservices and message brokers.
- **All final code review** — no AI snippet was committed without reading and understanding every line.

---

## 6. Corrections Made to AI Output

Below are the concrete bugs and design issues that AI introduced and that were fixed manually.

| Issue | Cause | Fix |
|---|---|---|
| `TypeError: Object of type datetime is not JSON serializable` | DRF `DateTimeField` returns a Python `datetime`, which cannot be stored in `JSONField` directly | Added `_make_json_safe()` helper |
| `NameError: name 'TemplateView' is not defined` | AI's `urls.py` omitted the import | Added `from django.views.generic import TemplateView` |
| `403 Forbidden` on POST /api/events | Django CSRF middleware blocked the API | Added `@method_decorator(csrf_exempt, name='dispatch')` |
| `Unknown command: 'mqtt_worker'` | The management folder was named `command` (singular) | Renamed to `commands` and added `__init__.py` files |
| Batch transaction too coarse | AI wrapped the whole batch in one transaction | Changed to one transaction per event |
| Dashboard had no ack UI | AI's draft only showed read-only tables | Added single and bulk Ack buttons |
| No MQTT status on dashboard | AI did not consider cross-process state | Added `SystemStatus` model + `/api/mqtt-status` endpoint |

---

## 7. Declaration

I, **Rahul Ghosh (Candidate ID 17)**, declare that:

- AI tools were used as **assistants**, not as authors.
- Every line of committed code was **read, understood, and, where necessary, modified**.
- All business logic, architectural decisions, and database constraints were **chosen by me** based on the assessment requirements.
- No confidential or proprietary code from any third party was fed into any AI tool.
- The final submission represents my own understanding of the problem and my own engineering choices.

I am prepared to explain **any** function in this repository during a live walkthrough and to make changes on the spot if asked.

---

## 📌 Summary

| Question | Answer |
|---|---|
| Which AI tools? | DeepSeek (primary), ChatGPT (occasional) |
| How much code was AI-assisted? | Scaffolding, boilerplate, and initial drafts |
| How much was written by me? | All business logic, all architectural decisions, all fixes |
| Was every AI snippet verified? | Yes — live API tests, MQTT connection, automated tests, manual UI walkthrough |
| Would I have written it without AI? | Yes — AI sped up boilerplate; the design is mine |
| Will I explain it in a live interview? | Yes, line by line |