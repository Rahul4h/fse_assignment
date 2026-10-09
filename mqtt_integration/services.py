import json
import hashlib
from datetime import datetime
from django.utils import timezone
from events.services import process_event
from events.models import MqttChallenge
from state.services import get_summary


CANDIDATE_ID = "17"


def handle_challenge(payload):
    challenge_id = payload.get('challenge_id')
    protocol_version = payload.get('protocol_version', '1.0')
    candidate_id = payload.get('candidate_id')
    command = payload.get('command')
    expires_at = payload.get('expires_at')
    events = payload.get('events', [])

    if candidate_id != CANDIDATE_ID:
        return build_error_response(challenge_id, "CANDIDATE_MISMATCH")

    if command != 'PROCESS_EVENTS':
        return build_error_response(challenge_id, "UNSUPPORTED_PROTOCOL")

    existing = MqttChallenge.objects.filter(challenge_id=challenge_id).first()
    if existing:
        return existing.serialized_result

    try:
        results = [process_event(e) for e in events]
    except Exception as exc:
        return build_error_response(challenge_id, "INTERNAL_ERROR")

    summary = get_summary()
    response = {
        "protocol_version": "1.0",
        "candidate_id": CANDIDATE_ID,
        "challenge_id": challenge_id,
        "status": "COMPLETED",
        "processed_at": timezone.now().isoformat(),
        "results": results,
        "state": {
            "net_total": summary['net_total'],
            "processed_events": summary['processed_events'],
            "pending_ack": summary['pending_ack'],
            "unresolved": summary['unresolved'],
            "duplicates": summary['duplicates'],
            "conflicts": summary['conflicts'],
            "rejected_submissions": summary.get('rejected_submissions', 0),
}
    }

    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    MqttChallenge.objects.create(
        challenge_id=challenge_id,
        request_digest=digest,
        serialized_result=response,
        received_at=timezone.now(),
        status='COMPLETED',
    )
    return response


def build_error_response(challenge_id, error_code):
    return {
        "protocol_version": "1.0",
        "candidate_id": CANDIDATE_ID,
        "challenge_id": challenge_id,
        "status": "FAILED",
        "error_code": error_code,
        "processed_at": timezone.now().isoformat(),
    }