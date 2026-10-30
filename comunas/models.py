from django.db import models
 
 
class Comuna(models.Model):
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)  # usado en las URLs: /comunas/petorca/
    region = models.CharField(max_length=100)
 
    class Meta:
        ordering = ["nombre"]
 
    def __str__(self):
        return self.nombre
 
 
class Monitoreo(models.Model):
    TIPOS = [("hidrico", "Hídrico"), ("ambiental", "Ambiental")]
    comuna = models.ForeignKey(Comuna, on_delete=models.CASCADE, related_name="monitoreos")
    tipo = models.CharField(max_length=20, choices=TIPOS)
    parametro = models.CharField("nombre", max_length=150)
    valor = models.CharField(max_length=100, blank=True)
    fecha_medicion = models.DateField(null=True, blank=True)
    fuente = models.CharField(max_length=100)  # DGA, SMA, PRAS...
    enlace_fuente = models.URLField()
    ultima_revision = models.DateField(
        "última revisión del enlace", null=True, blank=True,
        help_text="Fecha en que el equipo comprobó que el enlace funciona.")
 
    def __str__(self):
        return f"{self.fuente} - {self.parametro} ({self.comuna})"