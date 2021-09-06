import pytest
from django.urls import reverse


#test landing-login page
def test_signin(liveserver, client):
    url = 'icici.youtility.local:8000/'
    url2 = reverse('login')
    res = client.get(url)
    print(res.status_code)
    assert res.status_code == 200



def test_signin2(liveserver, client):
    url2 = reverse('login')
    res = client.get(url2)
    print(res.status_code)
    assert res.status_code == 200
