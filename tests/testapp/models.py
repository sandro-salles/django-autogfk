from django.db import models
from django.contrib.auth.models import User
from autogfk.fields import AutoGenericForeignKey

OWNER_LIMIT_CHOICES_TO = {"app_label__in": ["auth"]}

class IntelligenceCredentials(models.Model):
    owner = AutoGenericForeignKey(
        null=True,
        blank=True,
        limit_choices_to=OWNER_LIMIT_CHOICES_TO,
        related_name="intelligence_credentials",
        label="Dono",
    )
    label = models.CharField(max_length=50, default="cred")
