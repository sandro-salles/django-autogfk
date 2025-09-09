from __future__ import annotations
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Q
from .forms import AutoGenericFormField
from .widgets import AutoGenericWidget

SURROGATE_SUFFIX = "__autogfk"


def _apply_limit_choices(qs, lct):
    """
    Accepts dict, Q or callable returning dict/Q.
    Also accepts lists/tuples of Q/dicts (does AND).
    """
    if lct is None:
        return qs
    if callable(lct):
        lct = lct()
    if isinstance(lct, Q):
        return qs.filter(lct)
    if isinstance(lct, dict):
        return qs.filter(**lct)
    if isinstance(lct, (list, tuple)):
        cond = Q()
        for item in lct:
            if callable(item):
                item = item()
            if isinstance(item, Q):
                cond &= item
            elif isinstance(item, dict):
                cond &= Q(**item)
        return qs.filter(cond) if cond else qs
    # fallback: don't apply if it's an unexpected type
    return qs

class AutoGenericAdminMixin:
    # Controls whether the CT select shows 'app_label | verbose_name' or only the model label
    show_app_label_on_ct_field = True    
    
    # Controls whether the widget is enabled for plain GenericForeignKey fields as well
    enable_widget_for_genericforeignkey = True

    def _discover_plain_gfk_specs(self):
        """
        Descobre GenericForeignKeys PUROS no model (sem ser AutoGenericForeignKey),
        e retorna um dict compatível com _autogfk_fields.
        """
        specs = {}
        model = getattr(self, "model", None)
        if not model:
            return specs
        for f in getattr(model._meta, "private_fields", []):
            # Em Django, GenericForeignKey é 'private_field'
            if isinstance(f, GenericForeignKey):
                name = f.name
                ct_field = f.ct_field
                oid_field = f.fk_field
                label = getattr(f, "verbose_name", None) or name.replace("_", " ").title()
                specs[name] = {
                    "ct_field": ct_field,
                    "oid_field": oid_field,
                    "limit_choices_to": None,   # will be read from the CT FK later
                    "label": label,
                    "_source": "plain_gfk",
                }
        return specs


    def _surrogate(self, logical_name: str) -> str:
        return f"{logical_name}{SURROGATE_SUFFIX}"

    def _specs(self):
        model = getattr(self, "model", None)
        base = dict(getattr(model, "_autogfk_fields", {}) if model else {})
        if model and getattr(self, "enable_plain_genericforeignkey", True):
            # mescla GFKs puros sem sobrescrever AutoGFKs homônimos
            for k, v in self._discover_plain_gfk_specs().items():
                base.setdefault(k, v)
        return base

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        try:
            self._autogfk_rendering = True
            return super().changeform_view(request, object_id, form_url, extra_context)
        finally:
            if hasattr(self, "_autogfk_rendering"):
                delattr(self, "_autogfk_rendering")

    def get_form(self, request, obj=None, **kwargs):
        specs = self._specs()
        model = self.model

        # 1) Base 'fields' = only real editable fields; remove ct/oid and logical
        real_fields = [f.name for f in model._meta.get_fields()
                       if getattr(f, "editable", False) and not f.auto_created]
        for logical, meta in specs.items():
            for rm in (logical, meta["ct_field"], meta["oid_field"]):
                if rm in real_fields:
                    real_fields.remove(rm)
        kwargs["fields"] = tuple(real_fields)

        base_form = super().get_form(request, obj, **kwargs)

        if not specs:
            return base_form

        # 2) Create ONE unique subclass and inject ALL surrogates
        #    Also consolidate Meta.exclude to hide all ct/oid.
        all_exclude = list(getattr(getattr(base_form, "Meta", object), "exclude", []) or [])
        for meta in specs.values():
            for f in (meta["ct_field"], meta["oid_field"]):
                if f not in all_exclude:
                    all_exclude.append(f)

        class UnifiedForm(base_form):
            class Meta(base_form.Meta if hasattr(base_form, "Meta") else object):
                exclude = all_exclude

        # Add all surrogate fields
        for logical, meta in specs.items():
            ct_field = meta["ct_field"]
            oid_field = meta["oid_field"]
            ct_model_field = self.model._meta.get_field(ct_field)
            oid_model_field = self.model._meta.get_field(oid_field)
            label = meta.get("label")
            surrogate = self._surrogate(logical)

            # ContentType queryset respecting limit_choices_to:
            # 1) If the AutoGFK auto-created the FK, we use meta["limit_choices_to"];
            # 2) If the user declared a custom FK, we read limit_choices_to directly from the FK.
            ct_qs = ContentType.objects.all()
            lct = meta.get("limit_choices_to")
            if not lct:
                try:
                    fk_field = self.model._meta.get_field(ct_field)
                    lct = getattr(getattr(fk_field, "remote_field", fk_field), "limit_choices_to", None)
                except Exception:
                    lct = None
            ct_qs = _apply_limit_choices(ct_qs, lct)

            # rule: the pair is "required" if ANY of the physical fields doesn't accept empty (null=False and blank=False)
            pair_required = (not getattr(ct_model_field, "null", True) and not getattr(ct_model_field, "blank", True)) \
                            or (not getattr(oid_model_field, "null", True) and not getattr(oid_model_field, "blank", True))


            f = AutoGenericFormField(label=label, required=pair_required, limit_ct_qs=ct_qs)
            f.widget = AutoGenericWidget(self, self.admin_site, limit_ct_qs=ct_qs, show_app_label=self.show_app_label_on_ct_field)
            if obj is not None:
                ct_val = getattr(obj, ct_field + "_id", None)
                oid_val = getattr(obj, oid_field, None)
                f.initial = (ct_val, oid_val)
            UnifiedForm.base_fields[surrogate] = f

        # Wrap the save: iterate over all surrogates and propagate ct/oid
        orig_save = UnifiedForm.save
        def _save(self2, commit=True):
            for logical, meta in specs.items():
                surrogate = f"{logical}{SURROGATE_SUFFIX}"
                cleaned = self2.cleaned_data.get(surrogate) or {}
                setattr(self2.instance, meta["ct_field"], cleaned.get("content_type"))
                setattr(self2.instance, meta["oid_field"], cleaned.get("object_id"))
            return orig_save(self2, commit)
        UnifiedForm.save = _save

        return UnifiedForm

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        specs = self._specs()
        if not specs:
            return fieldsets

        if not fieldsets:
            fieldsets = [(None, {"fields": []})]

        title, opts = fieldsets[0]
        fields = list(opts.get("fields", []))

        # Always hide physical fields
        for meta in specs.values():
            for f in (meta["ct_field"], meta["oid_field"]):
                if f in fields:
                    fields.remove(f)

        if getattr(self, "_autogfk_rendering", False):
            # Rendering: insert surrogates, remove logical
            for logical in list(specs.keys()):
                if logical in fields:
                    fields.remove(logical)
            for logical in specs.keys():
                sur = self._surrogate(logical)
                if sur not in fields:
                    fields.insert(0, sur)
        else:
            # Form construction: remove logical and surrogates
            for logical in specs.keys():
                for rm in (logical, self._surrogate(logical)):
                    if rm in fields:
                        fields.remove(rm)

        fieldsets[0] = (title, {**opts, "fields": tuple(fields)})
        return fieldsets
