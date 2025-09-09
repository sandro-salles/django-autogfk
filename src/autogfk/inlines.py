# src/autogfk/inlines.py
from __future__ import annotations
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Q

from .forms import AutoGenericFormField
from .widgets import AutoGenericWidget

SURROGATE_SUFFIX = "__autogfk"

def _apply_limit_choices(qs, lct):
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
    return qs

class AutoGenericInlineMixin:
    """
    Mixin for InlineModelAdmin that:
      - hide *_content_type and *_object_id
      - inject a logical “surrogate” (Select2 CT→obj) field by AutoGFK/GFK
      - validate required/partial and save back to the physical fields
    """
    # UX: show "app | verbose_name" in the CT select (False: only the verbose_name)
    show_app_label_on_ct_field = True
    # Enable wrapping native GFK (in addition to AutoGFK)
    enable_plain_genericforeignkey = True

    def _surrogate(self, logical: str) -> str:
        return f"{logical}{SURROGATE_SUFFIX}"

    def _discover_plain_gfk_specs(self, model):
        specs = {}
        for f in getattr(model._meta, "private_fields", []):
            if isinstance(f, GenericForeignKey):
                specs[f.name] = {
                    "ct_field": f.ct_field,
                    "oid_field": f.fk_field,
                    "limit_choices_to": None,  # read from the FK at runtime
                    "label": getattr(f, "verbose_name", None) or f.name.replace("_", " ").title(),
                    "_source": "plain_gfk",
                }
        return specs

    def _specs(self, model):
        base = dict(getattr(model, "_autogfk_fields", {}) or {})
        if self.enable_plain_genericforeignkey:
            for k, v in self._discover_plain_gfk_specs(model).items():
                base.setdefault(k, v)
        return base

    # --- InlineModelAdmin hooks ---

    # --- Construction of the ModelForm (cannot contain surrogates) ---
    def get_fields(self, request, obj=None):
        """
        Returns only "real" and editable fields for the ModelForm construction,
        removing:
          - the logical fields (AutoGFK/GFK),
          - the physical auxiliar fields (<name>_content_type / <name>_object_id),
          - and the own surrogates (<name>__autogfk).
        This avoids the FieldError during the form creation.
        """
        model = self.model
        specs = self._specs(model)

        # builds the list from the model (instead of relying on super(), which
        # can look at fieldsets and, thus, take surrogates that should only exist in rendering)
        fields = [f.name for f in model._meta.get_fields()
                  if getattr(f, "editable", False) and not f.auto_created]

        for logical, meta in specs.items():
            for rm in (logical, meta["ct_field"], meta["oid_field"], self._surrogate(logical)):
                if rm in fields:
                    fields.remove(rm)

        return tuple(fields)

    def get_formset(self, request, obj=None, **kwargs):
        """
        Creates a base ModelForm via super(), injects surrogates and validation,
        and returns a FormSet that uses that ModelForm.
        """
        # During the FormSet construction (super call), we avoid injecting
        # surrogates in get_fieldsets() to not confuse the modelform_factory.
        # Only after, with the Form ready, the rendering can inject them.
        building_prev = getattr(self, "_autogfk_inline_building", False)
        self._autogfk_inline_building = True
        try:
            FormSet = super().get_formset(request, obj, **kwargs)
        finally:
            self._autogfk_inline_building = building_prev
        model = self.model
        specs = self._specs(model)
        if not specs:
            return FormSet

        base_form = FormSet.form

        # Exclude the physical fields from the inline forms
        all_exclude = list(getattr(getattr(base_form, "Meta", object), "exclude", []) or [])
        for meta in specs.values():
            for f in (meta["ct_field"], meta["oid_field"]):
                if f not in all_exclude:
                    all_exclude.append(f)

        # Rebuild a unified ModelForm
        class UnifiedForm(base_form):
            class Meta(base_form.Meta if hasattr(base_form, "Meta") else object):
                exclude = tuple(all_exclude)

        # Inject surrogates: field by field
        for logical, meta in specs.items():
            ct_field = meta["ct_field"]
            oid_field = meta["oid_field"]
            label = meta.get("label")
            surrogate = self._surrogate(logical)

            # limit_choices_to: use the AutoGFK limit_choices_to (if any) or read from the real FK
            lct = meta.get("limit_choices_to")
            if not lct:
                try:
                    fk_field = model._meta.get_field(ct_field)
                    lct = getattr(getattr(fk_field, "remote_field", fk_field), "limit_choices_to", None)
                except Exception:
                    lct = None
            ct_qs = _apply_limit_choices(ContentType.objects.all(), lct)

            # required = based on the physical fields
            ct_model_field = model._meta.get_field(ct_field)
            oid_model_field = model._meta.get_field(oid_field)
            pair_required = (not getattr(ct_model_field, "null", True) and not getattr(ct_model_field, "blank", True)) \
                            or (not getattr(oid_model_field, "null", True) and not getattr(oid_model_field, "blank", True))

            f = AutoGenericFormField(label=label, required=pair_required, limit_ct_qs=ct_qs)
            f.widget = AutoGenericWidget(self, self.admin_site, limit_ct_qs=ct_qs,
                                         show_app_label=self.show_app_label_on_ct_field)

            # initial is resolved by form.instance in editing; here we only register the field
            UnifiedForm.base_fields[surrogate] = f

        # Save: propagate surrogate -> physical fields
        orig_save = UnifiedForm.save
        def _save(self2, commit=True):
            for logical, meta in specs.items():
                surrogate = f"{logical}{SURROGATE_SUFFIX}"
                data = self2.cleaned_data.get(surrogate) or {}
                setattr(self2.instance, meta["ct_field"], data.get("content_type"))
                setattr(self2.instance, meta["oid_field"], data.get("object_id"))
            return orig_save(self2, commit)
        UnifiedForm.save = _save

        # Clean: validate required/partial
        orig_clean = UnifiedForm.clean if hasattr(UnifiedForm, "clean") else None
        def _clean(self2):
            if orig_clean:
                cleaned_all = orig_clean(self2)
            else:
                cleaned_all = super(UnifiedForm, self2).clean()

            for logical, meta in specs.items():
                surrogate = f"{logical}{SURROGATE_SUFFIX}"
                data = self2.cleaned_data.get(surrogate) or {}
                ct_val = data.get("content_type")
                oid_val = data.get("object_id")

                ct_field_name = meta["ct_field"]
                oid_field_name = meta["oid_field"]
                ct_model_field = self2._meta.model._meta.get_field(ct_field_name)
                oid_model_field = self2._meta.model._meta.get_field(oid_field_name)
                pair_required = (not getattr(ct_model_field, "null", True) and not getattr(ct_model_field, "blank", True)) \
                                or (not getattr(oid_model_field, "null", True) and not getattr(oid_model_field, "blank", True))

                if (ct_val and not oid_val) or (oid_val and not ct_val):
                    self2.add_error(surrogate, "Select content and object; it is not allowed to fill only one of the two.")
                elif pair_required and (not ct_val and not oid_val):
                    self2.add_error(surrogate, "This field is required.")

            return cleaned_all
        UnifiedForm.clean = _clean

        # Finally, wrap the FormSet to change the form class
        class WrappedFormSet(FormSet):
            form = UnifiedForm

            def _construct_form(self, i, **k):
                form = super()._construct_form(i, **k)
                # Populate initial when editing existing lines:
                inst = form.instance
                if inst and inst.pk:
                    for logical, meta in specs.items():
                        surrogate = f"{logical}{SURROGATE_SUFFIX}"
                        ct_val = getattr(inst, meta["ct_field"] + "_id", None)
                        oid_val = getattr(inst, meta["oid_field"], None)
                        if surrogate in form.fields:
                            form.initial[surrogate] = (ct_val, oid_val)
                return form

        return WrappedFormSet

    def get_fieldsets(self, request, obj=None):
        """
        Remove physical fields and inject surrogates for rendering (similar to admin mixin).
        """
        fieldsets = list(super().get_fieldsets(request, obj))
        specs = self._specs(self.model)
        if not specs:
            return fieldsets

        if not fieldsets:
            fieldsets = [(None, {"fields": []})]

        title, opts = fieldsets[0]
        fields = list(opts.get("fields", []))

        # remove physical and logical fields (the inline form will use surrogates)
        for logical, meta in specs.items():
            for rm in (logical, meta["ct_field"], meta["oid_field"]):
                if rm in fields:
                    fields.remove(rm)

        # inject surrogates only if we are not building the FormSet
        if not getattr(self, "_autogfk_inline_building", False):
            for logical in specs.keys():
                sur = self._surrogate(logical)
                if sur not in fields:
                    fields.insert(0, sur)

        fieldsets[0] = (title, {**opts, "fields": tuple(fields)})
        return fieldsets
