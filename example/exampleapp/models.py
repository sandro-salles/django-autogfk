from django.contrib.contenttypes.models import ContentType
from django.db import models
from autogfk.fields import AutoGenericForeignKey
from django.db.models import Q

class ModelA(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Model A"
        verbose_name_plural = "Models A"

class ModelB(models.Model):
    title = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    score = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Model B"
        verbose_name_plural = "Models B"


class ModelCRequired(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Model C Required"
        verbose_name_plural = "Models C Required"

# example allowing only ModelA, ModelB and ModelCRequired
OWNER_LIMIT_CHOICES_TO = Q(app_label="exampleapp", model__in=["modela", "modelb", "modelcrequired"])

# example allowing only ModelCRequired
OWNER_LIMIT_CHOICES_TO_CUSTOM_C = Q(app_label="exampleapp", model__in=["modelcrequired"])

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

    # example customizing the names of content_type and object_id fields
    custom_c_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="as_c", limit_choices_to=OWNER_LIMIT_CHOICES_TO_CUSTOM_C)
    custom_c_object_id = models.PositiveIntegerField(db_index=True)
    
    field_c = AutoGenericForeignKey(
        label="Field C",
        ct_field="custom_c_content_type",
        oid_field="custom_c_object_id",
    )

    notes = models.CharField(max_length=140, blank=True)

    class Meta:
        verbose_name = "Example"
        verbose_name_plural = "Examples"