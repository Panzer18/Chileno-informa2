from django.db import models

class Noticia(models.Model):
    titulo = models.CharField(max_length=250)
    fecha = models.DateField()
    fuente = models.CharField(max_length=100)  # por ejemplo, MMA
    enlace = models.URLField()
    comunas = models.ManyToManyField("comunas.Comuna", related_name="noticias")

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return self.titulo
