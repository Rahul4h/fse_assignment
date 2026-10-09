from django.db import transaction
from django.utils.dateparse import parse_datetime
import json
from datetime import datetime
from .models import ProductionEvent, SubmissionAttempt, ProductionSource


def _json_default(obj):
    """Convert non-JSON-serializable objects (like datetime) to strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def _make_json_safe(data):
    """Return a JSON-serializable copy of the input dict."""
    return json.loads(json.dumps(data, default=_json_default))


@transaction.atomic
def process_event(event_data):
    source_id = event_data.get('source_id')
    event_id = event_data.get('event_id')
    event_type = event_data.get('type')
    quantity = event_data.get('quantity')
    target_event_id = event_data.get('target_event_id')
    event_time_val = event_data.get('event_time')

    if not source_id or not event_id or not event_type or not event_time_val:
        return {"event_id": event_id or "UNKNOWN", "status": "REJECTED", "message": "Missing required fields"}

    if event_type not in ['COUNT', 'VOID']:
        return {"event_id": event_id, "status": "REJECTED", "message": "Invalid event type"}

    if event_type == 'COUNT':
     if not isinstance(quantity, int):
        SubmissionAttempt.objects.create(
            raw_payload=_make_json_safe(event_data),
            source_id=source_id, event_id=event_id,
            classification='REJECTED', error_reason='quantity must be an integer'
        )
        return {"event_id": event_id, "status": "REJECTED", "message": "quantity must be an integer"}

     if quantity < 1 or quantity > 500:
        SubmissionAttempt.objects.create(
            raw_payload=_make_json_safe(event_data),
            source_id=source_id, event_id=event_id,
            classification='REJECTED', error_reason='quantity must be between 1 and 500'
        )
        return {"event_id": event_id, "status": "REJECTED", "message": "quantity must be between 1 and 500"}

    if event_type == 'VOID' and not target_event_id:
        return {"event_id": event_id, "status": "REJECTED", "message": "VOID requires target_event_id"}

    # Handle both string and datetime objects (DRF Serializer returns datetime)
    if isinstance(event_time_val, str):
        event_time = parse_datetime(event_time_val)
    else:
        event_time = event_time_val

    if not event_time:
        return {"event_id": event_id, "status": "REJECTED", "message": "Invalid event_time format"}

    # Make event_data JSON-safe before storing in SubmissionAttempt.raw_payload
    safe_payload = _make_json_safe(event_data)

    ProductionSource.objects.get_or_create(source_id=source_id)

    existing = ProductionEvent.objects.filter(event_id=event_id).first()
    if existing:
        if (existing.type == event_type
                and existing.quantity == quantity
                and existing.target_event_id == target_event_id):
            SubmissionAttempt.objects.create(
                raw_payload=safe_payload,
                source_id=source_id,
                event_id=event_id,
                classification='DUPLICATE'
            )
            return {"event_id": event_id, "status": "DUPLICATE", "message": "Event already processed"}
        else:
            SubmissionAttempt.objects.create(
                raw_payload=safe_payload,
                source_id=source_id,
                event_id=event_id,
                classification='CONFLICT'
            )
            return {"event_id": event_id, "status": "CONFLICT", "message": "Same event_id, different data"}

    if event_type == 'COUNT':
        return _process_count(source_id, event_id, quantity, event_time, safe_payload)
    else:
        return _process_void(source_id, event_id, target_event_id, event_time, safe_payload)


def _process_count(source_id, event_id, quantity, event_time, event_data):
    event = ProductionEvent.objects.create(
        source_id=source_id, event_id=event_id, type='COUNT',
        quantity=quantity, event_time=event_time, status='ACCEPTED'
    )

    pending_voids = ProductionEvent.objects.filter(
        target_event_id=event_id, status='PENDING_REFERENCE', type='VOID'
    ).order_by('event_time')

    if pending_voids.exists():
        first_void = pending_voids.first()
        first_void.status = 'ACCEPTED'
        first_void.save()
        event.status = 'VOIDED'
        event.save()
        return {"event_id": event_id, "status": "ACCEPTED", "message": "COUNT accepted and voided by pending VOID"}

    return {"event_id": event_id, "status": "ACCEPTED", "message": "Event processed"}


def _process_void(source_id, event_id, target_event_id, event_time, event_data):
    target_event = ProductionEvent.objects.filter(event_id=target_event_id, type='COUNT').first()

    if target_event:
        already_voided = ProductionEvent.objects.filter(
            target_event_id=target_event_id, type='VOID', status='ACCEPTED'
        ).exists()
        if already_voided:
            SubmissionAttempt.objects.create(
                raw_payload=event_data,
                source_id=source_id,
                event_id=event_id,
                classification='REJECTED',
                error_reason='COUNT already voided'
            )
            return {"event_id": event_id, "status": "REJECTED", "message": "COUNT already voided"}

        ProductionEvent.objects.create(
            source_id=source_id, event_id=event_id, type='VOID',
            target_event_id=target_event_id, event_time=event_time, status='ACCEPTED'
        )
        return {"event_id": event_id, "status": "ACCEPTED", "message": "Void processed"}
    else:
        ProductionEvent.objects.create(
            source_id=source_id, event_id=event_id, type='VOID',
            target_event_id=target_event_id, event_time=event_time, status='PENDING_REFERENCE'
        )
        return {"event_id": event_id, "status": "PENDING_REFERENCE", "message": "Waiting for COUNT"}