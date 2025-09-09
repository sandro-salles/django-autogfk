# src/autogfk/widgets.py
from __future__ import annotations
from django import forms
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

class AutoGenericWidget(forms.MultiWidget):
    def __init__(self, model_admin, admin_site, *, limit_ct_qs=None, show_app_label=True, attrs=None):
        self.admin_site = admin_site
        self.model_admin = model_admin
        self.limit_ct_qs = limit_ct_qs
        self.show_app_label = show_app_label

        

        # 1º select = ContentType
        ct_widget = forms.Select(attrs={
            "class": "admin-autocomplete",
            "data-autogfk": "ct",
            "data-autogfk-show-app-label": "1" if show_app_label else "0",
        })
        qs = limit_ct_qs if limit_ct_qs is not None else ContentType.objects.all()
        ct_widget.choices = [("", "---------")] + [(ct.pk, self._ct_label(ct)) for ct in qs]

        # 2º select = objeto (preenchido por AJAX, mas vamos pré-popular no render se houver valor)
        obj_widget = forms.Select(attrs={
            "data-autocomplete-url": reverse("autogfk:autocomplete"),
            "class": "admin-autocomplete",
            "data-autogfk": "obj",
        })

        super().__init__([ct_widget, obj_widget], attrs)


    def _ct_label(self, ct):
        """Return label for ContentType respecting show_app_label flag."""
        try:
            model_cls = ct.model_class()
        except Exception:
            model_cls = None
        if self.show_app_label:
            return str(ct)
        else:
            return getattr(getattr(model_cls, "_meta", None), "verbose_name", None) or ct.model


    def decompress(self, value):
        # value pode vir como (ct_id, obj_id) OU dict {"content_type": <CT|id>, "object_id": id}
        if not value:
            return [None, None]
        if isinstance(value, dict):
            ct = value.get("content_type")
            ct_id = getattr(ct, "pk", ct)
            return [ct_id, value.get("object_id")]
        return [value[0], value[1]]

    # pré-popula o 2º select com o option selecionado
    def render(self, name, value, attrs=None, renderer=None):

        # normaliza
        ct_id = obj_id = None
        if isinstance(value, dict):
            ct = value.get("content_type")
            ct_id = getattr(ct, "pk", ct)
            obj_id = value.get("object_id")
        elif isinstance(value, (list, tuple)) and len(value) >= 2:
            ct_id, obj_id = value[0], value[1]

        # garante que o CT corrente esteja nas choices (caso o filtro tenha mudado)
        if ct_id:
            if all(str(ct_id) != str(v) for v, _ in self.widgets[0].choices):
                try:
                    ct = ContentType.objects.get(pk=ct_id)
                    self.widgets[0].choices = list(self.widgets[0].choices) + [(ct.pk, self._ct_label(ct))]
                except ContentType.DoesNotExist:
                    pass

        # se já tem (ct_id, obj_id), injeta a option selecionada no 2º select
        if ct_id and obj_id:
            try:
                model = ContentType.objects.get(pk=ct_id).model_class()
                if model is not None:
                    obj = model._default_manager.filter(pk=obj_id).first()
                    if obj is not None:
                        self.widgets[1].choices = [(obj.pk, str(obj))]  # <- option selected
            except Exception:
                # não interrompe o render por falhas pontuais
                pass

        return super().render(name, value, attrs=attrs, renderer=renderer)

    class Media:
        js = (
            "admin/js/vendor/select2/select2.full.js",
            "autogfk/autogfk.js",
        )
        css = {"all": ("admin/css/vendor/select2/select2.css", "autogfk/autogfk.css")}
