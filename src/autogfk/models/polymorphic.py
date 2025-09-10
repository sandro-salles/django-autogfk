from django.core.exceptions import ImproperlyConfigured
from ..managers import AutoGenericForeignKeyPolymorphicManager
from ..query import _gfk_map_for_model, _normalize_obj
try:
    from polymorphic.models import PolymorphicModel
except Exception as e:  # pragma: no cover
    raise ImproperlyConfigured(
        "django-polymorphic is required for autogfk.polymorphic. "
        "Install with: pip install django-polymorphic"
    ) from e

class AutoGenericForeignKeyPolymorphicModel(PolymorphicModel):
    """
    Modelo base (abstract) combinando PolymorphicModel com suporte transparente
    a filtros em GFK/AutoGenericForeignKey.
    """
    objects = AutoGenericForeignKeyPolymorphicManager()

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        # Same logic as non-polymorphic base: accept logical GFK in kwargs
        if kwargs:
            mapping = _gfk_map_for_model(self.__class__)
            for key in list(kwargs.keys()):
                if key not in mapping:
                    continue
                ct_field, oid_field = mapping[key]
                norm = _normalize_obj(kwargs.pop(key))
                if norm is None:
                    kwargs[ct_field] = None
                    kwargs[oid_field] = None
                else:
                    ct, oid = norm
                    kwargs[ct_field] = ct
                    kwargs[oid_field] = oid
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        # Ensure no partial ct/oid pairs are persisted
        mapping = _gfk_map_for_model(self.__class__)
        for _, (ct_field, oid_field) in mapping.items():
            ct_val = getattr(self, ct_field)
            oid_val = getattr(self, oid_field)
            if (ct_val is None) != (oid_val is None):
                setattr(self, ct_field, None)
                setattr(self, oid_field, None)
        return super().save(*args, **kwargs)
