from datetime import date
 
from django.test import TestCase
from django.urls import reverse
 
from comunas.models import Comuna
from noticias.models import Noticia
from normativa.models import Norma
 
 
class ExtrasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.comuna = Comuna.objects.create(
            nombre="Petorca", slug="petorca", region="Valparaíso")
        for i in range(7):
            n = Noticia.objects.create(
                titulo=f"Noticia {i}", fecha=date(2024, 1, i + 1),
                fuente="MMA", enlace="https://mma.gob.cl/")
            n.comunas.add(cls.comuna)
        for i in range(11):
            x = Norma.objects.create(
                nombre=f"Norma {i}", tipo_norma="Ley",
                enlace_fuente="https://www.leychile.cl/")
            x.comunas.add(cls.comuna)
 
    # --- Paginación ---
    def test_noticias_se_dividen_en_paginas(self):
        url = reverse("noticias:lista", args=["petorca"])
        r1 = self.client.get(url)
        self.assertEqual(len(r1.context["pagina"]), 6)
        self.assertEqual(r1.context["pagina"].paginator.num_pages, 2)
        r2 = self.client.get(url, {"page": 2})
        self.assertEqual(len(r2.context["pagina"]), 1)
 
    def test_leyes_se_dividen_en_paginas(self):
        url = reverse("normativa:lista", args=["petorca"])
        self.assertEqual(len(self.client.get(url).context["pagina"]), 10)
        self.assertEqual(len(self.client.get(url, {"page": 2}).context["pagina"]), 1)
 
    def test_pagina_invalida_no_rompe(self):
        url = reverse("noticias:lista", args=["petorca"])
        for valor in ("999", "abc", "-1"):
            with self.subTest(valor=valor):
                self.assertEqual(self.client.get(url, {"page": valor}).status_code, 200)
 
    def test_paginacion_conserva_los_filtros(self):
        url = reverse("noticias:lista", args=["petorca"])
        r = self.client.get(url, {"desde": "2024-01-01"})
        self.assertContains(r, "desde=2024-01-01&amp;page=2")
 
    # --- Accesibilidad ---
    def test_enlace_saltar_al_contenido(self):
        r = self.client.get(reverse("core:inicio"))
        self.assertContains(r, 'href="#contenido"')
        self.assertContains(r, 'id="contenido"')
