from django.urls import path
from . import views

app_name = "noticias"
urlpatterns = [path("<slug:slug>/noticias/", views.lista, name="lista")]
