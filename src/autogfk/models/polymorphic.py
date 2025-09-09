from django.core.exceptions import ImproperlyConfigured
from ..managers import AutoGenericForeignKeyPolymorphicManager
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