# src/autogfk/polymorphic.py
from __future__ import annotations
from typing import Any
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q

# Reaproveitamos a lógica de reescrita dos lookups de GFK:
from .query import (
    AutoGenericForeignKeyManager,             # só para tipo/assinatura
    _rewrite_kwargs_to_q,
    _rewrite_q_obj,
)

try:
    from polymorphic.models import PolymorphicModel
    from polymorphic.query import PolymorphicQuerySet
    from polymorphic.managers import PolymorphicManager
except Exception as e:  # pragma: no cover
    raise ImproperlyConfigured(
        "django-polymorphic is required for autogfk.polymorphic. "
        "Install with: pip install django-polymorphic"
    ) from e


class AutoGFKRewriteMixin:
    """
    QuerySet mixin: rewrites filters on GenericForeignKey/AutoGenericForeignKey
    and then delegates to super() — to coexist with PolymorphicQuerySet (and others).
    """
    def _rewrite_args_kwargs(self, *args: Q, **kwargs: Any):
        q_gfk, rest = _rewrite_kwargs_to_q(self.model, kwargs)
        new_args = [_rewrite_q_obj(self.model, a) for a in args]
        if q_gfk.children:
            new_args.append(q_gfk)
        return new_args, rest

    def filter(self, *args, **kwargs):
        new_args, rest = self._rewrite_args_kwargs(*args, **kwargs)
        return super().filter(*new_args, **rest)

    def exclude(self, *args, **kwargs):
        new_args, rest = self._rewrite_args_kwargs(*args, **kwargs)
        return super().exclude(*new_args, **rest)

    def get(self, *args, **kwargs):
        new_args, rest = self._rewrite_args_kwargs(*args, **kwargs)
        return super().get(*new_args, **rest)


class AutoGFKPolymorphicQuerySet(AutoGFKRewriteMixin, PolymorphicQuerySet):
    """
    QuerySet polimórfico com reescrita de lookups de GFK/AutoGFK.
    MRO importa: nosso mixin vem primeiro para interceptar filter/exclude/get.
    """
    pass


class AutoGFKPolymorphicManager(PolymorphicManager):
    """
    Manager polimórfico que devolve o queryset acima.
    """
    queryset_class = AutoGFKPolymorphicQuerySet

    def get_queryset(self):
        return self.queryset_class(self.model, using=self._db)


class AutoGenericForeignKeyPolymorphicModel(PolymorphicModel):
    """
    Modelo base (abstract) combinando PolymorphicModel com suporte transparente
    a filtros em GFK/AutoGFK.
    """
    objects = AutoGFKPolymorphicManager()

    class Meta:
        abstract = True
