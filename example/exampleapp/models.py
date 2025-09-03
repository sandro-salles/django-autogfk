from django.db import models
from autogfk.fields import AutoGenericForeignKey

class ModelA(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ModelB(models.Model):
    title = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    score = models.IntegerField(default=0)

    def __str__(self):
        return self.title

# Exemplo com dois AutoGenericForeignKey distintos
OWNER_LIMIT_CHOICES_TO = {"app_label__in": ["exampleapp"]}

class Example(models.Model):
    field_a = AutoGenericForeignKey(
        null=True,
        blank=True,
        limit_choices_to=OWNER_LIMIT_CHOICES_TO,
        related_name="as_a",
        label="Field A",
    )
    field_b = AutoGenericForeignKey(
        null=True,
        blank=True,
        limit_choices_to=OWNER_LIMIT_CHOICES_TO,
        related_name="as_b",
        label="Field B",
    )
    notes = models.CharField(max_length=140, blank=True)
