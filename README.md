# django-autogfk

**Admin-friendly GenericForeignKey for Django — Select2 autocomplete, smart field creation, and an example project.**

[![CI](https://github.com/sandro-salles/django-autogfk/actions/workflows/ci.yml/badge.svg)](https://github.com/sandro-salles/django-autogfk/actions)
[![PyPI version](https://img.shields.io/pypi/v/django-autogfk.svg)](https://pypi.org/project/django-autogfk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

`django-autogfk` makes working with `GenericForeignKey` in Django a first-class experience.  
Instead of clunky dropdowns and raw IDs, it gives you a **Select2-based interface** with **autocomplete, filtering, and pagination**, just like `autocomplete_fields` for normal `ForeignKey`s.

## ✨ Features
- **Drop-in**: `AutoGenericForeignKey` automatically creates the underlying `*_content_type` and `*_object_id` fields.
- **Beautiful Select2 widget** in the Admin (content type ➜ object) with AJAX search and pagination.
- Supports `limit_choices_to`, `null/blank`, `related_name` just like regular fields.
- `AutoGenericAdminMixin` integrates seamlessly with Django Admin.
- **Example project** included (`example/`) so you can try it out instantly.

**Requirements:** Django **4.2+** (also tested on 5.0)  
**License:** MIT

---

## 📦 Installation

From PyPI (recommended):
```bash
pip install django-autogfk
```

From source (editable):
```bash
git clone https://github.com/sandro-salles/django-autogfk.git
cd django-autogfk
pip install -e .[dev]
```

Add `autogfk` to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ...
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "autogfk",
]
```

Include URLs (for the autocomplete endpoint):
```python
# urls.py (project)
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("_autogfk/", include("autogfk.urls")),  # ← required
]
```

> The package uses Select2 shipped with Django Admin — no extra frontend deps.

---

## 🚀 Quickstart

### 1) Define your model using `AutoGenericForeignKey`
```python
# models.py
from django.db import models
from autogfk.fields import AutoGenericForeignKey

# Example: allow only content types from specific apps
OWNER_LIMIT_CHOICES_TO = {"app_label__in": ["auth", "bots"]}

class Example(models.Model):
    owner = AutoGenericForeignKey(
        null=True,
        blank=True,
        limit_choices_to=OWNER_LIMIT_CHOICES_TO,
        related_name="examples",
        label="Owner",
    )

    name = models.CharField(max_length=120, blank=True, default="")
```

This automatically creates the concrete fields:
- `owner_content_type = ForeignKey(ContentType, …)`
- `owner_object_id = PositiveIntegerField(…)`

Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2) Hook into the Admin
```python
# admin.py
from django.contrib import admin
from autogfk.admin import AutoGenericAdminMixin
from .models import Example

@admin.register(IntelligenceCredentials)
class ExampleAdmin(AutoGenericAdminMixin, admin.ModelAdmin):
    show_app_label_on_ct_field = False # constrols if ct select will show/hide the app_label
    list_display = ("id", "owner", "name")
```

Open the Django Admin and edit an object:  
You’ll see **two linked Select2 dropdowns**:
1) pick a **ContentType** (already filtered if you set `limit_choices_to`),  
2) search/select the **object** of that model via **AJAX autocomplete**.

---

#### 2.1) Use the Admin mixin with a *plain* `GenericForeignKey`

You don’t have to migrate your models to `AutoGenericForeignKey` to get the nice admin UX.
Just plug `AutoGenericAdminMixin` into your `ModelAdmin` and it will render the **same Select2 widget**
for any existing `GenericForeignKey` (CT → Object, with autocomplete, validation, and paging).

- Works **side-by-side** with `AutoGenericForeignKey`.
- Reads `limit_choices_to` **directly from your `ForeignKey(ContentType)`** (dict, `Q`, callable, or list/tuple).
- Enforces requiredness based on the **physical fields** (`null`/`blank`) and prevents partial input.
- Toggle labels: show or hide `app_label` in the CT select.

### Example (plain GFK model)

```python
# models.py
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

ALLOW_AB = Q(app_label="exampleapp", model__in=["modela", "modelb"])

class ExamplePlainGFK(models.Model):
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=ALLOW_AB,   # ← the admin mixin will respect this
        null=False, blank=False,     # ← makes the pair required in the form
    )
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_content_type", "target_object_id")

    def __str__(self):
        return f"{self.target_content_type} #{self.target_object_id}"

# admin.py
from django.contrib import admin
from autogfk.admin import AutoGenericAdminMixin
from .models import Example

@admin.register(ExamplePlainGFK)
class ExamplePlainGFKAdmin(AutoGenericAdminMixin, admin.ModelAdmin):
    list_display = ("id", "target")
    # optional - controls if the CT select will show/hide the app_label
    show_app_label_on_ct_field = False

    # optional - controls if the widget is enabled for plain GenericForeignKey fields as well
    enable_plain_genericforeignkey = True
```

## 🧩 Example project (runnable)

A fully working Django project lives in `example/`:

```bash
cd example
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Navigate to http://127.0.0.1:8000/admin/ and test the **Example** model.  
It contains:
- `ModelA`, `ModelB` and `ModelCRequired` (sample models),
- `Example` with **three** `AutoGenericForeignKey` fields: `field_a`, `field_b` and `field_c`.

---

## ⚙️ Configuration & Tips

### `limit_choices_to`
You can restrict selectable ContentTypes:
```python
AutoGenericForeignKey(limit_choices_to={"app_label__in": ["exampleapp"]})
```
> For advanced filtering (e.g., per user or per model), subclass the autocomplete view or add permission checks in `views.py`.

### Labels and Related Names
- `label="Owner"` controls form label/placeholder in the Admin.
- `related_name="intelligence_credentials"` is propagated to the generated `content_type` field.

### Migrations
Because the field **creates the concrete fields in `contribute_to_class`**, the migration system will pick them up after you add the `AutoGenericForeignKey`. Always run `makemigrations` after changes.

---

## 🔒 Permissions & Security

The built-in autocomplete view is protected by `@staff_member_required`.  
For multi-tenant or per-object permissions:
- Override the queryset in `views.autocomplete` to filter objects by `request.user`.
- Optionally mount a custom URL (e.g., `path("autocomplete/", my_view, name="autocomplete")`).

---

## 🧰 API Reference (short)

### `AutoGenericForeignKey(...)`
**Args (selected):**
- `ct_field: str | None` — name for the `ContentType` FK (auto: `<name>_content_type`)
- `oid_field: str | None` — name for the object ID field (auto: `<name>_object_id`)
- `null: bool` / `blank: bool`
- `limit_choices_to: dict | None`
- `related_name: str | None`
- `label: str | None` — Admin form label

### `AutoGenericAdminMixin`
- Auto-injects a **MultiWidget** with **Select2 + AJAX** for every `AutoGenericForeignKey` on the model.
- Handles initial values and saving back to `<name>_content_type` / `<name>_object_id`.

---

## 🧪 Tests

Run the test suite:
```bash
pytest
```

What’s covered (high level):
- Field auto-creation of `*_content_type` / `*_object_id`
- Autocomplete view (AJAX response, pagination basics)
- Admin form integration (initials and save path)

---

## 🐛 Troubleshooting

- **“The widget isn’t loading as Select2”**  
  Make sure you’re using Django Admin’s default assets. The package relies on Admin’s bundled Select2.

- **“No results appear in the object dropdown”**  
  Confirm the selected ContentType actually has instances. Try typing to trigger autocomplete.

- **“I need different search fields per model”**  
  Fork/override the `autocomplete` view and tailor the `search_fields` heuristic for your models.

- **“I want to restrict by user/team”**  
  Add checks in the `autocomplete` view using `request.user` and filter the queryset accordingly.

---

## 🤝 Contributing

PRs welcome!  
Ideas:
- Registry to configure **per-model** search fields.
- Per-model permission hooks.
- Optional support for non-integer identifiers (e.g., UUID) in a future minor version.

Steps:
```bash
git clone https://github.com/sandro-salles/django-autogfk.git
cd django-autogfk
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
pytest
```

---

## 📄 License

**MIT** — permissive and simple. See [LICENSE](./LICENSE).

---

## 💡 Credits

Built to make `GenericForeignKey` feel as smooth as a regular `ForeignKey` in the Django Admin. Enjoy!
