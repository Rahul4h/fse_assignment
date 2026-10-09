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
