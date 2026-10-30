from django.shortcuts import get_object_or_404, render
from .models import Comuna
 
 
def detalle(request, slug):
    comuna = get_object_or_404(Comuna, slug=slug)
    resumen = {
        "monitoreos": comuna.monitoreos.count(),
        "normas": comuna.normas.count(),
        "noticias": comuna.noticias.count(),
    }
    return render(request, "comunas/detalle.html", {"comuna": comuna, "resumen": resumen})
 
 
def monitoreo(request, slug):
    comuna = get_object_or_404(Comuna, slug=slug)
    return render(request, "comunas/monitoreo.html", {
        "comuna": comuna,
        "hidricos": comuna.monitoreos.filter(tipo="hidrico"),
        "ambientales": comuna.monitoreos.filter(tipo="ambiental"),
    })
 