from __future__ import annotations
from django import forms
from django.urls import reverse

class AutoGenericWidget(forms.MultiWidget):
    def __init__(self, model_admin, admin_site, *, limit_ct_qs=None, attrs=None):
        self.admin_site = admin_site
        self.model_admin = model_admin
        ct_widget = forms.Select(attrs={"class": "admin-autocomplete"})
        obj_widget = forms.Select(attrs={
            "data-autocomplete-url": reverse("autogfk:autocomplete"),
            "class": "admin-autocomplete",
        })
        super().__init__([ct_widget, obj_widget], attrs)
        self.limit_ct_qs = limit_ct_qs

    def decompress(self, value):
        if not value:
            return [None, None]
        return [value[0], value[1]]

    class Media:
        js = (
            "admin/js/vendor/select2/select2.full.js",
            "autogfk/autogfk.js",
        )
        css = {"all": ("admin/css/vendor/select2/select2.css", "autogfk/autogfk.css")}
