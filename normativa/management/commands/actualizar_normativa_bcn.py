
import json
import re
import time
import unicodedata
import urllib.request

from datetime import datetime
from urllib.error import HTTPError

from django.core.management.base import BaseCommand

from comunas.models import Comuna
from normativa.models import Norma


BASE_RECURSO = "http://datos.bcn.cl/recurso"

USER_AGENT = "ChilenosInforma2/1.0 (proyecto academico IWG400)"

RUTAS_BCN = [
    "cl/dto/ministerio-del-medio-ambiente",
]

CLAVES_AMBIENTALES = (
    "medio ambiente",
    "ambiental",
    "humedal",
    "descontaminacion",
    "prevencion",
    "residuo",
    "reciclaje",
    "cambio climatico",
    "area protegida",
    "biodiversidad",
    "contaminacion",
    "conservacion",
    "ecosistema",
    "agua",
    "bosque",
)


# --------------------------------------------------
# FUNCIONES AUXILIARES
# --------------------------------------------------

def _normalizar(texto):
    texto = unicodedata.normalize(
        "NFD",
        (texto or "").lower()
    )

    return "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )


def _normalizar_enlace(enlace):
    """
    Elimina el sufijo de idioma/versión de BCN.

    Ejemplo:
    /27/es@2012-11-28 -> /27
    """

    enlace = (enlace or "").strip().rstrip("/")

    enlace = re.sub(
        r"/es@[^/]+$",
        "",
        enlace
    )

    return enlace


def _nombre_predicado(predicado):
    return (
        str(predicado)
        .replace("#", "/")
        .rstrip("/")
        .split("/")[-1]
        .lower()
    )


def _parsear_fecha(valor):

    if not valor:
        return None

    if isinstance(valor, dict):
        valor = valor.get("@value") or valor.get("value")

    if not isinstance(valor, str):
        return None

    limpio = valor.strip()[:10]

    try:
        return datetime.strptime(
            limpio,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        return None


def _detectar_tipo(titulo, tipo_raw=""):

    cuerpo = _normalizar(
        f"{titulo} {tipo_raw}"
    )

    for etiqueta, patron in (
        ("Ley", r"\bley\b"),
        ("Decreto", r"\bdecreto\b|\bdto\b"),
        ("Resolución", r"\bresolucion\b|\bres\b"),
        ("Reglamento", r"\breglamento\b"),
        ("Ordenanza", r"\bordenanza\b|\borz\b"),
    ):

        if re.search(patron, cuerpo):
            return etiqueta

    return str(tipo_raw).strip()[:100] or "Norma"


# --------------------------------------------------
# DETECCIÓN DE COMUNAS Y REGIONES
# --------------------------------------------------

REGIONES_CHILE = [
    "Arica y Parinacota",
    "Tarapacá",
    "Antofagasta",
    "Atacama",
    "Coquimbo",
    "Valparaíso",
    "Metropolitana de Santiago",
    "Metropolitana",
    "Libertador General Bernardo O'Higgins",
    "O'Higgins",
    "Maule",
    "Ñuble",
    "Biobío",
    "La Araucanía",
    "Araucanía",
    "Los Ríos",
    "Los Lagos",
    "Aysén",
    "Aysén del General Carlos Ibáñez del Campo",
    "Magallanes y de la Antártica Chilena",
    "Magallanes",
]


def _comunas_que_calzan(texto_norma, todas_las_comunas):
    """Devuelve únicamente las comunas registradas que aparecen en el texto."""

    texto_n = _normalizar(texto_norma)
    coincidentes = []

    for comuna in todas_las_comunas:
        nombre = _normalizar(comuna.nombre).strip()

        if not nombre:
            continue

        if re.search(rf"\b{re.escape(nombre)}\b", texto_n):
            coincidentes.append(comuna)
            continue

        partes = [
            parte.strip()
            for parte in nombre.split("-")
            if parte.strip()
        ]

        if len(partes) > 1:
            todas_presentes = all(
                re.search(rf"\b{re.escape(parte)}\b", texto_n)
                for parte in partes
            )

            if todas_presentes:
                coincidentes.append(comuna)

    return coincidentes


def _comunas_mencionadas_expresamente(titulo, todas_las_comunas):
    """Busca comunas registradas mencionadas en el título completo."""

    return _comunas_que_calzan(titulo, todas_las_comunas)


def _menciona_territorio_local(titulo):
    """Detecta referencias a comunas, ciudades o localidades específicas."""

    texto_n = _normalizar(titulo)

    patrones = (
        r"\bcomunas?\b",
        r"\blocalidades?\b",
        r"\bciudades?\b",
        r"\bsectores\s+aleda[nñ]os\b",
        r"\bzona\s+circundante\b",
    )

    return any(re.search(patron, texto_n) for patron in patrones)


def _es_nombramiento_de_autoridad(titulo):
    """Evita tratar el nombramiento de una autoridad regional como norma regional."""

    texto_n = _normalizar(titulo)

    es_accion = re.search(r"\b(nombra|designa)\b", texto_n)

    es_autoridad = re.search(
        r"\b(seremi|secretario[s]? regional(es)? ministerial(es)?)\b",
        texto_n,
    )

    return bool(es_accion and es_autoridad)


def _obtener_nombre_region(region):
    """Normaliza nombres como 'Región de Valparaíso' a 'valparaiso'."""

    region_n = _normalizar(region).strip()

    region_n = re.sub(
        r"^region\s+(?:(?:de|del|la|los|las)\s+)?",
        "",
        region_n,
    )

    region_n = re.sub(r"^region\s+", "", region_n)

    return region_n.strip()


def _regiones_mencionadas(titulo, todas_las_comunas=None):
    """Detecta regiones chilenas sin depender de la tabla Comuna."""

    texto_n = _normalizar(titulo)
    regiones = set()

    for region in REGIONES_CHILE:

        region_n = _normalizar(region)

        patron = (
            rf"\bregion\s+"
            rf"(?:(?:de|del|la|los|las)\s+)?"
            rf"{re.escape(region_n)}\b"
        )

        if re.search(patron, texto_n):
            regiones.add(region_n)

    return regiones


def _detectar_ambito(titulo, todas_las_comunas):
    """Clasifica como COMUNAL, REGIONAL o NACIONAL."""

    if _menciona_territorio_local(titulo):

        comunas = _comunas_mencionadas_expresamente(
            titulo,
            todas_las_comunas,
        )

        return "COMUNAL", comunas, set()

    if _es_nombramiento_de_autoridad(titulo):
        return "NACIONAL", [], set()

    regiones = _regiones_mencionadas(titulo)

    if regiones:
        return "REGIONAL", [], regiones

    return "NACIONAL", [], set()


# --------------------------------------------------
# EXTRACCIÓN DE DATOS RDF/JSON DE BCN
# --------------------------------------------------

def _extraer_items_json(data):

    items = []

    if not isinstance(data, dict):
        return items

    for sujeto, propiedades in data.items():

        if not isinstance(propiedades, dict):
            continue

        for predicado, valores in propiedades.items():

            if _nombre_predicado(predicado) != "creatorof":
                continue

            if not isinstance(valores, list):
                valores = [valores]

            for valor in valores:

                if not isinstance(valor, dict):
                    continue

                uri = valor.get("value")

                if valor.get("type") == "uri" and uri:

                    items.append({
                        "enlace_fuente": str(uri).strip()
                    })

    unicos = {}

    for item in items:

        enlace = item["enlace_fuente"]
        clave = _normalizar_enlace(enlace)

        if clave not in unicos:
            unicos[clave] = item

    return list(unicos.values())


def _extraer_datos_norma(data, enlace):

    if not isinstance(data, dict):
        return None

    nombre = ""
    fecha = None
    tipo = ""
    codigo_leychile = ""

    for sujeto, propiedades in data.items():

        if not isinstance(propiedades, dict):
            continue

        for predicado, valores in propiedades.items():

            propiedad = _nombre_predicado(predicado)

            if not isinstance(valores, list):
                valores = [valores]

            for valor in valores:

                if isinstance(valor, dict):

                    contenido = (
                        valor.get("value")
                        or valor.get("@value")
                        or ""
                    )

                else:
                    contenido = valor

                if propiedad in (
                    "title",
                    "titulo",
                    "label",
                    "name"
                ):

                    if contenido and not nombre:
                        nombre = str(contenido).strip()

                elif propiedad in (
                    "publishdate",
                    "fecha",
                    "date"
                ):

                    if contenido and not fecha:
                        fecha = contenido

                elif propiedad in (
                    "type",
                    "tiponorma"
                ):

                    if contenido:
                        tipo = str(contenido)

                elif propiedad == "leychilecode":

                    if contenido:
                        codigo_leychile = str(contenido).strip()

    if not nombre:
        return None

    enlace_bcn = _normalizar_enlace(enlace)

    if codigo_leychile.isdigit():

        enlace_publico = (
            "https://www.bcn.cl/leychile/navegar"
            f"?idNorma={codigo_leychile}"
        )

    else:
        # No inventar códigos cuando BCN no entrega uno.
        enlace_publico = enlace_bcn

    return {
        "nombre": nombre,
        "tipo_norma": _detectar_tipo(nombre, tipo),
        "fecha_publicacion": _parsear_fecha(fecha),
        "enlace_fuente": enlace_publico,
        "enlace_bcn": enlace_bcn,
    }


# --------------------------------------------------
# COMANDO DJANGO
# --------------------------------------------------

class Command(BaseCommand):

    help = (
        "Consulta normas ambientales de BCN "
        "y las clasifica por ámbito territorial."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--comuna",
            help="Limita las asociaciones a una comuna mediante su slug."
        )

        parser.add_argument(
            "--ext",
            default="json",
            help="Extensión de representación BCN."
        )

        parser.add_argument(
            "--pausa",
            type=float,
            default=1.0,
            help="Pausa entre peticiones."
        )

        parser.add_argument(
            "--sin-filtro",
            action="store_true",
            help="Guarda todas las normas encontradas."
        )

        parser.add_argument(
            "--solo-locales",
            action="store_true",
            help="Guarda únicamente normas comunales."
        )

    # --------------------------------------------------
    # EJECUCIÓN PRINCIPAL
    # --------------------------------------------------

    def handle(self, *args, **opciones):

        todas_las_comunas = list(
            Comuna.objects.all()
        )

        if not todas_las_comunas:

            self.stderr.write(
                self.style.WARNING(
                    "No hay comunas en la base de datos."
                )
            )

            return

        if opciones["comuna"]:

            comunas_objetivo = [
                c for c in todas_las_comunas
                if c.slug == opciones["comuna"]
            ]

            if not comunas_objetivo:

                self.stderr.write(
                    self.style.ERROR(
                        f"No existe la comuna '{opciones['comuna']}'."
                    )
                )

                return

        else:

            comunas_objetivo = todas_las_comunas

        ext = opciones["ext"].lstrip(".")

        total_nuevas = 0
        total_existentes = 0

        for ruta in RUTAS_BCN:

            url = (
                f"{BASE_RECURSO}/"
                f"{ruta.strip('/')}/datos.{ext}"
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"Consultando índice: {url}"
                )
            )

            items = self._descargar_items(
                url,
                ext
            )

            if items is None:
                continue

            self.stdout.write(
                f"Normas encontradas: {len(items)}"
            )

            resumen = self._guardar(
                items,
                todas_las_comunas=todas_las_comunas,
                comunas_objetivo=comunas_objetivo,
                filtrar=not opciones["sin_filtro"],
                solo_locales=opciones["solo_locales"],
                ext=ext,
                pausa=opciones["pausa"],
            )

            self.stdout.write(
                f"Resultado: {resumen}"
            )

            total_nuevas += resumen["nuevas"]
            total_existentes += resumen["existentes"]

        self.stdout.write(
            self.style.SUCCESS(
                "\nProceso finalizado."
            )
        )

        self.stdout.write(
            f"Normas nuevas: {total_nuevas}"
        )

        self.stdout.write(
            f"Normas existentes: {total_existentes}"
        )

    # --------------------------------------------------
    # DESCARGAS
    # --------------------------------------------------

    def _descargar_items(self, url, ext):

        try:

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "application/rdf+json, "
                        "application/json, */*"
                    ),
                },
            )

            with urllib.request.urlopen(
                req,
                timeout=30
            ) as resp:

                cuerpo = resp.read().decode(
                    "utf-8",
                    errors="replace"
                )

            data = json.loads(cuerpo)

            return _extraer_items_json(data)

        except HTTPError as err:

            self.stderr.write(
                self.style.ERROR(
                    f"Error HTTP {err.code}: {url}"
                )
            )

        except (
            OSError,
            json.JSONDecodeError
        ) as err:

            self.stderr.write(
                self.style.ERROR(
                    f"Error al descargar índice: {err}"
                )
            )

        return None

    def _descargar_datos_norma(self, enlace, ext):

        url = (
            f"{enlace.rstrip('/')}/datos.{ext}"
        )

        try:

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "application/rdf+json, "
                        "application/json, */*"
                    ),
                },
            )

            with urllib.request.urlopen(
                req,
                timeout=30
            ) as resp:

                cuerpo = resp.read().decode(
                    "utf-8",
                    errors="replace"
                )

            if not cuerpo.strip():

                self.stderr.write(
                    self.style.WARNING(
                        f"Respuesta vacía al consultar norma: {url}"
                    )
                )

                return None

            try:
                data = json.loads(cuerpo)

            except json.JSONDecodeError as err:

                self.stderr.write(
                    self.style.WARNING(
                        f"La respuesta no es JSON válido ({err}): {url}"
                    )
                )

                return None

            return _extraer_datos_norma(
                data,
                enlace
            )

        except HTTPError as err:

            self.stderr.write(
                self.style.WARNING(
                    f"HTTP {err.code} al consultar norma: {enlace}"
                )
            )

        except (
            OSError,
            json.JSONDecodeError
        ) as err:

            self.stderr.write(
                self.style.WARNING(
                    f"Error al consultar norma: {err}"
                )
            )

        return None

    # --------------------------------------------------
    # GUARDADO Y CLASIFICACIÓN
    # --------------------------------------------------

    def _guardar(
        self,
        items,
        todas_las_comunas,
        comunas_objetivo,
        filtrar=True,
        solo_locales=False,
        ext="json",
        pausa=1.0,
    ):

        resumen = {
            "nuevas": 0,
            "existentes": 0,
            "locales": 0,
            "regionales": 0,
            "generales": 0,
            "descartadas": 0,
            "omitidas": 0,
        }

        slugs_objetivo = {
            comuna.slug for comuna in comunas_objetivo
        }

        todos_los_slugs = {
            comuna.slug for comuna in todas_las_comunas
        }

        ejecucion_completa = (
            slugs_objetivo == todos_los_slugs
        )

        # --------------------------------------------------
        # INDEXAR NORMAS EXISTENTES
        # --------------------------------------------------

        normas_existentes = list(
            Norma.objects.all().prefetch_related("comunas")
        )

        por_enlace = {}
        por_enlace_publico = {}

        for existente in normas_existentes:

            enlace_bcn = existente.enlace_bcn or ""

            # Compatibilidad con registros antiguos:
            # anteriormente la URI BCN se guardaba en enlace_fuente.
            if (
                not enlace_bcn
                and "datos.bcn.cl/recurso/" in existente.enlace_fuente
            ):

                enlace_bcn = _normalizar_enlace(
                    existente.enlace_fuente
                )

                existente.enlace_bcn = enlace_bcn

                existente.save(
                    update_fields=["enlace_bcn"]
                )

            if enlace_bcn:

                clave = _normalizar_enlace(enlace_bcn)

                if clave in por_enlace:

                    principal = por_enlace[clave]

                    asociaciones = list(
                        existente.comunas.all()
                    )

                    if asociaciones:
                        principal.comunas.add(*asociaciones)

                    existente.delete()
                    continue

                por_enlace[clave] = existente

            enlace_publico = (
                existente.enlace_fuente or ""
            ).strip()

            if enlace_publico:
                por_enlace_publico[enlace_publico] = existente

        total = len(items)

        # Conserva los títulos completos recibidos desde BCN durante
        # esta ejecución, aunque el modelo limite nombre a 250 caracteres.
        titulos_completos_por_pk = {}

        # --------------------------------------------------
        # PROCESAR NORMAS
        # --------------------------------------------------

        for indice, item in enumerate(items, start=1):

            self.stdout.write(
                f"Procesando norma {indice}/{total}..."
            )

            enlace_original = (
                item.get("enlace_fuente") or ""
            ).strip()

            if not enlace_original:

                resumen["omitidas"] += 1
                continue

            datos = self._descargar_datos_norma(
                enlace_original,
                ext,
            )

            if not datos:

                resumen["omitidas"] += 1

                if indice < total:
                    time.sleep(max(0, pausa))

                continue

            nombre = (
                datos.get("nombre") or ""
            ).strip()

            if not nombre:

                resumen["omitidas"] += 1
                continue

            # --------------------------------------------------
            # IDENTIFICAR LA NORMA ANTES DEL FILTRO
            # --------------------------------------------------

            enlace_bcn = _normalizar_enlace(
                datos.get("enlace_bcn") or enlace_original
            )

            enlace_publico = (
                datos.get("enlace_fuente") or enlace_bcn
            )

            # Buscar primero mediante la URI original de BCN.
            norma = por_enlace.get(enlace_bcn)

            # Recuperar registros antiguos si no tienen enlace_bcn.
            if norma is None:
                norma = por_enlace_publico.get(enlace_publico)

            # --------------------------------------------------
            # FILTRO DE CONTENIDO AMBIENTAL
            # --------------------------------------------------

            # Los registros existentes se actualizan aunque su título
            # no contenga las palabras del filtro ambiental.
            if filtrar and norma is None:

                texto_n = _normalizar(nombre)

                es_ambiental = any(
                    _normalizar(clave) in texto_n
                    for clave in CLAVES_AMBIENTALES
                )

                if not es_ambiental:

                    resumen["descartadas"] += 1

                    if indice < total:
                        time.sleep(max(0, pausa))

                    continue

            ambito, comunas_detectadas, regiones_detectadas = (
                _detectar_ambito(
                    nombre,
                    todas_las_comunas
                )
            )

            if solo_locales and ambito != "COMUNAL":

                resumen["descartadas"] += 1

                if indice < total:
                    time.sleep(max(0, pausa))

                continue

            # Calcular asociaciones según el ámbito territorial.
            if ambito == "COMUNAL":

                destino = [
                    comuna
                    for comuna in comunas_detectadas
                    if comuna.slug in slugs_objetivo
                ]

            elif ambito == "REGIONAL":

                destino = [
                    comuna
                    for comuna in todas_las_comunas
                    if (
                        _obtener_nombre_region(comuna.region)
                        in regiones_detectadas
                        and comuna.slug in slugs_objetivo
                    )
                ]

            else:
                destino = []

            creada = norma is None

            # --------------------------------------------------
            # CREAR NORMA
            # --------------------------------------------------

            if creada:

                norma = Norma.objects.create(
                    nombre=nombre[:250],
                    tipo_norma=(
                        datos.get("tipo_norma") or "Norma"
                    ),
                    ambito=ambito,
                    fecha_publicacion=datos.get(
                        "fecha_publicacion"
                    ),
                    enlace_fuente=enlace_publico,
                    enlace_bcn=enlace_bcn,
                )

            # --------------------------------------------------
            # ACTUALIZAR NORMA EXISTENTE
            # --------------------------------------------------

            else:

                campos_actualizados = []

                nombre_guardado = nombre[:250]

                if norma.nombre != nombre_guardado:

                    norma.nombre = nombre_guardado
                    campos_actualizados.append("nombre")

                if norma.ambito != ambito:

                    norma.ambito = ambito
                    campos_actualizados.append("ambito")

                if (
                    not norma.fecha_publicacion
                    and datos.get("fecha_publicacion")
                ):

                    norma.fecha_publicacion = (
                        datos["fecha_publicacion"]
                    )

                    campos_actualizados.append(
                        "fecha_publicacion"
                    )

                if datos.get("tipo_norma") and (
                    not norma.tipo_norma
                    or norma.tipo_norma == "Norma"
                ):

                    norma.tipo_norma = datos["tipo_norma"]

                    campos_actualizados.append(
                        "tipo_norma"
                    )

                # Actualizar URI original de BCN.
                if norma.enlace_bcn != enlace_bcn:

                    norma.enlace_bcn = enlace_bcn

                    campos_actualizados.append(
                        "enlace_bcn"
                    )

                # Actualizar enlace público de Ley Chile.
                if norma.enlace_fuente != enlace_publico:

                    norma.enlace_fuente = enlace_publico

                    campos_actualizados.append(
                        "enlace_fuente"
                    )

                if campos_actualizados:

                    norma.save(
                        update_fields=campos_actualizados
                    )

            # Actualizar índices para las siguientes normas.
            por_enlace[enlace_bcn] = norma
            por_enlace_publico[enlace_publico] = norma

            titulos_completos_por_pk[norma.pk] = nombre

            # --------------------------------------------------
            # ASOCIACIÓN DE COMUNAS
            # --------------------------------------------------

            if ejecucion_completa:

                norma.comunas.set(destino)

            else:

                norma.comunas.remove(*comunas_objetivo)

                if destino:
                    norma.comunas.add(*destino)

            if creada:
                resumen["nuevas"] += 1
            else:
                resumen["existentes"] += 1

            if ambito == "COMUNAL":
                resumen["locales"] += 1

            elif ambito == "REGIONAL":
                resumen["regionales"] += 1

            else:
                resumen["generales"] += 1

            if indice < total:
                time.sleep(max(0, pausa))

        # --------------------------------------------------
        # SINCRONIZACIÓN FINAL DE NORMAS AMBIENTALES
        # --------------------------------------------------

        normas_ambientales = Norma.objects.filter(
            enlace_bcn__contains="/ministerio-del-medio-ambiente/"
        )

        for norma in normas_ambientales:

            titulo_para_clasificar = (
                titulos_completos_por_pk.get(
                    norma.pk,
                    norma.nombre,
                )
            )

            ambito, comunas_detectadas, regiones_detectadas = (
                _detectar_ambito(
                    titulo_para_clasificar,
                    todas_las_comunas
                )
            )

            if ambito == "COMUNAL":

                destino = comunas_detectadas

            elif ambito == "REGIONAL":

                destino = [
                    comuna
                    for comuna in todas_las_comunas
                    if (
                        _obtener_nombre_region(comuna.region)
                        in regiones_detectadas
                    )
                ]

            else:
                destino = []

            if ambito != norma.ambito:

                norma.ambito = ambito

                norma.save(
                    update_fields=["ambito"]
                )

            if ejecucion_completa:

                norma.comunas.set(destino)

            else:

                norma.comunas.remove(*comunas_objetivo)

                asociaciones_objetivo = [
                    comuna
                    for comuna in destino
                    if comuna.slug in slugs_objetivo
                ]

                if asociaciones_objetivo:
                    norma.comunas.add(*asociaciones_objetivo)

        self.stdout.write(
            self.style.SUCCESS(
                f"Procesamiento finalizado: {total} normas revisadas."
            )
        )

        return resumen
