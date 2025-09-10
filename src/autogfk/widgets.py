# src/autogfk/widgets.py
from __future__ import annotations
from django import forms
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
import json
class AutoGenericForeignKeyWidget(forms.MultiWidget):

    template_name = "autogfk/widgets/autogfk.html"

    def __init__(self, model_admin, admin_site, *, request=None, limit_ct_qs=None, show_app_label=True, attrs=None):
        self.admin_site = admin_site
        self.model_admin = model_admin
        self.request = request
        self.limit_ct_qs = limit_ct_qs
        self.show_app_label = show_app_label

        # Subwidgets “base”: dois Selects, com nossos data-attrs
        ct_widget = forms.Select(attrs={
            "class": "autogfk-select autogfk-content-type",
            "data-autogfk": "ct",
            "data-autogfk-show-app-label": "1" if show_app_label else "0",
        })
        obj_widget = forms.Select(attrs={
            "class": "autogfk-select autogfk-object-id",
            "data-autogfk": "obj",
            "data-autogfk-url": reverse("autogfk:autocomplete"),
            "data-autogfk-admin-root": reverse("admin:index"),
        })

        super().__init__([ct_widget, obj_widget], attrs)

        # Choices e metadados do CT (id→label e id→(app, model)) vão em data-attrs do select de CT
        qs = limit_ct_qs if limit_ct_qs is not None else ContentType.objects.all()
        # Ensure labels are plain strings (avoid lazy translation proxies)
        ct_pairs = [(ct.pk, str(self._ct_label(ct))) for ct in qs]
        self.widgets[0].choices = [("", "---------")] + ct_pairs
        self.widgets[0].attrs["data-autogfk-choices"] = json.dumps(ct_pairs)
        # Include permission flags (add/change/view) for the current user per CT
        self.widgets[0].attrs["data-autogfk-ctmap"] = json.dumps([
            [ct.pk, ct.app_label, ct.model, self._ct_perms(ct)] for ct in qs
        ])


    def _ct_perms(self, ct):
        """
        Returns a dict with permission flags for the current request.user:
        {"add": bool, "change": bool, "view": bool}
        """
        perms = {"add": False, "change": False, "view": False}
        req = getattr(self, "request", None)
        if not req:
            return perms
        try:
            model_cls = ct.model_class()
        except Exception:
            model_cls = None
        if not model_cls:
            return perms

        # Prefer ModelAdmin permission checks when the model is registered in admin
        admin = getattr(self.admin_site, "_registry", {}).get(model_cls)
        if admin is not None:
            try:
                perms["add"] = bool(admin.has_add_permission(req))
            except Exception:
                pass
            try:
                perms["change"] = bool(admin.has_change_permission(req))
            except Exception:
                pass
            try:
                hv = admin.has_view_permission(req)
                perms["view"] = bool(hv if hv is not None else (perms["change"]))
            except Exception:
                perms["view"] = perms["change"]
            return perms

        # Fallback to direct user perms when model is not registered in admin
        user = getattr(req, "user", None)
        if not user:
            return perms
        app = ct.app_label
        model = ct.model
        try:
            perms["add"] = user.has_perm(f"{app}.add_{model}")
            perms["change"] = user.has_perm(f"{app}.change_{model}")
            # view might not exist in very old setups; fallback to change
            perms["view"] = user.has_perm(f"{app}.view_{model}") or perms["change"]
        except Exception:
            # Be safe and keep defaults
            pass
        return perms


    def _ct_label(self, ct):
        """Return label for ContentType respecting show_app_label flag, always as str."""
        try:
            model_cls = ct.model_class()
        except Exception:
            model_cls = None
        if self.show_app_label:
            return str(ct)
        else:
            label = getattr(getattr(model_cls, "_meta", None), "verbose_name", None) or ct.model
            return str(label)


    def decompress(self, value):
        # value can come as (ct_id, obj_id) OR dict {"content_type": <CT|id>, "object_id": id}
        if not value:
            return [None, None]
        if isinstance(value, dict):
            ct = value.get("content_type")
            ct_id = getattr(ct, "pk", ct)
            return [ct_id, value.get("object_id")]
        return [value[0], value[1]]

    def value_from_datadict(self, data, files, name):
        """
        Lê os dois selects (name_0 e name_1) e volta ao formato (ct_id, obj_id).
        """
        return (data.get(f"{name}_0") or None, data.get(f"{name}_1") or None)

    def get_context(self, name, value, attrs):
        """
        Monta o contexto para o template: ct_widget + obj_widget prontos, cada um
        com seu id/name padrão (name_0 / name_1). Injeta a option selecionada
        no objeto quando (ct_id, obj_id) existem.
        """
        ct_id, obj_id = self.decompress(value)

        # Garante que o CT atual (se existir) está nas choices (caso o filtro tenha mudado)
        if ct_id and all(str(ct_id) != str(v) for v, _ in self.widgets[0].choices):
            try:
                ct = ContentType.objects.get(pk=ct_id)
                self.widgets[0].choices = list(self.widgets[0].choices) + [(ct.pk, self._ct_label(ct))]
            except ContentType.DoesNotExist:
                pass

        obj = None
        # Pré-carrega a option do objeto selecionado (para Select2 mostrar label)
        if ct_id and obj_id:
            try:
                model = ContentType.objects.get(pk=ct_id).model_class()
                if model is not None:
                    obj = model._default_manager.filter(pk=obj_id).first()
                    if obj is not None:
                        self.widgets[1].choices = [(obj.pk, str(obj))]
            except Exception:
                pass

        # Ids/names dos subwidgets
        attrs = attrs or {}
        base_id = attrs.get("id")  # ex.: id_field_a__autogfk
        attrs_ct = dict(attrs)
        attrs_obj = dict(attrs)
        if base_id:
            attrs_ct["id"] = f"{base_id}_0"
            attrs_obj["id"] = f"{base_id}_1"

        # Contextos individuais dos subwidgets (usam select.html do Django)
        ct_ctx = self.widgets[0].get_context(f"{name}_0", ct_id, attrs_ct)
        obj_ctx = self.widgets[1].get_context(f"{name}_1", obj_id, attrs_obj)

        ctx = super().get_context(name, value, attrs)
        ctx["widget"]["ct"] = ct_ctx["widget"]
        ctx["widget"]["obj"] = obj_ctx["widget"]
        # Opcional: flags auxiliares que o template pode usar
        ctx["widget"]["has_initial_ct"] = bool(ct_id)
        ctx["widget"]["has_initial_obj"] = bool(ct_id and obj_id)

        if bool(ct_id and obj_id):
            ctx["widget"]["data_href_template"] = f'/{obj._meta.app_label}/{obj._meta.model_name}/__fk__/change/?_to_field=id&_popup=1'
        return ctx

    class Media:
        js = ("autogfk/autogfk.js",)
        css = {"all": ("autogfk/autogfk.css",)}
