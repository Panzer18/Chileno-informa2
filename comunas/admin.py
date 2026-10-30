from django.contrib import admin
from .models import Comuna, Monitoreo
 
 
@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("nombre",)}
    search_fields = ("nombre",)
 
 
@admin.register(Monitoreo)
class MonitoreoAdmin(admin.ModelAdmin):
    list_display = ("parametro", "comuna", "tipo", "fuente", "ultima_revision")
    list_filter = ("comuna", "tipo", "fuente")
    search_fields = ("parametro", "fuente")
 