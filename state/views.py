from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .services import get_summary, get_pending, get_exceptions, get_mqtt_status
from events.models import ProductionEvent


@method_decorator(csrf_exempt, name='dispatch')
class StateView(APIView):
    def get(self, request):
        source_id = request.query_params.get('source_id')
        view = request.query_params.get('view', 'summary')

        if view == 'summary':
            return Response(get_summary(source_id))
        elif view == 'pending':
            return Response({"pending": get_pending(source_id)})
        elif view == 'exceptions':
            return Response({"exceptions": get_exceptions(source_id)})
        else:
            return Response({"error": "Invalid view"}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class AckView(APIView):
    def post(self, request):
        event_ids = request.data.get('event_ids', [])
        if not isinstance(event_ids, list):
            return Response({"error": "event_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for eid in event_ids:
            event = ProductionEvent.objects.filter(event_id=eid).first()
            if not event:
                results.append({"event_id": eid, "status": "NOT_FOUND"})
            elif event.acknowledged_at:
                results.append({"event_id": eid, "status": "ALREADY_ACKED"})
            else:
                event.acknowledged_at = timezone.now()
                event.save()
                results.append({"event_id": eid, "status": "ACKED"})

        return Response({"results": results}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class MqttStatusView(APIView):
    def get(self, request):
        return Response({"status": get_mqtt_status()})