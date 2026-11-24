import time
import urllib.request
import xml.etree.ElementTree as ET
from urllib.error import HTTPError
 
from django.core.management.base import BaseCommand
 
from comunas.models import Comuna
from noticias.models import Noticia
from noticias.rss import guardar, imagen_de_pagina, leer_items, urls_para
 
 
class Command(BaseCommand):
    help = "Trae noticias del MMA para TODAS las comunas de la base de datos y las guarda en el sitio."
 
    def add_arguments(self, parser):
        parser.add_argument("--comuna", help="Solo esta comuna (su slug), por ejemplo: petorca")
        parser.add_argument("--pausa", type=float, default=1.0,
                            help="Segundos de espera entre consultas (por defecto, 1)")
        parser.add_argument("--max-imagenes", type=int, default=20,
                            help="Máximo de páginas que se abren por vez para buscar imágenes (por defecto, 20)")
        parser.add_argument("--sin-imagenes", action="store_true",
                            help="No buscar imágenes en las páginas de las noticias")
 
    def handle(self, *args, **opciones):
        comunas = Comuna.objects.all()
        if opciones["comuna"]:
            comunas = comunas.filter(slug=opciones["comuna"])
        if not comunas.exists():
            self.stderr.write(self.style.WARNING("No hay comunas que actualizar."))
            return
 
        for comuna in comunas:
            self.stdout.write(self.style.MIGRATE_HEADING(comuna.nombre))
            for url in urls_para(comuna):
                contenido = self._bajar(url)
                if contenido is not None:
                    try:
                        items = leer_items(contenido)
                    except ET.ParseError as error:
                        self.stderr.write(self.style.WARNING(f"  {url} -> no es un canal RSS válido: {error}"))
                    else:
                        self.stdout.write(f"  {url} -> {guardar(items, [comuna.slug])}")
                time.sleep(opciones["pausa"])  # no sobrecargar el sitio del MMA
 
        if not opciones["sin_imagenes"]:
            self._completar_imagenes(opciones["max_imagenes"], opciones["pausa"])
        self.stdout.write(self.style.SUCCESS("Listo."))
 
    def _completar_imagenes(self, maximo, pausa):
        """Abre la página de las noticias sin imagen y busca su imagen de portada."""
        pendientes = list(Noticia.objects.filter(imagen="").order_by("-fecha")[:maximo])
        if not pendientes:
            return
        self.stdout.write(self.style.MIGRATE_HEADING("Imágenes"))
        for noticia in pendientes:
            pagina = self._bajar(noticia.enlace, limite=300_000)
            imagen = imagen_de_pagina(pagina, noticia.enlace) if pagina else ""
            if imagen:
                noticia.imagen = imagen
                noticia.save(update_fields=["imagen"])
            self.stdout.write(f"  {'con imagen' if imagen else 'sin imagen'}: {noticia.titulo[:60]}")
            time.sleep(pausa)
 
    def _bajar(self, url, limite=None):
        """Devuelve el contenido de una dirección, o None si no se pudo leer."""
        try:
            peticion = urllib.request.Request(
                url, headers={"User-Agent": "ChilenosInforma2/1.0 (proyecto academico IWG400)"})
            with urllib.request.urlopen(peticion, timeout=15) as respuesta:
                return respuesta.read(limite) if limite else respuesta.read()
        except HTTPError as error:
            if error.code == 404:
                self.stdout.write(f"  {url} -> no existe (404)")
            else:
                self.stderr.write(self.style.WARNING(f"  {url} -> error {error.code}"))
        except OSError as error:
            self.stderr.write(self.style.WARNING(f"  {url} -> no se pudo leer: {error}"))
        return None