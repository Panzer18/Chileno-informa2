from django.urls import path
from . import views
 
app_name = "core"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("que-es/", views.que_es, name="que_es"),
    path("fuentes/", views.fuentes, name="fuentes"),
    path("buscar/", views.buscar, name="buscar"),
]
 