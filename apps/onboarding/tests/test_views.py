import pytest
from django.urls import reverse


SERVER = "icici.youtility.local"

@pytest.mark.django_db(databases=['icici', 'default'])
def test_ta_create(client):
    url = reverse('onboarding:ta_form')
    res = client.get(url, SERVER_NAME = SERVER)
    assert res.status_code == 200