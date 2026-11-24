from django.db import models
 
 
class Noticia(models.Model):
    titulo = models.CharField(max_length=250)
    fecha = models.DateField()
    fuente = models.CharField(max_length=100)  # por ejemplo, MMA
    enlace = models.URLField()
    imagen = models.URLField(
        "imagen de previsualización", max_length=500, blank=True,
        help_text="Dirección de una imagen de la noticia (opcional).")
    comunas = models.ManyToManyField("comunas.Comuna", related_name="noticias")
 
    class Meta:
        ordering = ["-fecha"]
 
    def __str__(self):
        return self.titulo