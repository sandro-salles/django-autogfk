from django.contrib.contenttypes.models import ContentType
from django.db import models
from autogfk.fields import AutoGenericForeignKey
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Q

from autogfk.models import AutoGenericForeignKeyModel, AutoGenericForeignKeyPolymorphicModel
from autogfk.managers import AutoGenericForeignKeyManager

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


ALLOW_AB = Q(app_label="exampleapp", model__in=["modela", "modelb"])

class ExamplePlainGFK(models.Model):
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=ALLOW_AB,
        null=False, blank=False,
    )
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_content_type", "target_object_id")        


class ExampleInheriting(AutoGenericForeignKeyModel):
    # Usa AutoGenericForeignKey (auto cria ct/oid)
    field_a = AutoGenericForeignKey(
        null=True, blank=True,
        limit_choices_to=ALLOW_AB,
        label="A (auto)",
        related_name="inheriting_as_a",
    )

    # Mostra que o manager também entende GFK nativo no mesmo model (opcional)
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=ALLOW_AB,
        null=True, blank=True,
        related_name="inheriting_as_target",
    )
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("target_content_type", "target_object_id")

    notes = models.CharField(max_length=140, blank=True)

    class Meta:
        verbose_name = "Example (inherits base)"
        verbose_name_plural = "Examples (inherit base)"
        # índice composto opcional (acelera filtros por par ct/oid)
        indexes = [
            models.Index(fields=["field_a_content_type", "field_a_object_id"]),
            models.Index(fields=["target_content_type", "target_object_id"]),
        ]

class ExampleUsingManager(models.Model):
    # Só troca o manager
    objects = AutoGenericForeignKeyManager()

    # Pode usar tanto AutoGenericForeignKey…
    field_b = AutoGenericForeignKey(
        null=True, blank=True,
        limit_choices_to=ALLOW_AB,
        label="B (auto)",
        related_name="using_manager_as_b",
    )
    # …quanto GFK nativo
    owner_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=ALLOW_AB,
        null=True, blank=True,
        related_name="using_manager_as_owner",
    )
    owner_object_id = models.PositiveIntegerField(null=True, blank=True)
    owner = GenericForeignKey("owner_content_type", "owner_object_id")

    notes = models.CharField(max_length=140, blank=True)

    class Meta:
        verbose_name = "Example (manager only)"
        verbose_name_plural = "Examples (manager only)"
        indexes = [
            models.Index(fields=["field_b_content_type", "field_b_object_id"]),
            models.Index(fields=["owner_content_type", "owner_object_id"]),
        ]


class ExamplePoly(AutoGenericForeignKeyPolymorphicModel):
    field_a = AutoGenericForeignKey(
        null=True, blank=True,
        limit_choices_to=ALLOW_AB,
        label="A (auto)",
    )
    notes = models.CharField(max_length=140, blank=True)

class ExamplePolyChild(ExamplePoly):
    extra = models.CharField(max_length=50, blank=True)


class ExampleParentKind(models.TextChoices):
    MOTHER = "mother"
    FATHER = "father"

class ExampleParent(models.Model):
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=120, choices=ExampleParentKind.choices)


    field_b = AutoGenericForeignKey(
        null=True, blank=True,
        limit_choices_to=ALLOW_AB,
        label="B (auto)",
        related_name="parents_as_b",
    )
    class Meta:
        verbose_name = "Parent"
        verbose_name_plural = "Parents"


class ExampleChild(models.Model):
    age = models.IntegerField()
    parent = models.ForeignKey(ExampleParent, on_delete=models.CASCADE, related_name="children")

    field_a = AutoGenericForeignKey(
        null=True, blank=True,
        limit_choices_to=ALLOW_AB,
        label="A (auto)",
        related_name="children_as_a",
    )

    fk_b = models.ForeignKey(ModelB, on_delete=models.CASCADE, related_name="children_as_fk_b", null=True, blank=True)
    class Meta:
        verbose_name = "Child"
        verbose_name_plural = "Children"