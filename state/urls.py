from django.urls import path
from .views import StateView, AckView, MqttStatusView

urlpatterns = [
    path('state', StateView.as_view(), name='state'),
    path('ack', AckView.as_view(), name='ack'),
    path('mqtt-status', MqttStatusView.as_view(), name='mqtt-status'),
]