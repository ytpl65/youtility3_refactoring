import string

from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

from celery import shared_task

@shared_task
def create_random_user_accounts(total):
    for _ in range(total):
        print("task execution started...")
        username = f'user_{get_random_string(10, string.ascii_letters)}'
        email = f'{username}@example.com'
        password = get_random_string(50)
        User.objects.create_user(username=username, email=email, password=password)
    return f'{total} random users created with success!'


@shared_task
def add(x, y):
    import time
    time.sleep(10)
    return x+y