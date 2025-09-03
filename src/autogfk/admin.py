from __future__ import annotations
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from .forms import AutoGenericFormField
from .widgets import AutoGenericWidget

class AutoGenericAdminMixin:
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        model = self.model
        if hasattr(model, "_autogfk_fields"):
            for name, meta in model._autogfk_fields.items():
                ct_field = meta["ct_field"]
                oid_field = meta["oid_field"]
                label = meta.get("label")

                ct_qs = ContentType.objects.all()
                if meta.get("limit_choices_to"):
                    ct_qs = ct_qs.filter(**meta["limit_choices_to"])

                class _F(form):
                    pass

                def _field_factory(initial=None):
                    f = AutoGenericFormField(label=label, required=False, limit_ct_qs=ct_qs)
                    f.widget = AutoGenericWidget(self, self.admin_site, limit_ct_qs=ct_qs)
                    if obj is not None:
                        ct_val = getattr(obj, ct_field + "_id", None)
                        oid_val = getattr(obj, oid_field, None)
                        f.initial = (ct_val, oid_val)
                    return f

                setattr(_F.base_fields, name, _field_factory())

                orig_save = _F.save
                def _save(self2, commit=True):
                    cleaned = self2.cleaned_data.get(name)
                    if cleaned:
                        ct = cleaned.get("content_type")
                        oid = cleaned.get("object_id")
                        setattr(self2.instance, ct_field, ct)
                        setattr(self2.instance, oid_field, oid)
                    return orig_save(self2, commit)
                _F.save = _save

                form = _F
        return form
