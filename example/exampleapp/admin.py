from django.contrib import admin
from autogfk.admin import AutoGenericForeignKeyAdminMixin, AutoGenericForeignKeyInlineAdminMixin
from .models import ExampleChild, ExampleInheriting, ExampleParent, ExamplePlainGFK, ExamplePoly, ExamplePolyChild, ExampleUsingManager, ModelA, ModelB, ModelCRequired, Example

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
class ExampleAdmin(AutoGenericForeignKeyAdminMixin, admin.ModelAdmin):
    # optional - controls if the CT select will show/hide the app_label
    show_app_label_on_ct_field = False
    list_display = ("id", "field_a", "field_b", "field_c", "notes")

@admin.register(ExamplePlainGFK)
class ExamplePlainGFKAdmin(AutoGenericForeignKeyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "target")
    # optional - controls if the CT select will show/hide the app_label
    show_app_label_on_ct_field = False

    # optional - controls if the widget is enabled for plain GenericForeignKey fields as well
    enable_plain_genericforeignkey = False


@admin.register(ExampleInheriting)
class ExampleInheritingAdmin(AutoGenericForeignKeyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "field_a", "target", "notes")
    # optional - controls if the CT select will show/hide the app_label
    show_app_label_on_ct_field = False

    # optional - controls if the widget is enabled for plain GenericForeignKey fields as well
    enable_plain_genericforeignkey = True

@admin.register(ExampleUsingManager)
class ExampleUsingManagerAdmin(AutoGenericForeignKeyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "field_b", "owner", "notes")
    # optional - controls if the CT select will show/hide the app_label
    show_app_label_on_ct_field = False

    # optional - controls if the widget is enabled for plain GenericForeignKey fields as well
    enable_plain_genericforeignkey = False


@admin.register(ExamplePoly)
class ExamplePolyAdmin(AutoGenericForeignKeyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "field_a", "notes")
    # optional - controls if the CT select will show/hide the app_label
    show_app_label_on_ct_field = False



@admin.register(ExamplePolyChild)
class ExamplePolyChildAdmin(AutoGenericForeignKeyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "field_a", "extra")



class ExampleChildInline(AutoGenericForeignKeyInlineAdminMixin, admin.StackedInline):
    model = ExampleChild
    extra = 1
    show_app_label_on_ct_field = False
    autocomplete_fields = ["fk_b"]  # opcional

@admin.register(ExampleParent)
class ExampleParentAdmin(AutoGenericForeignKeyAdminMixin, admin.ModelAdmin):
    inlines = [ExampleChildInline]

    fieldsets = [
        (None, {
            "fields": ["name", "kind"],
        }),
        ("Field B", {
            "fields": ["field_b"],
        }),
    ]

    