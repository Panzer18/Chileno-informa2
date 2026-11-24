from django.db import models


class Norma(models.Model):

    AMBITOS = [
        ("NACIONAL", "Nacional"),
        ("REGIONAL", "Regional"),
        ("COMUNAL", "Comunal"),
    ]

    nombre = models.CharField(max_length=250)

    tipo_norma = models.CharField(max_length=100)

    ambito = models.CharField(
        max_length=20,
        choices=AMBITOS,
        default="NACIONAL"
    )

    fecha_publicacion = models.DateField(
        null=True,
        blank=True
    )

    enlace_fuente = models.URLField()

    comunas = models.ManyToManyField(
        "comunas.Comuna",
        related_name="normas",
        blank=True
    )

    class Meta:
        ordering = ["-fecha_publicacion"]

    def __str__(self):
        return self.nombre
