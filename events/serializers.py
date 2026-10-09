from rest_framework import serializers
from .models import ProductionEvent


class EventInputSerializer(serializers.Serializer):
    source_id = serializers.CharField(max_length=100)
    event_id = serializers.CharField(max_length=100)
    type = serializers.ChoiceField(choices=['COUNT', 'VOID'])
    quantity = serializers.IntegerField(required=False, allow_null=True)
    target_event_id = serializers.CharField(max_length=100, required=False, allow_null=True)
    event_time = serializers.DateTimeField()


class EventResultSerializer(serializers.Serializer):
    event_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField()


class ProductionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionEvent
        fields = '__all__'