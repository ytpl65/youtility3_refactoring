import pytest
import warnings
from django.test import TestCase, Client

from django.urls import reverse

from apps.core.utils import save_user_session
from django.contrib.sessions.backends.db import SessionStore
import json
from apps.core.utils import basic_user_setup




@pytest.mark.django_db  # Required for DB access
class TestAttendanceView(TestCase):
    def setUp(self):
        self.client = Client()
        self.request = basic_user_setup()
        self.client.login(**{'username':'testuser', 'password':'testpassword', 'timezone':330})
        self.url = reverse('attendance:attendance_view')
        session_data = dict(self.request.session)
        session = self.client.session
        session.update(session_data)
        session.save()

        
    def test_attendance_get_template(self):
        print(dict(self.client.session))
        response = self.client.get(self.url, data={'template':'true'})
        print(response.content)
        self.assertEqual(response.status_code, 200)
    
    def test_attendance_get_sos_template(self):
        response = self.client.get(self.url, data={'template':'sos_template'})
        self.assertEqual(response.status_code, 200)
    
    def test_attendance_action_sos_list_view(self):
        print(dict(self.client.session))
        params = json.dumps({'from':'2023-05-01', 'to':'2023-05-30'})
        response = self.client.get(self.url, data={'action':'sos_list_view', 'params':params})
        self.assertEqual(response.status_code, 200)
        
        
