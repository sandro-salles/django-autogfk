from django.contrib import admin
from autogfk.admin import AutoGenericAdminMixin
from .models import ModelA, ModelB, Example

@admin.register(ModelA)
class ModelAAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name", "description")

@admin.register(ModelB)
class ModelBAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active", "score")
    search_fields = ("title",)

@admin.register(Example)
class ExampleAdmin(AutoGenericAdminMixin, admin.ModelAdmin):
    list_display = ("id", "field_a", "field_b", "notes")
