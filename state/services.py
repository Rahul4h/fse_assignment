from django.db.models import Sum
from events.models import ProductionEvent, SystemStatus


def get_summary(source_id=None):
    from events.models import SubmissionAttempt

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

    # Rejected submissions count (from SubmissionAttempt, not from ProductionEvent)
    rejected_qs = SubmissionAttempt.objects.filter(classification='REJECTED')
    if source_id:
        rejected_qs = rejected_qs.filter(source_id=source_id)

    return {
        'net_total': total_count - total_void,
        'processed_events': count_qs.count() + void_qs.count(),
        'pending_ack': qs.filter(acknowledged_at__isnull=True).exclude(
            status__in=['DUPLICATE', 'CONFLICT', 'REJECTED']
        ).count(),
        'unresolved': qs.filter(status='PENDING_REFERENCE').count(),
        'duplicates': qs.filter(status='DUPLICATE').count(),
        'conflicts': qs.filter(status='CONFLICT').count(),
        'rejected_submissions': rejected_qs.count(),
    }


def get_pending(source_id=None):
    """
    Return events that are ready for acknowledgement.
    
    Per FSE-01 spec (page 4, section 6.2):
    - Successfully processed COUNT/VOID events that are not yet acknowledged
    - Plus PENDING_REFERENCE events (unresolved VOIDs)
    """
    from django.db.models import Q
    
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