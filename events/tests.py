from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from rest_framework.test import APIClient
from .models import ProductionEvent
from .services import process_event


class EventProcessingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_count_event_accepted(self):
        """Test 1: COUNT event should be accepted and total should be correct"""
        result = process_event({
            'source_id': 'LINE-01',
            'event_id': 'EV-001',
            'type': 'COUNT',
            'quantity': 5,
            'event_time': '2026-10-09T10:30:00Z',
        })
        self.assertEqual(result['status'], 'ACCEPTED')
        event = ProductionEvent.objects.get(event_id='EV-001')
        self.assertEqual(event.quantity, 5)
        self.assertEqual(event.status, 'ACCEPTED')

    def test_duplicate_event_no_double_counting(self):
        """Test 2: Same event twice should not double the count"""
        payload = {
            'source_id': 'LINE-01',
            'event_id': 'EV-002',
            'type': 'COUNT',
            'quantity': 5,
            'event_time': '2026-10-09T10:30:00Z',
        }
        first = process_event(payload)
        second = process_event(payload)
        self.assertEqual(first['status'], 'ACCEPTED')
        self.assertEqual(second['status'], 'DUPLICATE')
        # Only one event stored
        self.assertEqual(ProductionEvent.objects.filter(event_id='EV-002').count(), 1)

    def test_void_before_count_pending_reference(self):
        """Test 3: VOID before COUNT should be PENDING_REFERENCE then resolve"""
        void_result = process_event({
            'source_id': 'LINE-01',
            'event_id': 'EV-003-VOID',
            'type': 'VOID',
            'target_event_id': 'EV-003',
            'event_time': '2026-10-09T10:30:00Z',
        })
        self.assertEqual(void_result['status'], 'PENDING_REFERENCE')

        # Now COUNT arrives
        count_result = process_event({
            'source_id': 'LINE-01',
            'event_id': 'EV-003',
            'type': 'COUNT',
            'quantity': 5,
            'event_time': '2026-10-09T10:31:00Z',
        })
        self.assertEqual(count_result['status'], 'ACCEPTED')

        # VOID should now be ACCEPTED
        void_event = ProductionEvent.objects.get(event_id='EV-003-VOID')
        self.assertEqual(void_event.status, 'ACCEPTED')

    def test_repeated_acknowledgement(self):
        """Test 4: Acknowledging the same event twice returns ALREADY_ACKED"""
        process_event({
            'source_id': 'LINE-01',
            'event_id': 'EV-004',
            'type': 'COUNT',
            'quantity': 5,
            'event_time': '2026-10-09T10:30:00Z',
        })
        response = self.client.post('/api/ack', {'event_ids': ['EV-004']}, format='json')
        self.assertEqual(response.data['results'][0]['status'], 'ACKED')

        response = self.client.post('/api/ack', {'event_ids': ['EV-004']}, format='json')
        self.assertEqual(response.data['results'][0]['status'], 'ALREADY_ACKED')

    def test_conflict_same_id_different_data(self):
        """Test 5: Same event_id with different data should be CONFLICT"""
        process_event({
            'source_id': 'LINE-01',
            'event_id': 'EV-005',
            'type': 'COUNT',
            'quantity': 5,
            'event_time': '2026-10-09T10:30:00Z',
        })
        result = process_event({
            'source_id': 'LINE-01',
            'event_id': 'EV-005',
            'type': 'COUNT',
            'quantity': 10,  # different quantity
            'event_time': '2026-10-09T10:30:00Z',
        })
        self.assertEqual(result['status'], 'CONFLICT')

    def test_state_summary_api(self):
        """Test 6: State API returns correct summary"""
        process_event({
            'source_id': 'LINE-01',
            'event_id': 'EV-006',
            'type': 'COUNT',
            'quantity': 10,
            'event_time': '2026-10-09T10:30:00Z',
        })
        response = self.client.get('/api/state?view=summary')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['net_total'], 10)