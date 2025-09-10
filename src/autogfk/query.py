# src/autogfk/query.py
from __future__ import annotations
from typing import Any, Iterable, Tuple
from django.db import models
from django.db.models import Q
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured

try:
    from polymorphic.query import PolymorphicQuerySet
except Exception as e:  # pragma: no cover
    raise ImproperlyConfigured(
        "django-polymorphic is required for autogfk.polymorphic. "
        "Install with: pip install django-polymorphic"
    ) from e



def _gfk_map_for_model(model: type[models.Model]) -> dict[str, Tuple[str, str]]:
    """
    Maps <gfk_name> -> (ct_field_name, oid_field_name) for:
      - AutoGenericForeignKey (via model._autogfk_fields)
      - Native GenericForeignKey (via _meta.private_fields)
    """
    mapping: dict[str, Tuple[str, str]] = {}

    # AutoGenericForeignKey registers metadata here:
    auto = getattr(model, "_autogfk_fields", {}) or {}
    for name, meta in auto.items():
        mapping[name] = (meta["ct_field"], meta["oid_field"])

    # Native GFK lives in private_fields
    for f in getattr(model._meta, "private_fields", []):
        if isinstance(f, GenericForeignKey):
            mapping.setdefault(f.name, (f.ct_field, f.fk_field))

    return mapping


def _split_lookup(key: str) -> tuple[str, str]:
    # "field_a__in" -> ("field_a", "in"); "field_a" -> ("field_a","exact")
    parts = key.split("__", 1)
    if len(parts) == 1:
        return parts[0], "exact"
    return parts[0], parts[1]


def _normalize_obj(value: Any) -> tuple[ContentType, Any] | None:
    """
    Converts 'value' to (ContentType, object_id) or None.
    Accepts:
      - model instance
      - (ContentType|ct_id, object_id)
      - {"content_type": ct|id, "object_id": id}
      - None
    """
    if value is None:
        return None
    if isinstance(value, dict):
        ct = value.get("content_type")
        oid = value.get("object_id")
        if ct is None or oid is None:
            raise ValueError("Dict for GFK must contain 'content_type' and 'object_id'.")
        ct = ContentType.objects.get(pk=getattr(ct, "pk", ct))
        return ct, oid
    if isinstance(value, tuple) and len(value) == 2:
        ct, oid = value
        ct = ContentType.objects.get(pk=getattr(ct, "pk", ct))
        return ct, oid
    # model instance
    if isinstance(value, models.Model):
        ct = ContentType.objects.get_for_model(value)  # GenericForeignKey default: concrete model
        return ct, value.pk
    raise ValueError(f"Unsupported value for GFK lookup: {value!r}")


def _pairs_q(field: str, items: Iterable[Any], mapping: dict[str, Tuple[str, str]]) -> Q:
    """
    Builds Q with OR of pairs (ct=id & oid=id) for '__in'.
    """
    ct_field, oid_field = mapping[field]
    items = list(items)
    if not items:
        # empty should return empty set
        return Q(pk__in=[])  # force empty
    q = Q()
    for it in items:
        norm = _normalize_obj(it)
        if norm is None:
            # treat None inside __in as "empty": ct IS NULL AND oid IS NULL
            q |= Q(**{f"{ct_field}__isnull": True, f"{oid_field}__isnull": True})
        else:
            ct, oid = norm
            q |= Q(**{ct_field: ct, oid_field: oid})
    return q


def _rewrite_kwargs_to_q(model: type[models.Model], kwargs: dict[str, Any]) -> tuple[Q, dict[str, Any]]:
    """
    Separates kwargs into:
      - Q with conditions referring to rewritten GFKs
      - remaining kwargs (real fields)
    """
    mapping = _gfk_map_for_model(model)
    q = Q()
    rest: dict[str, Any] = {}
    for key, val in kwargs.items():
        field, lookup = _split_lookup(key)
        if field not in mapping:
            rest[key] = val
            continue

        ct_field, oid_field = mapping[field]

        if lookup in ("exact",):
            norm = _normalize_obj(val)
            if norm is None:
                q &= Q(**{f"{ct_field}__isnull": True, f"{oid_field}__isnull": True})
            else:
                ct, oid = norm
                q &= Q(**{ct_field: ct, oid_field: oid})

        elif lookup == "in":
            q &= _pairs_q(field, val, mapping)

        elif lookup == "isnull":
            truthy = bool(val)
            if truthy:
                q &= Q(**{f"{ct_field}__isnull": True, f"{oid_field}__isnull": True})
            else:
                q &= Q(**{f"{ct_field}__isnull": False, f"{oid_field}__isnull": False})

        else:
            raise NotImplementedError(
                f"Lookup '{lookup}' not supported for GenericForeignKey '{field}'. "
                "Supported: exact, in, isnull."
            )
    return q, rest


def _rewrite_q_obj(model: type[models.Model], expr: Q) -> Q:
    """
    Rewrites Q recursively, converting conditions on GFKs.
    """
    mapping = _gfk_map_for_model(model)
    # Q.children contains tuples (key, val) or nested Qs
    new_children = []
    for child in expr.children:
        if isinstance(child, Q):
            new_children.append(_rewrite_q_obj(model, child))
            continue
        key, val = child
        field, lookup = _split_lookup(key)
        if field not in mapping:
            new_children.append((key, val))
            continue

        ct_field, oid_field = mapping[field]
        if lookup in ("exact",):
            norm = _normalize_obj(val)
            if norm is None:
                new_children.append((f"{ct_field}__isnull", True))
                new_children.append((f"{oid_field}__isnull", True))
            else:
                ct, oid = norm
                new_children.append((ct_field, ct))
                new_children.append((oid_field, oid))
        elif lookup == "in":
            new_children.append(_pairs_q(field, val, mapping))
        elif lookup == "isnull":
            truthy = bool(val)
            new_children.append((f"{ct_field}__isnull", truthy))
            new_children.append((f"{oid_field}__isnull", truthy))
        else:
            raise NotImplementedError(
                f"Lookup '{lookup}' not supported for GenericForeignKey '{field}'. "
                "Supported: exact, in, isnull."
            )
    q2 = Q()
    q2.connector = expr.connector
    q2.negated = expr.negated
    q2.children = new_children
    return q2


class AutoGenericForeignKeyRewriteMixin:
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

    # --- write helpers: create/update families ---
    def _rewrite_payload_for_write(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Rewrites logical GFK assignments in a payload dict (for create/update/defaults)
        into their physical ct/oid fields. Does NOT modify the original dict.

        Accepts values as in filters: model instance, (ct|ct_id, oid), {content_type, object_id}, or None.
        """
        if not payload:
            return payload or {}
        mapping = _gfk_map_for_model(self.model)
        new_payload = dict(payload)
        for key in list(payload.keys()):
            if key not in mapping:
                continue
            ct_field, oid_field = mapping[key]
            norm = _normalize_obj(payload[key])
            if norm is None:
                new_payload[ct_field] = None
                new_payload[oid_field] = None
            else:
                ct, oid = norm
                new_payload[ct_field] = ct
                new_payload[oid_field] = oid
            # remove logical key
            new_payload.pop(key, None)
        return new_payload

    def create(self, **kwargs):
        kwargs2 = self._rewrite_payload_for_write(kwargs)
        return super().create(**kwargs2)

    def update(self, **kwargs):
        kwargs2 = self._rewrite_payload_for_write(kwargs)
        return super().update(**kwargs2)

    def get_or_create(self, defaults=None, **kwargs):
        # Rewrites both the lookup kwargs and the defaults payload
        new_args, lookup_rest = self._rewrite_args_kwargs(**kwargs)
        defaults2 = self._rewrite_payload_for_write(defaults or {})
        if new_args:
            # Narrow queryset first, then delegate to base implementation to avoid recursion
            narrowed = super().filter(*new_args, **lookup_rest)
            return models.QuerySet.get_or_create(narrowed, defaults=defaults2, **lookup_rest)
        # No Q args to apply; call base directly on self
        return super().get_or_create(defaults=defaults2, **lookup_rest)

    def update_or_create(self, defaults=None, **kwargs):
        new_args, lookup_rest = self._rewrite_args_kwargs(**kwargs)
        defaults2 = self._rewrite_payload_for_write(defaults or {})
        if new_args:
            narrowed = super().filter(*new_args, **lookup_rest)
            return models.QuerySet.update_or_create(narrowed, defaults=defaults2, **lookup_rest)
        return super().update_or_create(defaults=defaults2, **lookup_rest)

class AutoGenericForeignKeyQuerySet(AutoGenericForeignKeyRewriteMixin, models.QuerySet):
    pass


class AutoGenericForeignKeyPolymorphicQuerySet(AutoGenericForeignKeyRewriteMixin, PolymorphicQuerySet):
    """
    QuerySet polimórfico com reescrita de lookups de GFK/AutoGenericForeignKey.
    MRO importa: nosso mixin vem primeiro para interceptar filter/exclude/get.
    """
    pass
