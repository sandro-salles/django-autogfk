from __future__ import annotations
from typing import Optional
from django import forms
from django.contrib.contenttypes.models import ContentType

class AutoGenericForeignKeyFormField(forms.MultiValueField):
    def __init__(self, *, label: Optional[str] = None, required: bool = False, limit_ct_qs=None):
        fields = (
            forms.ModelChoiceField(queryset=limit_ct_qs or ContentType.objects.all(), required=required),
            forms.CharField(required=required),
        )
        super().__init__(fields=fields, require_all_fields=False, label=label, required=required)

    def compress(self, data_list):
        if not data_list:
            return {"content_type": None, "object_id": None}
        ct, oid = data_list
        if not ct or not oid:
            return {"content_type": None, "object_id": None}
        return {"content_type": ct, "object_id": int(oid)}
