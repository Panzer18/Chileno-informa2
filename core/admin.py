from django.contrib import admin
from .models import Fuente
 
 
@admin.register(Fuente)
class FuenteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "enlace")
    list_filter = ("tipo",)
    search_fields = ("nombre", "descripcion")