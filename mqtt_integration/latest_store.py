"""
Thread-safe store for the latest MQTT challenge.
The MQTT listener writes here; the REST API reads from here.
"""
import threading
from datetime import datetime

_lock = threading.Lock()

_latest_challenge = {
    "challenge_id": None,
    "received_at": None,
    "payload": None,
    "status": None,
}

_history = []  # last N challenges
MAX_HISTORY = 20


def set_latest(challenge_id, payload, status="RECEIVED"):
    """Called by the MQTT listener when a new challenge arrives."""
    with _lock:
        _latest_challenge["challenge_id"] = challenge_id
        _latest_challenge["received_at"] = datetime.utcnow().isoformat() + "Z"
        _latest_challenge["payload"] = payload
        _latest_challenge["status"] = status

        _history.insert(0, {
            "challenge_id": challenge_id,
            "received_at": _latest_challenge["received_at"],
            "payload": payload,
            "status": status,
        })
        del _history[MAX_HISTORY:]


def get_latest():
    """Called by the REST API."""
    with _lock:
        return dict(_latest_challenge)


def get_history():
    with _lock:
        return list(_history)