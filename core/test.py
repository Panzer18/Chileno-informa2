from datetime import date
 
from django.test import TestCase
from django.urls import reverse
 
from comunas.models import Comuna, Monitoreo
from core.models import Fuente
from noticias.models import Noticia
 
 
class SitioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.petorca = Comuna.objects.create(
            nombre="Petorca", slug="petorca", region="Valparaíso")
        cls.quintero = Comuna.objects.create(
            nombre="Quintero-Puchuncaví", slug="quintero-puchuncavi", region="Valparaíso")
        Monitoreo.objects.create(
            comuna=cls.quintero, tipo="hidrico", parametro="Estaciones hídricas",
            fuente="DGA", enlace_fuente="https://dga.mop.gob.cl/",
            ultima_revision=date(2025, 3, 5))
        Monitoreo.objects.create(
            comuna=cls.quintero, tipo="ambiental", parametro="Calidad del aire",
            fuente="SMA", enlace_fuente="https://portal.sma.gob.cl/")
 
    def _noticia(self, titulo, fecha):
        n = Noticia.objects.create(
            titulo=titulo, fecha=fecha, fuente="MMA", enlace="https://mma.gob.cl/")
        n.comunas.add(self.petorca)
        return n
 
    # --- Navegación general ---
    def test_todas_las_paginas_responden(self):
        urls = [reverse("core:inicio"), reverse("core:que_es"),
                reverse("core:fuentes"), reverse("core:buscar")]
        for c in (self.petorca, self.quintero):
            for nombre in ("comunas:detalle", "comunas:monitoreo",
                           "normativa:lista", "noticias:lista"):
                urls.append(reverse(nombre, args=[c.slug]))
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
 
    def test_404_usa_plantilla_propia(self):
        r = self.client.get("/comunas/no-existe/")
        self.assertEqual(r.status_code, 404)
        self.assertTemplateUsed(r, "404.html")
 
    # --- Monitoreo ---
    def test_monitoreo_con_datos_muestra_enlace_y_revision(self):
        r = self.client.get(reverse("comunas:monitoreo", args=["quintero-puchuncavi"]))
        self.assertContains(r, "https://dga.mop.gob.cl/")
        self.assertContains(r, "Enlace revisado el 05/03/2025")
        self.assertContains(r, "Revisión pendiente")
 
    def test_monitoreo_sin_datos_muestra_aviso(self):
        r = self.client.get(reverse("comunas:monitoreo", args=["petorca"]))
        self.assertContains(r, "No hay información de monitoreo hídrico disponible")
        self.assertContains(r, "No hay información de monitoreo ambiental disponible")
 
    # --- Leyes y noticias vacías ---
    def test_leyes_sin_datos_muestra_aviso(self):
        r = self.client.get(reverse("normativa:lista", args=["petorca"]))
        self.assertContains(r, "No hay leyes ni normativas cargadas")
 
    def test_noticias_sin_datos_muestra_aviso(self):
        r = self.client.get(reverse("noticias:lista", args=["petorca"]))
        self.assertContains(r, "No hay noticias cargadas para esta comuna")
 
    # --- Filtro de noticias por fechas ---
    def test_noticias_filtro_por_fechas(self):
        self._noticia("Noticia antigua", date(2024, 1, 10))
        self._noticia("Noticia reciente", date(2024, 6, 10))
        url = reverse("noticias:lista", args=["petorca"])
 
        r = self.client.get(url, {"desde": "2024-05-01"})
        self.assertContains(r, "Noticia reciente")
        self.assertNotContains(r, "Noticia antigua")
 
        r = self.client.get(url, {"hasta": "2024-05-01"})
        self.assertContains(r, "Noticia antigua")
        self.assertNotContains(r, "Noticia reciente")
 
    def test_fecha_invalida_no_rompe_la_pagina(self):
        url = reverse("noticias:lista", args=["petorca"])
        for valor in ("basura", "2024-02-31"):
            with self.subTest(valor=valor):
                self.assertEqual(self.client.get(url, {"desde": valor}).status_code, 200)
 
    # --- Buscador ---
    def test_buscador_encuentra_comuna(self):
        r = self.client.get(reverse("core:buscar"), {"q": "petorca"})
        self.assertIn(self.petorca, r.context["coincidencias"])
 
    def test_buscador_tolera_error_de_tipeo(self):
        r = self.client.get(reverse("core:buscar"), {"q": "petorka"})
        self.assertIn(self.petorca, r.context["similares"])
 
    def test_buscador_ignora_tildes(self):
        r = self.client.get(reverse("core:buscar"), {"q": "puchuncavi"})
        self.assertIn(self.quintero, r.context["coincidencias"])
 
    # --- Fuentes ---
    def test_pagina_fuentes_muestra_enlaces(self):
        Fuente.objects.create(nombre="DGA", descripcion="Aguas",
                              enlace="https://dga.mop.gob.cl/", tipo="monitoreo")
        r = self.client.get(reverse("core:fuentes"))
        self.assertContains(r, "https://dga.mop.gob.cl/")