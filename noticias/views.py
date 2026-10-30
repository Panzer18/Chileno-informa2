from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date
from comunas.models import Comuna
 
POR_PAGINA = 6
 
 
def _fecha(valor):
    """Convierte 'AAAA-MM-DD' en fecha. Devuelve None si está vacío o es inválido."""
    try:
        return parse_date(valor)
    except ValueError:
        return None
 
 
def lista(request, slug):
    comuna = get_object_or_404(Comuna, slug=slug)
    todas = comuna.noticias.all()
    fuentes = sorted(set(todas.values_list("fuente", flat=True)))
    fuente = request.GET.get("fuente", "")
    desde = request.GET.get("desde", "")
    hasta = request.GET.get("hasta", "")
 
    noticias = todas
    if fuente:
        noticias = noticias.filter(fuente=fuente)
    if _fecha(desde):
        noticias = noticias.filter(fecha__gte=_fecha(desde))
    if _fecha(hasta):
        noticias = noticias.filter(fecha__lte=_fecha(hasta))
 
    # Los filtros se conservan en los enlaces "Anterior" y "Siguiente".
    consulta = request.GET.copy()
    consulta.pop("page", None)
    pagina = Paginator(noticias, POR_PAGINA).get_page(request.GET.get("page"))
 
    return render(request, "noticias/lista.html", {
        "comuna": comuna, "pagina": pagina, "consulta": consulta.urlencode(),
        "fuentes": fuentes, "fuente": fuente, "desde": desde, "hasta": hasta,
        "hay_filtros": bool(fuente or desde or hasta),
    })