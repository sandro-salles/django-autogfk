from __future__ import annotations
from typing import Optional
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class AutoGenericForeignKey(GenericForeignKey):
    """GenericForeignKey com auto-criação de campos auxiliares e metadados para o Admin."""

    def __init__(
        self,
        ct_field: Optional[str] = None,
        oid_field: Optional[str] = None,
        *,
        null: bool = False,
        blank: bool = False,
        limit_choices_to: Optional[dict] = None,
        related_name: Optional[str] = None,
        label: Optional[str] = None,
        on_delete: Optional[str] = None,
    ) -> None:
        self._auto_ct_field = ct_field
        self._auto_oid_field = oid_field
        self.null = null
        self.blank = blank
        self.limit_choices_to = limit_choices_to
        self.related_name = related_name
        self.label = label
        self.on_delete = on_delete
        super().__init__(ct_field or "", oid_field or "")

    def deconstruct(self):
        path = f"{self.__class__.__module__}.{self.__class__.__name__}"
        kwargs = {
            "ct_field": None if self.ct_field.startswith(self.name) else self.ct_field,
            "oid_field": None if self.fk_field.startswith(self.name) else self.fk_field,
            "null": self.null,
            "blank": self.blank,
        }
        if self.limit_choices_to:
            kwargs["limit_choices_to"] = self.limit_choices_to
        if self.related_name:
            kwargs["related_name"] = self.related_name
        if self.label:
            kwargs["label"] = self.label
        return (self.name, path, (), kwargs)

    def contribute_to_class(self, cls, name, private_only=False):
        ct_field = self._auto_ct_field or f"{name}_content_type"
        oid_field = self._auto_oid_field or f"{name}_object_id"

        if not hasattr(cls, ct_field):
            ct_kwargs = {
                "on_delete": self.on_delete or models.CASCADE,
                "null": self.null,
                "blank": self.blank,
                "related_name": self.related_name,
            }
            if self.limit_choices_to:
                ct_kwargs["limit_choices_to"] = self.limit_choices_to
            ct = models.ForeignKey(ContentType, **ct_kwargs)
            ct.contribute_to_class(cls, ct_field)

        if not hasattr(cls, oid_field):
            oid = models.PositiveIntegerField(null=self.null, blank=self.blank, db_index=True)
            oid.contribute_to_class(cls, oid_field)

        self.ct_field = ct_field
        self.fk_field = oid_field
        self.model = cls
        self.name = name

        super().contribute_to_class(cls, name, private_only)

        if not hasattr(cls, "_autogfk_fields"):
            cls._autogfk_fields = {}
        cls._autogfk_fields[name] = {
            "ct_field": ct_field,
            "oid_field": oid_field,
            "limit_choices_to": self.limit_choices_to,
            "label": self.label or name.replace("_", " ").title(),
        }
