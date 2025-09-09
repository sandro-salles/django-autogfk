# Example project

Minimal Django project to test `django-autogfk` locally.

## Running

```bash
cd example
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# or: pip install ../  (install local package)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Access: http://127.0.0.1:8000/admin/

- Register some `ModelA`, `ModelB` and `ModelCRequired`.
- In `Example`, use the **Field A**, **Field B** and **Field C** fields (each one is an `AutoGenericForeignKey` with Select2 + autocomplete).
```

