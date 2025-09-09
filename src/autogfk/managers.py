# src/autogfk/managers.py
from __future__ import annotations
from django.db import models
from .query import AutoGenericForeignKeyQuerySet, AutoGenericForeignKeyPolymorphicQuerySet
from polymorphic.managers import PolymorphicManager


class AutoGenericForeignKeyManager(models.Manager.from_queryset(AutoGenericForeignKeyQuerySet)):
    """
    Manager that provides the QuerySet above.
    """
    pass



class AutoGenericForeignKeyPolymorphicManager(PolymorphicManager):
    """
    Manager polimórfico que devolve o queryset acima.
    """
    queryset_class = AutoGenericForeignKeyPolymorphicQuerySet

    def get_queryset(self):
        return self.queryset_class(self.model, using=self._db)


