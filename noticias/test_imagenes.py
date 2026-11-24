from datetime import date
 
from django.test import TestCase
from django.urls import reverse
 
from comunas.models import Comuna
from noticias.models import Noticia
from noticias.rss import guardar, imagen_de_pagina, leer_items
 
RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><title>MMA</title>
<item><title>Con media</title><link>https://mma.gob.cl/a/</link>
<pubDate>Mon, 10 Jun 2024 10:00:00 +0000</pubDate>
<media:content url="https://mma.gob.cl/img/a.jpg" medium="image"/></item>
<item><title>Con enclosure</title><link>https://mma.gob.cl/b/</link>
<pubDate>Mon, 10 Jun 2024 10:00:00 +0000</pubDate>
<enclosure url="https://mma.gob.cl/img/b.jpg" type="image/jpeg" length="0"/></item>
<item><title>Con img en el contenido</title><link>https://mma.gob.cl/c/</link>
<pubDate>Mon, 10 Jun 2024 10:00:00 +0000</pubDate>
<content:encoded><![CDATA[<p>Hola</p><img src="https://mma.gob.cl/img/c.jpg" alt="">]]></content:encoded></item>
<item><title>Sin imagen</title><link>https://mma.gob.cl/d/</link>
<pubDate>Mon, 10 Jun 2024 10:00:00 +0000</pubDate></item>
<item><title>Imagen peligrosa</title><link>https://mma.gob.cl/e/</link>
<pubDate>Mon, 10 Jun 2024 10:00:00 +0000</pubDate>
<media:content url="javascript:alert(1)" medium="image"/></item>
</channel></rss>"""
 
 
class ImagenesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.comuna = Comuna.objects.create(
            nombre="Petorca", slug="petorca", region="Valparaíso")
 
    def test_extrae_la_imagen_del_canal(self):
        imagenes = [i["imagen"] for i in leer_items(RSS)]
        self.assertEqual(imagenes, [
            "https://mma.gob.cl/img/a.jpg",
            "https://mma.gob.cl/img/b.jpg",
            "https://mma.gob.cl/img/c.jpg",
            "",
            "",  # la dirección "javascript:" se descarta
        ])
 
    def test_imagen_de_portada_de_una_pagina(self):
        html = b'<html><head><meta property="og:image" content="https://mma.gob.cl/img/x.jpg"></head></html>'
        self.assertEqual(imagen_de_pagina(html), "https://mma.gob.cl/img/x.jpg")
        relativa = b'<meta property="og:image" content="/img/y.jpg">'
        self.assertEqual(
            imagen_de_pagina(relativa, "https://mma.gob.cl/nota/"), "https://mma.gob.cl/img/y.jpg")
        self.assertEqual(imagen_de_pagina(b"<html></html>"), "")
 
    def test_guardar_conserva_la_imagen(self):
        guardar(leer_items(RSS), ["petorca"])
        self.assertEqual(Noticia.objects.count(), 5)
        self.assertEqual(
            Noticia.objects.get(enlace="https://mma.gob.cl/a/").imagen, "https://mma.gob.cl/img/a.jpg")
 
    def test_completa_la_imagen_de_una_noticia_ya_guardada(self):
        Noticia.objects.create(
            titulo="Con media", fecha=date(2024, 6, 10), fuente="MMA",
            enlace="https://mma.gob.cl/a/")
        guardar(leer_items(RSS), ["petorca"])
        self.assertEqual(
            Noticia.objects.get(enlace="https://mma.gob.cl/a/").imagen, "https://mma.gob.cl/img/a.jpg")
 
    def test_la_miniatura_se_muestra_solo_si_hay_imagen(self):
        con = Noticia.objects.create(
            titulo="Con imagen", fecha=date(2024, 6, 10), fuente="MMA",
            enlace="https://mma.gob.cl/1/", imagen="https://mma.gob.cl/img/1.jpg")
        con.comunas.add(self.comuna)
        url = reverse("noticias:lista", args=["petorca"])
        r = self.client.get(url)
        self.assertContains(r, 'class="miniatura"')
        self.assertContains(r, "https://mma.gob.cl/img/1.jpg")
 
        con.imagen = ""
        con.save()
        self.assertNotContains(self.client.get(url), 'class="miniatura"')
 
    def test_la_portada_muestra_la_miniatura(self):
        n = Noticia.objects.create(
            titulo="Con imagen", fecha=date(2024, 6, 10), fuente="MMA",
            enlace="https://mma.gob.cl/1/", imagen="https://mma.gob.cl/img/1.jpg")
        n.comunas.add(self.comuna)
        self.assertContains(self.client.get(reverse("core:inicio")), 'class="miniatura"')