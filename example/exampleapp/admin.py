from django.contrib import admin
from autogfk.admin import AutoGenericAdminMixin
from .models import ModelA, ModelB, ModelCRequired, Example

@admin.register(ModelA)
class ModelAAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name", "description")

@admin.register(ModelB)
class ModelBAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active", "score")
    search_fields = ("title",)

@admin.register(ModelCRequired)
class ModelCRequiredAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name", "description")

@admin.register(Example)
class ExampleAdmin(AutoGenericAdminMixin, admin.ModelAdmin):
    show_app_label_on_ct_field = False
    list_display = ("id", "field_a", "field_b", "field_c", "notes")
