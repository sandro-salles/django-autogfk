from django.urls import path
from .views import autocomplete

app_name = "autogfk"

urlpatterns = [
    path("autocomplete/", autocomplete, name="autocomplete"),
]
