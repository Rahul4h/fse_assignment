

# Register your models here.
from django.contrib import admin
from .models import ProductionSource, ProductionEvent, SubmissionAttempt, MqttChallenge


@admin.register(ProductionSource)
class ProductionSourceAdmin(admin.ModelAdmin):
    list_display = ('source_id', 'display_name')
    search_fields = ('source_id',)


@admin.register(ProductionEvent)
class ProductionEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'source_id', 'type', 'quantity', 'status', 'acknowledged_at', 'event_time')
    list_filter = ('type', 'status', 'source_id')
    search_fields = ('event_id', 'source_id', 'target_event_id')
    readonly_fields = ('created_at',)


@admin.register(SubmissionAttempt)
class SubmissionAttemptAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'source_id', 'classification', 'received_at')
    list_filter = ('classification',)


@admin.register(MqttChallenge)
class MqttChallengeAdmin(admin.ModelAdmin):
    list_display = ('challenge_id', 'status', 'received_at')