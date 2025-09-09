from __future__ import annotations
from typing import Optional
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
_SENTINEL = object()
class AutoGenericForeignKey(GenericForeignKey):
    """
    GenericForeignKey with auto-creation of auxiliary fields and metadata for Admin.
    Validation rules:
    - If `ct_field` is provided, `oid_field` must also be provided (and vice-versa).
    - If `ct_field`/`oid_field` are provided (custom fields), it is NOT allowed
      to pass: `limit_choices_to`, `related_name`, `on_delete`, `null`, `blank`.
      These parameters must be defined directly on the declared custom fields.
    - If there is NO `ct_field`/`oid_field` (auto mode), the field will create:
        * <name>_content_type = FK(ContentType, on_delete=..., limit_choices_to=...)
        * <name>_object_id   = PositiveIntegerField(null/blank=...)
      and will propagate the parameters mentioned above.
    """
    def __init__(
            self,
        ct_field: Optional[str] = None,
        oid_field: Optional[str] = None,
        *,
        null: bool = False,
        blank: bool = False,
        limit_choices_to: Optional[object] = None,
        related_name: Optional[str] = None,
        on_delete: Optional[object] = None,
        label: Optional[str] = None,
    ) -> None:
        # ct/oid pairing rules
        if (ct_field is None) ^ (oid_field is None):
            raise ImproperlyConfigured(
                "AutoGenericForeignKey: if you provide ct_field or oid_field, you must provide BOTH."
            )
        self._user_ct_field = ct_field
        self._user_oid_field = oid_field
        self._owns_fields = ct_field is None and oid_field is None
        # Validations when user declares custom fields
        if not self._owns_fields:
            forbidden = {}
            if limit_choices_to is not None:
                forbidden["limit_choices_to"] = limit_choices_to
            if related_name is not None:
                forbidden["related_name"] = related_name
            if on_delete is not None:
                forbidden["on_delete"] = on_delete
            if null is not False:
                forbidden["null"] = null
            if blank is not False:
                forbidden["blank"] = blank
            if forbidden:
                raise ImproperlyConfigured(
                    "AutoGenericForeignKey: when using custom ct_field/oid_field, do NOT pass these "
                    f"options on the AutoGenericForeignKey constructor; define them on your custom fields instead: {list(forbidden.keys())}."
                )
        # Store options (for auto-created fields only)
        # cant use self.null and self.blank because they are ignored in the superclass constructor, so will always be False on contribute_to_class and deconstruct
        self._auto_null = bool(null)
        self._auto_blank = bool(blank)

        self.limit_choices_to = limit_choices_to if self._owns_fields else None
        self.related_name = related_name if self._owns_fields else None
        self.on_delete = on_delete if self._owns_fields else None
        self.label = label
        super().__init__(ct_field or "", oid_field or "")
    def deconstruct(self):
        path = f"{self.__class__.__module__}.{self.__class__.__name__}"
        # Export kwargs only as needed

        kwargs = {
            "ct_field": None if (self._user_ct_field is None) else self._user_ct_field,
            "oid_field": None if (self._user_oid_field is None) else self._user_oid_field,
            "null": self._auto_null,
            "blank": self._auto_blank,
        }
        if self._owns_fields:
            if self.limit_choices_to is not None:
                kwargs["limit_choices_to"] = self.limit_choices_to
            if self.related_name is not None:
                kwargs["related_name"] = self.related_name
            if self.on_delete is not None:
                kwargs["on_delete"] = self.on_delete
        if self.label:
            kwargs["label"] = self.label
        return (self.name, path, (), kwargs)
    def contribute_to_class(self, cls, name, private_only=False):
        ct_field_name = self._user_ct_field or f"{name}_content_type"
        oid_field_name = self._user_oid_field or f"{name}_object_id"
        if self._owns_fields:
            # Auto-creation of physical fields
            if not hasattr(cls, ct_field_name):
                ct_kwargs = {
                    "on_delete": self.on_delete or models.CASCADE,
                    "null": self._auto_null,
                    "blank": self._auto_blank,
                    "related_name": self.related_name,
                }
                if self.limit_choices_to is not None:
                    ct_kwargs["limit_choices_to"] = self.limit_choices_to
                # TIP: in some setups the autodetector is more stable seeing default=None when null=True
                if self._auto_null and "default" not in ct_kwargs:
                    ct_kwargs["default"] = None
                ct = models.ForeignKey(ContentType, **ct_kwargs)
                ct.contribute_to_class(cls, ct_field_name)
            if not hasattr(cls, oid_field_name):
                oid_kwargs = {
                    "null": self._auto_null,
                    "blank": self._auto_blank,
                    "db_index": True,
                }
                if self._auto_null and "default" not in oid_kwargs:
                    oid_kwargs["default"] = None
                oid = models.PositiveIntegerField(**oid_kwargs)
                oid.contribute_to_class(cls, oid_field_name)
        else:
            # Custom fields: ensure they EXIST
            try:
                cls._meta.get_field(ct_field_name)
                cls._meta.get_field(oid_field_name)
            except Exception as e:
                raise ImproperlyConfigured(
                    "AutoGenericForeignKey: custom ct_field/oid_field were provided but not found on the model. "
                    f"Declare both fields on the model: '{ct_field_name}' (FK to ContentType) and '{oid_field_name}' (object id)."
                ) from e
        # Configure the GFK itself
        self.ct_field = ct_field_name
        self.fk_field = oid_field_name
        self.model = cls
        self.name = name

        super().contribute_to_class(cls, name)
        # Metadata for Admin
        if not hasattr(cls, "_autogfk_fields"):
            cls._autogfk_fields = {}
        cls._autogfk_fields[name] = {
            "ct_field": ct_field_name,
            "oid_field": oid_field_name,
            "limit_choices_to": self.limit_choices_to,  # can be None for custom fields
            "label": self.label or name.replace("_", " ").title(),
        }