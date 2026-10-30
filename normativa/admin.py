from django.contrib import admin
from .models import Norma
 
 
@admin.register(Norma)
class NormaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo_norma", "fecha_publicacion")
    list_filter = ("tipo_norma", "comunas")
    search_fields = ("nombre", "tipo_norma")
    date_hierarchy = "fecha_publicacion"