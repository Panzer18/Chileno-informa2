from django.db import models

class Norma(models.Model):
    nombre = models.CharField(max_length=250)
    tipo_norma = models.CharField(max_length=100)  # Ley, Decreto, Resolución...
    fecha_publicacion = models.DateField(null=True, blank=True)
    enlace_fuente = models.URLField()  # por ejemplo, la página en Ley Chile
    comunas = models.ManyToManyField("comunas.Comuna", related_name="normas")

    class Meta:
        ordering = ["-fecha_publicacion"]

    def __str__(self):
        return self.nombre
