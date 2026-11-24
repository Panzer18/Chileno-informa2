import unicodedata
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import quote_plus, urljoin
 
from comunas.models import Comuna
from .models import Noticia
 
LARGO_MAX_ENLACE = 200   # límite del campo `enlace` del modelo Noticia
LARGO_MAX_IMAGEN = 500   # límite del campo `imagen` del modelo Noticia
BASE_MMA = "https://mma.gob.cl"
NS_MEDIA = "{http://search.yahoo.com/mrss/}"
NS_CONTENIDO = "{http://purl.org/rss/1.0/modules/content/}"
 
# Canales adicionales para comunas cuya etiqueta en el MMA no coincide con su slug.
# Se escribe: "slug-de-la-comuna": ["canal 1", "canal 2"]
FEEDS_ESPECIALES = {
    "quintero-puchuncavi": [f"{BASE_MMA}/tag/quintero-y-puchuncavi/feed/"],
}
 
 
def _normalizar(texto):
    """Minúsculas y sin tildes, para buscar palabras sin importar cómo se escriban."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")
 
 
def terminos_busqueda(nombre):
    """Palabras a buscar en el MMA para una comuna.
 
    'Petorca' -> ['Petorca']; 'Quintero-Puchuncaví' -> ['Quintero', 'Puchuncaví'];
    'Los Andes' -> ['"Los Andes"'] (frase entre comillas).
    """
    terminos = []
    for parte in nombre.split("-"):
        parte = parte.strip()
        if parte:
            terminos.append(f'"{parte}"' if " " in parte else parte)
    return terminos
 
 
def urls_para(comuna):
    """Canales RSS del MMA donde buscar noticias de una comuna."""
    urls = [f"{BASE_MMA}/tag/{comuna.slug}/feed/"]
    urls += FEEDS_ESPECIALES.get(comuna.slug, [])
    for termino in terminos_busqueda(comuna.nombre):
        urls.append(f"{BASE_MMA}/?s={quote_plus(termino)}&feed=rss2")
    return list(dict.fromkeys(urls))  # sin repetidos, conservando el orden
 
 
# ---------- Imágenes ----------
def _limpiar_url(url):
    """Acepta solo direcciones http/https de largo razonable (descarta 'javascript:' y similares)."""
    url = (url or "").strip()
    if url.startswith(("http://", "https://")) and len(url) <= LARGO_MAX_IMAGEN:
        return url
    return ""
 
 
class _PrimeraImagen(HTMLParser):
    """Encuentra la primera etiqueta <img> de un trozo de HTML."""
    def __init__(self):
        super().__init__()
        self.url = ""
 
    def handle_starttag(self, etiqueta, atributos):
        if etiqueta == "img" and not self.url:
            self.url = dict(atributos).get("src") or ""
 
 
class _ImagenDePortada(HTMLParser):
    """Encuentra la imagen de portada (og:image) de una página."""
    def __init__(self):
        super().__init__()
        self.url = ""
 
    def handle_starttag(self, etiqueta, atributos):
        if etiqueta == "meta" and not self.url:
            a = dict(atributos)
            if a.get("property") in ("og:image", "og:image:url") or a.get("name") == "twitter:image":
                self.url = a.get("content") or ""
 
 
def _imagen_del_item(item):
    """Busca la imagen de una noticia dentro del propio canal RSS."""
    for etiqueta in (NS_MEDIA + "content", NS_MEDIA + "thumbnail"):
        for el in item.findall(etiqueta):
            tipo = el.get("type") or el.get("medium") or "image"
            if tipo.startswith("image") and _limpiar_url(el.get("url")):
                return _limpiar_url(el.get("url"))
    for el in item.findall("enclosure"):
        if (el.get("type") or "").startswith("image/") and _limpiar_url(el.get("url")):
            return _limpiar_url(el.get("url"))
    for texto in (item.findtext(NS_CONTENIDO + "encoded"), item.findtext("description")):
        buscador = _PrimeraImagen()
        buscador.feed(texto or "")
        if _limpiar_url(buscador.url):
            return _limpiar_url(buscador.url)
    return ""
 
 
def imagen_de_pagina(html, url_pagina=""):
    """Devuelve la imagen de portada (og:image) de una página, o '' si no tiene."""
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="replace")
    buscador = _ImagenDePortada()
    buscador.feed(html)
    if not buscador.url:
        return ""
    return _limpiar_url(urljoin(url_pagina, buscador.url))
 
 
# ---------- Lectura y guardado ----------
def leer_items(xml_bytes):
    """Convierte un canal RSS en una lista de noticias (título, enlace, fecha, texto e imagen)."""
    raiz = ET.fromstring(xml_bytes)
    items = []
    for it in raiz.iter("item"):
        try:
            fecha = parsedate_to_datetime(it.findtext("pubDate")).date()
        except (TypeError, ValueError):
            fecha = None
        items.append({
            "titulo": (it.findtext("title") or "").strip(),
            "enlace": (it.findtext("link") or "").strip(),
            "texto": it.findtext("description") or "",
            "fecha": fecha,
            "imagen": _imagen_del_item(it),
        })
    return items
 
 
def guardar(items, slugs_comunas, palabras=(), fuente="MMA"):
    """Guarda las noticias en la base de datos y las asigna a las comunas indicadas.
 
    Si se entregan `palabras`, solo se guardan las noticias que las mencionen.
    Devuelve un resumen con la cantidad de noticias nuevas, existentes, descartadas y omitidas.
    """
    comunas = list(Comuna.objects.filter(slug__in=slugs_comunas))
    palabras_n = [_normalizar(p) for p in palabras]
    resumen = {"nuevas": 0, "existentes": 0, "descartadas": 0, "omitidas": 0}
 
    for it in items:
        # Omitidas: les falta información o su enlace no cabe en el campo.
        if (not it["titulo"] or not it["enlace"] or not it["fecha"]
                or len(it["enlace"]) > LARGO_MAX_ENLACE):
            resumen["omitidas"] += 1
            continue
        # Descartadas: no mencionan ninguna de las palabras pedidas.
        if palabras_n:
            texto = _normalizar(it["titulo"] + " " + it.get("texto", ""))
            if not any(p in texto for p in palabras_n):
                resumen["descartadas"] += 1
                continue
 
        imagen = _limpiar_url(it.get("imagen"))
        noticia = Noticia.objects.filter(enlace=it["enlace"]).first()
        creada = noticia is None
        if creada:
            noticia = Noticia.objects.create(
                titulo=it["titulo"][:250], fecha=it["fecha"],
                fuente=fuente, enlace=it["enlace"], imagen=imagen)
        elif imagen and not noticia.imagen:
            noticia.imagen = imagen  # completa la imagen de una noticia ya guardada
            noticia.save(update_fields=["imagen"])
        noticia.comunas.add(*comunas)
        resumen["nuevas" if creada else "existentes"] += 1
    return resumen