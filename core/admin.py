from django.contrib import admin
from .models import Fuente, Mensaje
 
 
@admin.register(Fuente)
class FuenteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "enlace")
    list_filter = ("tipo",)
    search_fields = ("nombre", "descripcion")
 
 
@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ("fecha_envio", "nombre", "correo", "motivo")
    list_filter = ("motivo",)
    search_fields = ("nombre", "correo", "mensaje")
    readonly_fields = ("fecha_envio",)