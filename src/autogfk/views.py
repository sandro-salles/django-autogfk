from __future__ import annotations
from django.http import JsonResponse, Http404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.core.paginator import Paginator

PAGE_SIZE = 30

@staff_member_required
def autocomplete(request):
    ct_id = request.GET.get("ct")
    if not ct_id:
        raise Http404("Missing content type")
    try:
        ct = ContentType.objects.get(pk=ct_id)
    except ContentType.DoesNotExist:
        raise Http404("Invalid content type")

    model = ct.model_class()
    if model is None:
        return JsonResponse({"results": [], "more": False})

    q = request.GET.get("q", "")
    qs = model._default_manager.all()

    search_fields = []
    for field_name in ("name", "title", "username", "email", "slug", "id"):
        if hasattr(model, field_name):
            search_fields.append(field_name)
    if q and search_fields:
        filt = Q()
        for f in search_fields:
            if f == "id" and q.isdigit():
                filt |= Q(**{f: int(q)})
            else:
                filt |= Q(**{f"{f}__icontains": q})
        qs = qs.filter(filt)

    if getattr(model._meta, "ordering", None):
        qs = qs.order_by(*model._meta.ordering)
    else:
        qs = qs.order_by("pk")

    paginator = Paginator(qs, PAGE_SIZE)
    page_number = int(request.GET.get("page", 1))
    page = paginator.get_page(page_number)

    def label(obj):
        if hasattr(obj, "__str__"):
            return str(obj)
        return f"{model.__name__} #{obj.pk}"

    data = {
        "results": [{"id": obj.pk, "text": label(obj)} for obj in page.object_list],
        "more": page.has_next(),
    }
    return JsonResponse(data)
