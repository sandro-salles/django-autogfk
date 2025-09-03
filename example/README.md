# Example project

Projeto Django mínimo para testar `django-autogfk` localmente.

## Rodando

```bash
cd example
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# ou: pip install ../  (instala o pacote local)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/admin/

- Cadastre alguns `ModelA` e `ModelB`.
- Em `Example`, use os campos **Field A** e **Field B** (cada um é um `AutoGenericForeignKey` com Select2 + autocomplete).
```

