"""Importa ordenanzas municipales desde BCN para las comunas registradas en Django.

Instalación:
    normativa/management/commands/actualizar_ordenanzas_bcn.py

Ejecución:
    python manage.py actualizar_ordenanzas_bcn

Opciones:
    --solo-ordenanzas   Consulta únicamente ORZ.
    --pausa 0.2         Pausa entre peticiones HTTP.

El comando no consulta el catálogo general cl/organismo. Construye las consultas
usando Comuna.objects.all(), por lo que una comuna nueva se incorpora en la
siguiente ejecución.
"""

import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from comunas.models import Comuna
from normativa.models import Norma


BASE_RECURSO = "http://datos.bcn.cl/recurso"
USER_AGENT = "ChilenosInforma2/1.0 (proyecto academico)"

# Casos en que el nombre/slug de la comuna no coincide con el organismo emisor.
# Quintero-Puchuncaví se consulta contra ambas municipalidades.
ALIAS_ORGANISMOS = {
    "quintero-puchuncavi": (
        "municipalidad-de-quintero",
        "municipalidad-de-puchuncavi",
    ),
}


def normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    texto = "".join(
        caracter for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    return re.sub(r"\s+", " ", texto).strip()


def nombre_predicado(predicado):
    return str(predicado).replace("#", "/").rstrip("/").split("/")[-1].lower()


def valor_rdf(valor):
    if isinstance(valor, dict):
        return valor.get("value") or valor.get("@value") or valor.get("@id") or ""
    return valor or ""


def normalizar_enlace(enlace):
    enlace = (enlace or "").strip().rstrip("/")
    return re.sub(r"/es@[^/]+$", "", enlace)


def parsear_fecha(valor):
    valor = valor_rdf(valor)
    if not valor:
        return None
    texto = str(valor).strip()
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        return None


def extraer_tipo_y_organismo(enlace):
    partes = [parte for parte in urlparse(enlace).path.split("/") if parte]
    try:
        indice = partes.index("cl")
        return partes[indice + 1].lower(), partes[indice + 2].lower()
    except (ValueError, IndexError):
        return "", ""


def slug_comuna(nombre):
    texto = normalizar(nombre)
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")


def slugs_organismo_comuna(comuna):
    """Devuelve los slugs BCN que pueden corresponder a una comuna Django."""
    clave = slug_comuna(comuna.slug or comuna.nombre)
    if clave in ALIAS_ORGANISMOS:
        return ALIAS_ORGANISMOS[clave]

    # Algunos proyectos guardan en slug el nombre completo del organismo.
    if clave.startswith("municipalidad-"):
        return (clave,)
    if clave.startswith("municipalidad-de-"):
        return (clave,)
    return (f"municipalidad-de-{clave}",)


def organismos_desde_comunas(comunas):
    """Construye la lista de organismos exclusivamente desde Comuna en Django."""
    organismos = {}
    for comuna in comunas:
        for slug in slugs_organismo_comuna(comuna):
            if slug not in organismos:
                organismos[slug] = {"nombre": f"Municipalidad asociada a {comuna.nombre}", "slug": slug}
    return list(organismos.values())


def extraer_items_norma(data):
    """Extrae URIs de normas desde la relación RDF bcn-norms#creatorOf."""
    items = {}
    if not isinstance(data, dict):
        return []

    for propiedades in data.values():
        if not isinstance(propiedades, dict):
            continue
        for predicado, valores in propiedades.items():
            if nombre_predicado(predicado) != "creatorof":
                continue
            if not isinstance(valores, list):
                valores = [valores]
            for valor in valores:
                uri = valor_rdf(valor)
                if isinstance(uri, str) and uri.startswith(("http://", "https://")):
                    clave = normalizar_enlace(uri)
                    items[clave] = clave
    return list(items.values())


def extraer_datos_norma(data, enlace):
    if not isinstance(data, dict):
        return None

    nombre = ""
    fecha = None
    tipo = ""

    for propiedades in data.values():
        if not isinstance(propiedades, dict):
            continue
        for predicado, valores in propiedades.items():
            propiedad = nombre_predicado(predicado)
            if not isinstance(valores, list):
                valores = [valores]
            for valor in valores:
                contenido = valor_rdf(valor)
                if not contenido:
                    continue
                if propiedad in {"title", "titulo", "label", "name"} and not nombre:
                    nombre = str(contenido).strip()
                elif propiedad in {"publishdate", "fecha", "date"} and not fecha:
                    fecha = contenido
                elif propiedad in {"type", "tiponorma"} and not tipo:
                    tipo = str(contenido).strip()

    if not nombre:
        return None

    tipo_uri, _ = extraer_tipo_y_organismo(enlace)
    tipo_n = normalizar(tipo)
    titulo_n = normalizar(nombre)
    if tipo_uri == "orz" or "ordenanza" in tipo_n:
        etiqueta = "Ordenanza"
    elif tipo_uri == "dto" or "decreto" in tipo_n or re.search(r"\bdecreto\b", titulo_n):
        etiqueta = "Decreto"
    elif "reglamento" in tipo_n or "reglamento" in titulo_n:
        etiqueta = "Reglamento"
    else:
        etiqueta = "Norma municipal"

    return {
        "nombre": nombre,
        "tipo_norma": etiqueta,
        "fecha_publicacion": parsear_fecha(fecha),
        "enlace_fuente": normalizar_enlace(enlace),
    }


def comunas_del_organismo(slug_organismo, comunas):
    slug_organismo = (slug_organismo or "").lower()
    return [
        comuna for comuna in comunas
        if slug_organismo in slugs_organismo_comuna(comuna)
    ]


def comunas_mencionadas_en_titulo(titulo, comunas):
    texto = normalizar(titulo)
    encontradas = []
    for comuna in comunas:
        nombre = normalizar(comuna.nombre)
        if not nombre:
            continue
        patron = rf"(?<![a-z0-9]){re.escape(nombre)}(?![a-z0-9])"
        if re.search(patron, texto):
            encontradas.append(comuna)
            continue
        partes = [p.strip() for p in nombre.split("-") if p.strip()]
        if len(partes) > 1 and all(
            re.search(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", texto)
            for p in partes
        ):
            encontradas.append(comuna)
    return encontradas


class Command(BaseCommand):
    help = "Importa ordenanzas municipales desde BCN para las comunas registradas en Django."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pausa", type=float, default=0.2,
            help="Segundos de pausa entre peticiones (predeterminado: 0.2).",
        )
        parser.add_argument(
            "--solo-ordenanzas", action="store_true",
            help="Importa únicamente normas ORZ; omite decretos relacionados.",
        )

    def handle(self, *args, **opciones):
        pausa = max(0, opciones["pausa"])
        comunas = list(Comuna.objects.all())

        self.stdout.write(self.style.MIGRATE_HEADING(
            "Consultando ordenanzas municipales de las comunas registradas..."
        ))
        self.stdout.write(f"Comunas actualmente registradas en Django: {len(comunas)}")
        if not comunas:
            raise CommandError("No hay comunas registradas en Django. No se consultó la BCN.")

        organismos = organismos_desde_comunas(comunas)
        self.stdout.write(f"Municipalidades que se consultarán: {len(organismos)}")
        for organismo in organismos:
            self.stdout.write(f"  - {organismo['slug']}")

        self.errores_lectura = []
        registros = self._recopilar_normas(organismos, pausa, opciones["solo_ordenanzas"])
        if registros is None:
            raise CommandError(
                "No fue posible completar la consulta a la BCN. No se modificó la base de datos."
            )

        self.stdout.write(f"Documentos municipales recopilados: {len(registros)}")
        resumen = self._guardar(registros, comunas)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Importación terminada."))
        for clave, valor in resumen.items():
            if clave != "por_comuna":
                self.stdout.write(f"{clave.replace('_', ' ').capitalize()}: {valor}")

        self.stdout.write("\nNormas asociadas por comuna:")
        for nombre_comuna, cantidad in resumen["por_comuna"].items():
            self.stdout.write(f"  - {nombre_comuna}: {cantidad}")

        self.stdout.write(f"\nDocumentos pendientes por error de lectura: {len(self.errores_lectura)}")
        for error in self.errores_lectura:
            self.stdout.write(self.style.WARNING(f"  - {error['url']} ({error['detalle']})"))

    def _solicitar_json(self, url):
        """Solicita RDF/JSON; reintenta y prueba HTTPS si HTTP no entrega JSON."""
        urls = [url]
        if url.startswith("http://"):
            urls.append("https://" + url[len("http://"):])

        ultimo_error = None
        for url_actual in urls:
            for intento in range(1, 4):
                solicitud = urllib.request.Request(
                    url_actual,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/rdf+json, application/json",
                    },
                )
                try:
                    with urllib.request.urlopen(solicitud, timeout=60) as respuesta:
                        cuerpo = respuesta.read().decode("utf-8", errors="replace")
                    if not cuerpo.strip():
                        raise ValueError(f"Respuesta vacía desde {url_actual}")
                    try:
                        return json.loads(cuerpo)
                    except json.JSONDecodeError as error:
                        muestra = cuerpo[:100].replace("\n", " ").strip()
                        raise ValueError(
                            f"Respuesta no JSON desde {url_actual}: {error}; "
                            f"inicio de respuesta: {muestra!r}"
                        ) from error
                except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError) as error:
                    ultimo_error = error
                    # No repetir errores HTTP permanentes (por ejemplo, 404).
                    if isinstance(error, urllib.error.HTTPError) and error.code not in {408, 429, 500, 502, 503, 504}:
                        break
                    if intento < 3:
                        time.sleep(0.5 * intento)

        if isinstance(ultimo_error, urllib.error.HTTPError):
            raise ultimo_error
        raise ValueError(f"Fallaron los intentos para {url}: {ultimo_error}") from ultimo_error

    def _recopilar_normas(self, organismos, pausa, solo_ordenanzas):
        registros = {}
        total_organismos = len(organismos)
        errores_graves = 0

        for indice, organismo in enumerate(organismos, start=1):
            slug_org = organismo["slug"]
            tipos = ("orz",) if solo_ordenanzas else ("orz", "dto")
            self.stdout.write(f"Municipalidad {indice}/{total_organismos}: {slug_org}")

            for tipo in tipos:
                url_indice = f"{BASE_RECURSO}/cl/{tipo}/{slug_org}/datos.json"
                try:
                    data_indice = self._solicitar_json(url_indice)
                    enlaces = extraer_items_norma(data_indice)
                except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError) as error:
                    self.stderr.write(self.style.WARNING(
                        f"No se pudo consultar {tipo.upper()} de {slug_org}: {error}"
                    ))
                    # Un 404 puede significar que ese municipio no tiene normas de ese tipo.
                    if not isinstance(error, urllib.error.HTTPError) or error.code != 404:
                        errores_graves += 1
                    continue

                self.stdout.write(f"  {tipo.upper()}: {len(enlaces)} referencias")
                for enlace in enlaces:
                    tipo_uri, slug_uri = extraer_tipo_y_organismo(enlace)
                    if tipo_uri not in {"orz", "dto"} or slug_uri != slug_org:
                        continue
                    try:
                        datos = extraer_datos_norma(
                            self._solicitar_json(f"{enlace}/datos.json"), enlace
                        )
                    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError) as error:
                        detalle = str(error)
                        self.stderr.write(self.style.WARNING(
                            f"No se pudo leer una norma ({enlace}): {detalle}"
                        ))
                        self.errores_lectura.append({"url": enlace, "detalle": detalle})
                        errores_graves += 1
                        continue

                    if not datos:
                        continue
                    if tipo_uri == "dto" and "ordenanza" not in normalizar(datos["nombre"]):
                        continue

                    datos["organismo_slug"] = slug_org
                    registros[datos["enlace_fuente"]] = datos
                    if pausa:
                        time.sleep(pausa)

                if pausa:
                    time.sleep(pausa)

            self.stdout.write(f"  Documentos acumulados: {len(registros)}")

        # Si todos los índices fallaron por razones distintas a 404, abortamos
        # antes de tocar la base de datos para evitar una falsa importación vacía.
        if errores_graves and not registros:
            return None
        return list(registros.values())

    @transaction.atomic
    def _guardar(self, registros, comunas):
        resumen = {
            "nuevas": 0,
            "actualizadas": 0,
            "asociaciones_comunales": 0,
            "sin_comuna_registrada": 0,
            "omitidas": 0,
            "por_comuna": {},
        }

        por_enlace = {}
        for norma in Norma.objects.all().prefetch_related("comunas"):
            clave = normalizar_enlace(norma.enlace_fuente)
            if clave:
                por_enlace.setdefault(clave, norma)

        total = len(registros)
        normas_procesadas_ids = set()
        for indice, datos in enumerate(registros, start=1):
            enlace = datos["enlace_fuente"]
            nombre = datos["nombre"]
            if not enlace or not nombre:
                resumen["omitidas"] += 1
                continue

            _, organismo_slug = extraer_tipo_y_organismo(enlace)
            destino = comunas_del_organismo(organismo_slug, comunas)
            if not destino:
                destino = comunas_mencionadas_en_titulo(nombre, comunas)

            norma = por_enlace.get(enlace)
            if norma is None:
                norma = Norma.objects.create(
                    nombre=nombre[:250],
                    tipo_norma=datos["tipo_norma"],
                    fecha_publicacion=datos["fecha_publicacion"],
                    enlace_fuente=enlace,
                    ambito="COMUNAL",
                )
                por_enlace[enlace] = norma
                resumen["nuevas"] += 1
            else:
                cambios = []
                for campo, valor in (
                    ("nombre", nombre[:250]),
                    ("tipo_norma", datos["tipo_norma"]),
                    ("ambito", "COMUNAL"),
                ):
                    if getattr(norma, campo) != valor:
                        setattr(norma, campo, valor)
                        cambios.append(campo)
                if datos["fecha_publicacion"] and norma.fecha_publicacion != datos["fecha_publicacion"]:
                    norma.fecha_publicacion = datos["fecha_publicacion"]
                    cambios.append("fecha_publicacion")
                if cambios:
                    norma.save(update_fields=cambios)
                resumen["actualizadas"] += 1

            norma.comunas.set(destino)
            normas_procesadas_ids.add(norma.pk)
            if destino:
                resumen["asociaciones_comunales"] += 1
            else:
                resumen["sin_comuna_registrada"] += 1

            if indice % 100 == 0 or indice == total:
                self.stdout.write(f"Guardando {indice}/{total}...")

        # Reasocia normas ya importadas si se agregó una comuna después.
        slugs_consultables = {
            slug for comuna in comunas for slug in slugs_organismo_comuna(comuna)
        }
        for norma in Norma.objects.all().prefetch_related("comunas"):
            tipo, organismo_slug = extraer_tipo_y_organismo(norma.enlace_fuente)
            if organismo_slug not in slugs_consultables:
                continue
            if tipo == "orz":
                es_importable = True
            elif tipo == "dto" and "ordenanza" in normalizar(norma.nombre):
                es_importable = True
            else:
                es_importable = False
            if not es_importable:
                continue

            destino = comunas_del_organismo(organismo_slug, comunas)
            if not destino:
                destino = comunas_mencionadas_en_titulo(norma.nombre, comunas)
            if norma.ambito != "COMUNAL":
                norma.ambito = "COMUNAL"
                norma.save(update_fields=["ambito"])
            norma.comunas.set(destino)

        # Cuenta normas únicas asociadas a cada comuna en esta ejecución.
        for comuna in comunas:
            cantidad = Norma.objects.filter(
                pk__in=normas_procesadas_ids,
                comunas=comuna,
            ).distinct().count()
            resumen["por_comuna"][comuna.nombre] = cantidad

        return resumen
