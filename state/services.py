from django.db.models import Sum, Q
from events.models import ProductionEvent, SubmissionAttempt, SystemStatus


def get_summary(source_id=None):
    qs = ProductionEvent.objects.all()
    if source_id:
        qs = qs.filter(source_id=source_id)

    count_qs = qs.filter(type='COUNT', status='ACCEPTED')
    void_qs = qs.filter(type='VOID', status='ACCEPTED')

    total_count = count_qs.aggregate(total=Sum('quantity'))['total'] or 0

    total_void = 0
    for v in void_qs:
        target = ProductionEvent.objects.filter(event_id=v.target_event_id, type='COUNT').first()
        if target and target.quantity:
            total_void += target.quantity

    # ACK-aware counters (excluding DUPLICATE, CONFLICT, REJECTED)
    ack_eligible = qs.exclude(status__in=['DUPLICATE', 'CONFLICT', 'REJECTED'])

    total_ack = ack_eligible.count()
    acked_count = ack_eligible.filter(acknowledged_at__isnull=False).count()
    pending_count = ack_eligible.filter(acknowledged_at__isnull=True).count()

    # Audit-log-based counters (from SubmissionAttempt)
    attempts = SubmissionAttempt.objects.all()
    if source_id:
        attempts = attempts.filter(source_id=source_id)

    return {
        'net_total': total_count - total_void,
        'processed_events': count_qs.count() + void_qs.count(),
        'total_ack': total_ack,                                        # ACKED + Pending
        'acked': acked_count,                                          # যেগুলো ack হয়েছে
        'pending_ack': pending_count,                                  # যেগুলো pending
        'unresolved': qs.filter(status='PENDING_REFERENCE').count(),
        'conflicts': attempts.filter(classification='CONFLICT').count(),
        'rejected_submissions': attempts.filter(classification='REJECTED').count(),
    }


def get_pending(source_id=None):
    """
    Return events that are ready for acknowledgement.
    
    Per FSE-01 spec (page 4, section 6.2):
    - Successfully processed COUNT/VOID events that are not yet acknowledged
    - Plus PENDING_REFERENCE events (unresolved VOIDs)
    """
    qs = ProductionEvent.objects.filter(
        Q(status='ACCEPTED', acknowledged_at__isnull=True) |
        Q(status='VOIDED', acknowledged_at__isnull=True) |
        Q(status='PENDING_REFERENCE')
    )
    if source_id:
        qs = qs.filter(source_id=source_id)

    return list(qs.values(
        'event_id', 'source_id', 'type', 'target_event_id',
        'event_time', 'status', 'acknowledged_at'
    ))


def get_exceptions(source_id=None):
    qs = ProductionEvent.objects.filter(status__in=['REJECTED', 'CONFLICT'])
    if source_id:
        qs = qs.filter(source_id=source_id)
    return list(qs.values('event_id', 'source_id', 'type', 'status'))


def get_mqtt_status():
    try:
        status = SystemStatus.objects.get(key='mqtt_status')
        return status.value
    except SystemStatus.DoesNotExist:
        return 'OFFLINE'