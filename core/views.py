import difflib
import unicodedata
 
from django.db.models import Count, Q
from django.shortcuts import render
from comunas.models import Comuna
from noticias.models import Noticia
from normativa.models import Norma
from .models import Fuente
 
OPCIONES_EN = ("todo", "comunas", "leyes", "noticias")
 
 
def inicio(request):
    comunas = Comuna.objects.annotate(
        n_monitoreos=Count("monitoreos", distinct=True),
        n_normas=Count("normas", distinct=True),
        n_noticias=Count("noticias", distinct=True),
    )
    return render(request, "core/inicio.html", {
        "comunas": comunas,
        "ultimas_noticias": Noticia.objects.order_by("-fecha")[:3],
    })
 
 
def que_es(request):
    return render(request, "core/que_es.html")
 
 
def fuentes(request):
    grupos = [(etiqueta, Fuente.objects.filter(tipo=clave))
              for clave, etiqueta in Fuente.TIPOS]
    return render(request, "core/fuentes.html", {"grupos": grupos})
 
 
def _normalizar(texto):
    """Pasa a minúsculas y quita las tildes, para comparar nombres."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")
 
 
def buscar(request):
    q = request.GET.get("q", "").strip()
    en = request.GET.get("en", "todo")
    if en not in OPCIONES_EN:
        en = "todo"
    comuna_filtro = Comuna.objects.filter(slug=request.GET.get("comuna", "")).first()
 
    buscando = bool(q or comuna_filtro)
    coincidencias, similares, normas, noticias = [], [], [], []
 
    if buscando:
        # Comunas parecidas al texto escrito (solo si no se eligió una comuna).
        if q and not comuna_filtro and en in ("todo", "comunas"):
            q_n = _normalizar(q)
            for c in Comuna.objects.all():
                nombre = _normalizar(c.nombre)
                palabras = nombre.replace("-", " ").split()
                if q_n in nombre:
                    coincidencias.append(c)
                elif (difflib.SequenceMatcher(None, q_n, nombre).ratio() >= 0.5
                      or difflib.get_close_matches(q_n, palabras, n=1, cutoff=0.6)):
                    similares.append(c)
        encontradas = coincidencias + similares
 
        if en in ("todo", "leyes"):
            normas = Norma.objects.all()
            if q:
                normas = normas.filter(
                    Q(nombre__icontains=q) | Q(tipo_norma__icontains=q)
                    | Q(comunas__in=encontradas))
            if comuna_filtro:
                normas = normas.filter(comunas=comuna_filtro)
            normas = normas.distinct()
 
        if en in ("todo", "noticias"):
            noticias = Noticia.objects.all()
            if q:
                noticias = noticias.filter(
                    Q(titulo__icontains=q) | Q(fuente__icontains=q)
                    | Q(comunas__in=encontradas))
            if comuna_filtro:
                noticias = noticias.filter(comunas=comuna_filtro)
            noticias = noticias.distinct()
 
    total = len(coincidencias) + len(similares) + len(normas) + len(noticias)
    return render(request, "core/buscar.html", {
        "q": q, "en": en, "buscando": buscando, "total": total,
        "comuna_slug": comuna_filtro.slug if comuna_filtro else "",
        "todas_comunas": Comuna.objects.all(),
        "coincidencias": coincidencias, "similares": similares,
        "normas": normas, "noticias": noticias,
    })
 