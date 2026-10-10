from django.urls import path
from .views import StateView, AckView, MqttStatusView, MqttLatestView, MqttHistoryView

urlpatterns = [
    path('state', StateView.as_view(), name='state'),
    path('ack', AckView.as_view(), name='ack'),
    path('mqtt-status', MqttStatusView.as_view(), name='mqtt-status'),
    path('mqtt-latest', MqttLatestView.as_view(), name='mqtt-latest'),
    path('mqtt-history', MqttHistoryView.as_view(), name='mqtt-history'),
]