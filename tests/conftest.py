import pytest
from django.contrib.auth.models import User
from django.test import Client

@pytest.fixture
def admin_client(db):
    User.objects.create_superuser("admin", "a@b.c", "pass")
    c = Client()
    assert c.login(username="admin", password="pass")
    return c
