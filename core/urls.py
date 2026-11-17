from django.urls import path
from . import views, views_contacto
 
app_name = "core"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("que-es/", views.que_es, name="que_es"),
    path("fuentes/", views.fuentes, name="fuentes"),
    path("buscar/", views.buscar, name="buscar"),
    path("contacto/", views_contacto.contacto, name="contacto"),
]
 