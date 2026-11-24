import html
import re
import unicodedata
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

from django.utils import timezone

from comunas.models import Comuna
from noticias.models import Noticia

LARGO_MAX_ENLACE = 200
FUENTE_BCN = "BCN"

URL_LISTADO_BCN = (
    "https://www.bcn.cl/leychile/consulta/listado_n_sel"
    "?comp=&agr=2&_grupo_aporte=&sub=1181"
)

FEEDS_BCN_GENERALES = [
    URL_LISTADO_BCN,
]

FEEDS_BCN_POR_COMUNA = {}

PALABRAS_MEDIO_AMBIENTE = (
    "medio ambiente",
    "ambiental",
    "humedal",
    "contaminacion",
    "contaminación",
    "calidad del aire",
    "residuos",
    "agua",
    "forestal",
    "climatico",
    "climático",
)


class _NormasHtmlParser(HTMLParser):
    """Extrae enlaces de normas de Ley Chile/BCN desde HTML."""

    def __init__(self, base_url=""):
        super().__init__()
        self.base_url = base_url
        self._en_a = False
        self._href = ""
        self._texto = []
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = (dict(attrs).get("href") or "").strip()
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                self._en_a = True
                self._href = urljoin(self.base_url, href) if self.base_url else href
                self._texto = []

    def handle_data(self, data):
        if self._en_a:
            self._texto.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._en_a:
            titulo = re.sub(r"\s+", " ", "".join(self._texto)).strip()
            es_norma = (
                "idnorma=" in self._href.lower()
                or "/navegar" in self._href.lower()
                or "/norma" in self._href.lower()
            )
            if es_norma and len(titulo) >= 5:
                self.items.append({
                    "titulo": html.unescape(titulo),
                    "enlace": self._href,
                    "texto": "",
                    "fecha": None,
                })
            self._en_a = False
            self._href = ""
            self._texto = []


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def urls_bcn_para(comuna):
    urls = list(FEEDS_BCN_GENERALES)
    urls.extend(FEEDS_BCN_POR_COMUNA.get(comuna.slug, []))
    return list(dict.fromkeys(urls))


def leer_normativas(contenido_bytes, url_origen=""):
    """Lee un feed RSS/XML o extrae enlaces de normas desde HTML de Ley Chile/BCN."""
    texto_inicio = contenido_bytes.lstrip()[:300].lower()
    if texto_inicio.startswith((b"<!doctype html", b"<html")):
        parser = _NormasHtmlParser(base_url=url_origen)
        parser.feed(contenido_bytes.decode("utf-8", errors="replace"))

        vistos = set()
        unicos = []
        for it in parser.items:
            if it["enlace"] not in vistos:
                vistos.add(it["enlace"])
                unicos.append(it)
        return unicos

    raiz = ET.fromstring(contenido_bytes)
    items = []
    for it in raiz.iter("item"):
        fecha_texto = it.findtext("pubDate") or it.findtext("dc:date")
        try:
            fecha = parsedate_to_datetime(fecha_texto).date() if fecha_texto else None
        except (TypeError, ValueError):
            fecha = None

        items.append({
            "titulo": (it.findtext("title") or "").strip(),
            "enlace": (it.findtext("link") or "").strip(),
            "texto": it.findtext("description") or "",
            "fecha": fecha,
        })
    return items


def es_normativa_ambiental(item, palabras_extra=()):
    contenido = _normalizar(f"{item.get('titulo', '')} {item.get('texto', '')}")
    claves = [_normalizar(p) for p in (*PALABRAS_MEDIO_AMBIENTE, *palabras_extra)]
    return any(p in contenido for p in claves if p)


def guardar_normativas(items, slugs_comunas, solo_ambientales=True, fuente=FUENTE_BCN):
    """Guarda normativas en `Noticia` y las asocia a las comunas indicadas sin duplicar."""
    comunas = list(Comuna.objects.filter(slug__in=slugs_comunas))
    resumen = {"nuevas": 0, "existentes": 0, "descartadas": 0, "omitidas": 0}

    for it in items:
        fecha = it.get("fecha")
        if (
            not it.get("titulo")
            or not it.get("enlace")
            or not fecha
            or len(it["enlace"]) > LARGO_MAX_ENLACE
        ):
            resumen["omitidas"] += 1
            continue

        if solo_ambientales and not es_normativa_ambiental(it):
            resumen["descartadas"] += 1
            continue

        noticia = Noticia.objects.filter(enlace=it["enlace"]).first()
        creada = noticia is None
        if creada:
            noticia = Noticia.objects.create(
                titulo=it["titulo"][:250],
                fecha=fecha,
                fuente=fuente,
                enlace=it["enlace"],
            )
        noticia.comunas.add(*comunas)
        resumen["nuevas" if creada else "existentes"] += 1

    return resumen