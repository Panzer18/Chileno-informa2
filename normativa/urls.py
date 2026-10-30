from django.urls import path
from . import views

app_name = "normativa"
urlpatterns = [path("<slug:slug>/leyes/", views.lista, name="lista")]
