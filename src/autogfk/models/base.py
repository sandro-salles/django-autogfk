from django.db import models
from ..managers import AutoGenericForeignKeyManager
from ..query import _gfk_map_for_model, _normalize_obj


class AutoGenericForeignKeyModel(models.Model):
    """
    Base model (abstract) that already exposes the GFK-compatible manager.
    """
    objects = AutoGenericForeignKeyManager()

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """
        Accept logical GFK assignments in constructor kwargs and translate them
        to the physical `<name>_content_type` and `<name>_object_id` fields.

        Supported values: model instance; (ct|ct_id, object_id); {content_type, object_id}; None.
        """
        if kwargs:
            mapping = _gfk_map_for_model(self.__class__)
            # Work on a copy of keys to allow popping while iterating
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
        """
        Ensure consistency of physical GFK fields before saving.
        This hook doesn't change normal Django behavior when the logical GFK
        descriptor is used (assigning a model instance). It only ensures that
        when either side is None, both are None, keeping the pair consistent.
        """
        mapping = _gfk_map_for_model(self.__class__)
        for _, (ct_field, oid_field) in mapping.items():
            ct_val = getattr(self, ct_field)
            oid_val = getattr(self, oid_field)
            if (ct_val is None) != (oid_val is None):
                # If one is None and the other is not, reset both to None to avoid partial pairs
                setattr(self, ct_field, None)
                setattr(self, oid_field, None)
        return super().save(*args, **kwargs)
