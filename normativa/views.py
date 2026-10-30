from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from comunas.models import Comuna
 
POR_PAGINA = 10
 
 
def lista(request, slug):
    comuna = get_object_or_404(Comuna, slug=slug)
    normas = comuna.normas.all()
    tipos = sorted(set(normas.values_list("tipo_norma", flat=True)))
    tipo = request.GET.get("tipo", "")
    if tipo:
        normas = normas.filter(tipo_norma=tipo)
 
    consulta = request.GET.copy()
    consulta.pop("page", None)
    pagina = Paginator(normas, POR_PAGINA).get_page(request.GET.get("page"))
 
    return render(request, "normativa/lista.html", {
        "comuna": comuna, "pagina": pagina, "consulta": consulta.urlencode(),
        "tipos": tipos, "tipo": tipo,
    })