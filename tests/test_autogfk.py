import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import Client
from tests.testapp.models import IntelligenceCredentials

@pytest.mark.django_db
def test_autocreate_fields():
    fields = [f.name for f in IntelligenceCredentials._meta.get_fields()]
    assert "owner_content_type" in fields
    assert "owner_object_id" in fields

@pytest.mark.django_db
def test_autocomplete_view(admin_client):
    # create a user to appear in autocomplete
    User.objects.create_user(username="alice", password="x")
    ct = ContentType.objects.get(app_label="auth", model="user")
    url = reverse("autogfk:autocomplete") + f"?ct={ct.pk}&q=ali"
    resp = admin_client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data and len(data["results"]) >= 1
