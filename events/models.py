from django.db import models

# Create your models here.


class ProductionSource(models.Model):
    source_id = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.source_id

class ProductionEvent(models.Model):
    EVENT_TYPES = [('COUNT', 'COUNT'), ('VOID', 'VOID')]
    STATUS_CHOICES = [
        ('ACCEPTED', 'ACCEPTED'),
        ('PENDING_REFERENCE', 'PENDING_REFERENCE'),
        ('DUPLICATE', 'DUPLICATE'),
        ('CONFLICT', 'CONFLICT'),
        ('REJECTED', 'REJECTED'),
    ]

    source_id = models.CharField(max_length=100)
    event_id = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=EVENT_TYPES)
    quantity = models.IntegerField(null=True, blank=True)
    target_event_id = models.CharField(max_length=100, null=True, blank=True)
    event_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Requirement: Composite unique key on (source_id, event_id)
        unique_together = ('source_id', 'event_id')

    def __str__(self):
        return f"{self.source_id} - {self.event_id} ({self.status})"

class SubmissionAttempt(models.Model):
    raw_payload = models.JSONField()
    source_id = models.CharField(max_length=100, null=True, blank=True)
    event_id = models.CharField(max_length=100, null=True, blank=True)
    classification = models.CharField(max_length=50, null=True, blank=True)
    error_reason = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attempt: {self.event_id} - {self.classification}"

class MqttChallenge(models.Model):
    challenge_id = models.CharField(max_length=100, unique=True)
    request_digest = models.CharField(max_length=255)
    serialized_result = models.JSONField()
    received_at = models.DateTimeField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"Challenge: {self.challenge_id}"

class SystemStatus(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key} = {self.value}"
