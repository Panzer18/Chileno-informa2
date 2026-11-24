import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from comunas.models import Comuna

from .models import Norma

BASE_MMA = "https://mma.gob.cl"

FEEDS_ESPECIALES = {
    "quintero-puchuncavi": [f"{BASE_MMA}/tag/quintero-y-puchuncavi/feed/"],
}

# Reglas estrictas: (Etiqueta en BD, patrones regex sobre texto normalizado sin tildes)
REGLAS_TIPO_NORMA = (
    ("Ley", (r"\bley\b", r"\bleyes\b", r"\bproyecto de ley\b")),
    ("Decreto", (r"\bdecreto\b", r"\bdecreto supremo\b", r"\bd\.s\.\b")),
    ("Resolución", (r"\bresolucion\b", r"\bresolucion exenta\b")),
    ("Reglamento", (r"\breglamento\b",)),
    ("Ordenanza", (r"\bordenanza\b",)),
    (
        "Plan",
        (
            r"\bplan de prevencion\b",
            r"\bplan de descontaminacion\b",
            r"\bplan regulador\b",
            r"\bplan de manejo\b",
            r"\bplan de accion\b",
            r"\bppda\b",
        ),
    ),
    (
        "Norma",
        (
            r"\bnorma primaria\b",
            r"\bnorma secundaria\b",
            r"\bnorma de emision\b",
            r"\bnorma de calidad\b",
            r"\bnormativa ambiental\b",
        ),
    ),
)

# Exige además señales de acto normativo/regulatorio (promulgación, aprobación, consulta pública, etc.)
# para evitar notas meramente protocolares ("realizan balance del PPDA", "se despliega para informar").
SENALES_ACTO_NORMATIVO = (
    r"\bley\b",
    r"\bdecreto\b",
    r"\bresolucion\b",
    r"\breglamento\b",
    r"\bordenanza\b",
    r"\bpromulga\b",
    r"\baprueba\b",
    r"\bmodifica\b",
    r"\bpublica en el diario oficial\b",
    r"\bdiario oficial\b",
    r"\bconsulta publica\b",
    r"\banteproyecto\b",
    r"\bentrada en vigencia\b",
    r"\bnorma primaria\b",
    r"\bnorma secundaria\b",
    r"\bnorma de emision\b",
    r"\bnorma de calidad\b",
)


def _normalizar(texto):
    """Minúsculas y sin tildes."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _parsear_fecha(texto_fecha):
    if not texto_fecha:
        return None
    texto_fecha = texto_fecha.strip()
    try:
        return parsedate_to_datetime(texto_fecha).date()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(texto_fecha.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def detectar_tipo_norma(titulo, texto=""):
    """Devuelve el tipo de instrumento normativo si corresponde, o None si es solo una noticia."""
    contenido = _normalizar(f"{titulo} {texto}")

    # Debe tener al menos una señal real de acto o instrumento normativo
    if not any(re.search(patron, contenido) for patron in SENALES_ACTO_NORMATIVO):
        return None

    for etiqueta, patrones in REGLAS_TIPO_NORMA:
        if any(re.search(patron, contenido) for patron in patrones):
            return etiqueta[:100]

    return None


def terminos_busqueda(nombre):
    """Genera términos de búsqueda para una comuna."""
    terminos = []
    for parte in (nombre or "").split("-"):
        parte = parte.strip()
        if parte:
            terminos.append(f'"{parte}"' if " " in parte else parte)
    return terminos


def urls_para(comuna):
    """Devuelve las URLs de canales/búsquedas del MMA asociadas a una comuna, sin duplicados."""
    urls = [f"{BASE_MMA}/tag/{comuna.slug}/feed/"]
    urls.extend(FEEDS_ESPECIALES.get(comuna.slug, []))
    for termino in terminos_busqueda(comuna.nombre):
        urls.append(f"{BASE_MMA}/?s={quote_plus(termino)}&feed=rss2")
    return list(dict.fromkeys(urls))


def leer_items_rss(xml_bytes):
    """Convierte un XML RSS en una lista de ítems (título, enlace, fecha y texto)."""
    raiz = ET.fromstring(xml_bytes)
    items = []

    for it in raiz.iter("item"):
        fecha_raw = it.findtext("pubDate") or it.findtext("dc:date")
        items.append({
            "titulo": (it.findtext("title") or "").strip(),
            "enlace": (it.findtext("link") or "").strip(),
            "texto": it.findtext("description") or "",
            "fecha": _parsear_fecha(fecha_raw),
        })

    return items


def guardar_normativas(items, slugs_comunas, solo_normativas=True):
    """Guarda en `Norma` solo ítems que correspondan a leyes, decretos, resoluciones o planes normativos."""
    comunas = list(Comuna.objects.filter(slug__in=slugs_comunas))
    resumen = {"nuevas": 0, "existentes": 0, "descartadas": 0, "omitidas": 0}

    for it in items:
        if not it.get("titulo") or not it.get("enlace") or not it.get("fecha"):
            resumen["omitidas"] += 1
            continue

        tipo = detectar_tipo_norma(it["titulo"], it.get("texto", ""))
        if solo_normativas and tipo is None:
            resumen["descartadas"] += 1
            continue

        norma = Norma.objects.filter(enlace_fuente=it["enlace"]).first()
        creada = norma is None
        if creada:
            norma = Norma.objects.create(
                nombre=it["titulo"][:250],
                tipo_norma=tipo or "Norma",
                fecha_publicacion=it["fecha"],
                enlace_fuente=it["enlace"],
            )
        if comunas:
            norma.comunas.add(*comunas)
        resumen["nuevas" if creada else "existentes"] += 1

    return resumen