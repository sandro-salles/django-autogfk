# django-autogfk

> **AutoGenericForeignKey**: transforme `GenericForeignKey` em algo *usável* no Django Admin, com Select2 + autocomplete e criação automática dos campos auxiliares.

![demo](docs/demo.gif)

## Features
- `AutoGenericForeignKey` que **cria** `*_content_type` e `*_object_id` automaticamente.
- **Widget** no Admin com **Select2** (content type ➜ objeto) e **autocomplete** via AJAX.
- View de autocomplete paginada, segura para staff.
- Integração via `AutoGenericAdminMixin`.

Compatível com Django **4.2+** (testado também em 5.0).

## Instalação
```bash
pip install django-autogfk
# ou para desenvolvimento
pip install -e .[dev]
```

## Uso
```python
# models.py
from django.db import models
from autogfk.fields import AutoGenericForeignKey

OWNER_LIMIT_CHOICES_TO = {"app_label__in": ["auth", "bots"]}

class IntelligenceCredentials(models.Model):
    owner = AutoGenericForeignKey(
        null=True,
        blank=True,
        limit_choices_to=OWNER_LIMIT_CHOICES_TO,
        related_name="intelligence_credentials",
        label="Dono",
    )
```

```python
# urls.py do projeto
from django.urls import include, path
urlpatterns = [
    path("_autogfk/", include("autogfk.urls")),
]
```

```python
# admin.py
from django.contrib import admin
from autogfk.admin import AutoGenericAdminMixin
from .models import IntelligenceCredentials

@admin.register(IntelligenceCredentials)
class IntelligenceCredentialsAdmin(AutoGenericAdminMixin, admin.ModelAdmin):
    list_display = ("id", "owner",)
```

## Configuração
- Garanta que `django.contrib.contenttypes` e `django.contrib.admin` estão instalados.
- O Select2 do Admin é usado automaticamente.

## Desenvolvimento & Testes
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Roadmap
- Registry de `search_fields` por ContentType.
- Permissões por modelo.
- Suporte a ID não-inteiro (UUID).

MIT © 2025


## Exemplo (projeto executável)
Um projeto Django de exemplo está em `example/`.

```bash
cd example
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Abra http://127.0.0.1:8000/admin/ e teste os campos `field_a` e `field_b` do modelo `Example`.
