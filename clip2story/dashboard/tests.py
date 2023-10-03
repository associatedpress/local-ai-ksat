import requests
import json

from django.test import TestCase

from .models import Recording

class RecordingTestCase(TestCase):
    transcript_id = None

    def setUp(self):
        self.transcript_id = <TRANSCRIPT_ID> #Not the best way to do this, but testing doesn't allow for keyword arguments


    def generate_transcript_complete_request(self):
        transcript_msg = {
            "eventType": 'TRANSCRIPT_COMPLETE',
            "transcriptId": self.transcript_id,
            "title": 'unimportant.mp4',
            "user": 'user@test.com',
            "metadata": 'some opaque metadata string' 
        }

        response = requests.post(url="http://127.0.0.1:8000/dashboard/transcript_msg_receiver", data=json.dumps(transcript_msg))
        self.assertIn(response.text, "Database entry found, status text updated and potentially the transcript is as well")
    
    def generate_transcript_verified_request(self):
        transcript_msg = {
            "eventType": 'TRANSCRIPT_VERIFIED',
            "transcriptId": self.transcript_id,
            "title": 'unimportant.mp4',
            "user": 'user@test.com',
            "metadata": 'some opaque metadata string' 
        }

        response = requests.post(url="http://127.0.0.1:8000/dashboard/transcript_msg_receiver", data=json.dumps(transcript_msg))

        self.assertIn(response.text, "Database entry found, status text updated and potentially the transcript is as well")
