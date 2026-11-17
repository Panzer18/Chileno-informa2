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
 
 
class Mensaje(models.Model):
    MOTIVOS = [
        ("consulta", "Consulta general"),
        ("enlace", "Reportar un enlace que no funciona"),
        ("fuente", "Sugerir una fuente, ley o noticia"),
        ("error", "Reportar un error del sitio"),
        ("otro", "Otro motivo"),
    ]
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    mensaje = models.TextField(max_length=2000)
    fecha_envio = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["-fecha_envio"]
        verbose_name_plural = "mensajes de contacto"
 
    def __str__(self):
        return f"{self.get_motivo_display()} - {self.nombre}"