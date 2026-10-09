from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import process_event
from .serializers import EventInputSerializer


@method_decorator(csrf_exempt, name='dispatch')
class EventIngestView(APIView):
    def post(self, request):
        data = request.data
        is_batch = isinstance(data, list)
        events = data if is_batch else [data]

        if not isinstance(events, list) or len(events) == 0:
            return Response(
                {"error": "Invalid payload. Expected event or array of events."},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = []
        for ev in events:
            serializer = EventInputSerializer(data=ev)
            if serializer.is_valid():
                result = process_event(serializer.validated_data)
            else:
                result = {
                    "event_id": ev.get('event_id', 'UNKNOWN'),
                    "status": "REJECTED",
                    "message": str(serializer.errors)
                }
            results.append(result)

        return Response({"results": results}, status=status.HTTP_200_OK)