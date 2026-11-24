from datetime import date
 
from django.test import TestCase
 
from comunas.models import Comuna
from noticias.models import Noticia
from noticias.rss import guardar, leer_items, terminos_busqueda, urls_para
 
RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>MMA</title>
<item><title>Humedal en Quintero</title>
<link>https://mma.gob.cl/humedal-quintero/</link>
<pubDate>Mon, 10 Jun 2024 10:00:00 +0000</pubDate>
<description>Texto sobre Quintero</description></item>
<item><title>Noticia nacional</title>
<link>https://mma.gob.cl/nacional/</link>
<pubDate>Tue, 11 Jun 2024 10:00:00 +0000</pubDate>
<description>Nada local</description></item>
<item><title>Sin fecha</title>
<link>https://mma.gob.cl/sin-fecha/</link>
<description>x</description></item>
</channel></rss>"""
 
 
class RssTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.comuna = Comuna.objects.create(
            nombre="Quintero-Puchuncaví", slug="quintero-puchuncavi", region="Valparaíso")
 
    def test_lee_los_items_del_canal(self):
        items = leer_items(RSS)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["titulo"], "Humedal en Quintero")
        self.assertEqual(items[0]["fecha"], date(2024, 6, 10))
        self.assertIsNone(items[2]["fecha"])
 
    def test_guarda_y_asigna_la_comuna(self):
        resumen = guardar(leer_items(RSS), ["quintero-puchuncavi"])
        self.assertEqual(resumen["nuevas"], 2)
        self.assertEqual(resumen["omitidas"], 1)  # la que no tiene fecha
        self.assertEqual(Noticia.objects.count(), 2)
        self.assertEqual(self.comuna.noticias.count(), 2)
 
    def test_filtra_por_palabras_sin_importar_tildes_ni_mayusculas(self):
        resumen = guardar(leer_items(RSS), ["quintero-puchuncavi"], palabras=["QUINTÉRO"])
        self.assertEqual(Noticia.objects.count(), 1)
        self.assertEqual(resumen["descartadas"], 1)
 
    def test_no_duplica_noticias(self):
        guardar(leer_items(RSS), ["quintero-puchuncavi"])
        resumen = guardar(leer_items(RSS), ["quintero-puchuncavi"])
        self.assertEqual(Noticia.objects.count(), 2)
        self.assertEqual(resumen["nuevas"], 0)
        self.assertEqual(resumen["existentes"], 2)
 
    def test_omite_enlaces_demasiado_largos(self):
        items = [{"titulo": "Larga", "enlace": "https://mma.gob.cl/" + "a" * 250,
                  "texto": "", "fecha": date(2024, 6, 10)}]
        resumen = guardar(items, ["quintero-puchuncavi"])
        self.assertEqual(resumen["omitidas"], 1)
        self.assertEqual(Noticia.objects.count(), 0)
 
    def test_una_noticia_puede_quedar_en_dos_comunas(self):
        otra = Comuna.objects.create(nombre="Petorca", slug="petorca", region="Valparaíso")
        guardar(leer_items(RSS), ["quintero-puchuncavi"])
        guardar(leer_items(RSS), ["petorca"])
        self.assertEqual(Noticia.objects.count(), 2)  # no se duplicó
        self.assertEqual(otra.noticias.count(), 2)
        self.assertEqual(self.comuna.noticias.count(), 2)
 
    # --- Canales para cualquier comuna ---
    def test_terminos_de_busqueda(self):
        self.assertEqual(terminos_busqueda("Petorca"), ["Petorca"])
        self.assertEqual(terminos_busqueda("Quintero-Puchuncaví"), ["Quintero", "Puchuncaví"])
        self.assertEqual(terminos_busqueda("Los Andes"), ['"Los Andes"'])
 
    def test_urls_para_una_comuna_nueva(self):
        comuna = Comuna(nombre="Los Andes", slug="los-andes", region="Valparaíso")
        urls = urls_para(comuna)
        self.assertEqual(urls[0], "https://mma.gob.cl/tag/los-andes/feed/")
        self.assertIn("https://mma.gob.cl/?s=%22Los+Andes%22&feed=rss2", urls)
 
    def test_comuna_con_canal_especial_y_sin_repetidos(self):
        urls = urls_para(self.comuna)
        self.assertIn("https://mma.gob.cl/tag/quintero-y-puchuncavi/feed/", urls)
        self.assertEqual(len(urls), len(set(urls)))