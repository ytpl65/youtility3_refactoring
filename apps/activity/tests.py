import pytest

# Create your tests here.

def add(a, b):
    return a + b

@pytest.mark.django_db
def test_add():
    assert add(1, 2) == 3
    assert add(1, 1) == 2
    assert add(1, 0) == 1
    assert add(1, -1) == 0

