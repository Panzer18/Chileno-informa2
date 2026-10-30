from django.urls import path
from . import views

app_name = "comunas"
urlpatterns = [
    path("<slug:slug>/", views.detalle, name="detalle"),
    path("<slug:slug>/monitoreo/", views.monitoreo, name="monitoreo"),
]
