from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, render
 
from comunas.models import Comuna
from .consultas import normas_de
from .models import Norma
 
POR_PAGINA = 10
ORDENES = [("reciente", "Más reciente"), ("antiguo", "Más antiguo")]
 
 
def _ordenar(normas, orden):
    """Ordena por fecha de publicación; las normas sin fecha quedan al final."""
    fecha = F("fecha_publicacion")
    if orden == "antiguo":
        return normas.order_by(fecha.asc(nulls_last=True), "nombre")
    return normas.order_by(fecha.desc(nulls_last=True), "nombre")
 
 
def lista(request, slug):
    comuna = get_object_or_404(Comuna, slug=slug)
    normas = normas_de(comuna)
 
    # Las opciones de los filtros se calculan antes de filtrar.
    tipos = sorted(set(normas.values_list("tipo_norma", flat=True)))
    presentes = set(normas.values_list("ambito", flat=True))
    ambitos = [(clave, etiqueta) for clave, etiqueta in Norma.AMBITOS if clave in presentes]
 
    tipo = request.GET.get("tipo", "")
    ambito = request.GET.get("ambito", "")
    orden = request.GET.get("orden", "reciente")
    if tipo:
        normas = normas.filter(tipo_norma=tipo)
    if ambito in dict(Norma.AMBITOS):
        normas = normas.filter(ambito=ambito)
    else:
        ambito = ""
    if orden not in dict(ORDENES):
        orden = "reciente"
 
    normas = _ordenar(normas, orden)
 
    consulta = request.GET.copy()
    consulta.pop("page", None)
    pagina = Paginator(normas, POR_PAGINA).get_page(request.GET.get("page"))
 
    return render(request, "normativa/lista.html", {
        "comuna": comuna, "pagina": pagina, "consulta": consulta.urlencode(),
        "tipos": tipos, "tipo": tipo, "ambitos": ambitos, "ambito": ambito,
        "ordenes": ORDENES, "orden": orden,
        "hay_filtros": bool(tipo or ambito),
    })