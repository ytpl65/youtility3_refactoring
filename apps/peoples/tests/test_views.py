import pytest
from django.urls import reverse

SERVER = "icici.youtility.local"
# test landing-login page
@pytest.mark.django_db(databases=['icici', 'default'])
def test_signin(client):
    url2 = reverse('login')
    res = client.get(url2, SERVER_NAME = "icici.youtility.local")
    print(res.status_code)
    assert res.status_code == 200

