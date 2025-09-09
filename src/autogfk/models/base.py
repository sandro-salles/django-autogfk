from django.db import models
from ..managers import AutoGenericForeignKeyManager


class AutoGenericForeignKeyModel(models.Model):
    """
    Base model (abstract) that already exposes the GFK-compatible manager.
    """
    objects = AutoGenericForeignKeyManager()

    class Meta:
        abstract = True
