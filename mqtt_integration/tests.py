from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from mqtt_integration.services import handle_challenge
from events.models import ProductionEvent, MqttChallenge


class MqttChallengeTests(TestCase):
    def test_challenge_processed_once(self):
        """Test: Same challenge_id processed twice should NOT double count"""
        payload = {
            'protocol_version': '1.0',
            'candidate_id': '17',
            'challenge_id': 'CH-TEST-001',
            'command': 'PROCESS_EVENTS',
            'events': [{
                'source_id': 'LINE-01',
                'event_id': 'EV-MQTT-001',
                'type': 'COUNT',
                'quantity': 3,
                'event_time': '2026-10-09T10:30:00Z',
            }],
        }
        first = handle_challenge(payload)
        second = handle_challenge(payload)

        self.assertEqual(first['status'], 'COMPLETED')
        self.assertEqual(second['challenge_id'], 'CH-TEST-001')
        # Only one event should exist
        self.assertEqual(ProductionEvent.objects.filter(event_id='EV-MQTT-001').count(), 1)
        self.assertEqual(MqttChallenge.objects.filter(challenge_id='CH-TEST-001').count(), 1)

    def test_candidate_mismatch(self):
        """Test: Wrong candidate_id returns CANDIDATE_MISMATCH"""
        payload = {
            'protocol_version': '1.0',
            'candidate_id': '999',
            'challenge_id': 'CH-TEST-002',
            'command': 'PROCESS_EVENTS',
            'events': [],
        }
        result = handle_challenge(payload)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['error_code'], 'CANDIDATE_MISMATCH')