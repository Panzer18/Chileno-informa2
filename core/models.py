from django.db import models
 
 
class Fuente(models.Model):
    TIPOS = [
        ("monitoreo", "Monitoreo"),
        ("normativa", "Leyes y normativas"),
        ("noticias", "Noticias"),
    ]
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=250)
    enlace = models.URLField()
    tipo = models.CharField(max_length=20, choices=TIPOS)
 
    class Meta:
        ordering = ["tipo", "nombre"]
 
    def __str__(self):
        return self.nombre