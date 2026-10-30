from django.contrib import admin
from .models import Noticia
 
 
@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "fecha", "fuente")
    list_filter = ("fuente", "comunas")
    search_fields = ("titulo", "fuente")
    date_hierarchy = "fecha"