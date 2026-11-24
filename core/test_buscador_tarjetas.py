from datetime import date
 
from django.test import TestCase
from django.urls import reverse
 
from comunas.models import Comuna
from noticias.models import Noticia
from normativa.models import Norma
 
 
class TarjetasDeComunaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.petorca = Comuna.objects.create(
            nombre="Petorca", slug="petorca", region="Valparaíso")
 
    def test_la_comuna_se_muestra_como_tarjeta_con_contadores(self):
        r = self.client.get(reverse("core:buscar"), {"q": "petorca"})
        self.assertIn(self.petorca, r.context["coincidencias"])
        self.assertContains(r, 'class="tarjeta-comuna tema-petorca"')
        self.assertContains(r, "0 fuentes de monitoreo")
 
    def test_las_comunas_similares_tambien_son_tarjetas(self):
        r = self.client.get(reverse("core:buscar"), {"q": "petorka"})
        self.assertIn(self.petorca, r.context["similares"])
        self.assertContains(r, 'class="tarjeta-comuna tema-petorca"')
 
    def test_los_contadores_incluyen_noticias_y_normas_nacionales(self):
        noticia = Noticia.objects.create(
            titulo="Sequía", fecha=date(2024, 6, 10), fuente="MMA",
            enlace="https://mma.gob.cl/sequia/")
        noticia.comunas.add(self.petorca)
        Norma.objects.create(
            nombre="Nacional", tipo_norma="Ley", ambito="NACIONAL",
            enlace_fuente="https://www.leychile.cl/nacional")
        r = self.client.get(reverse("core:buscar"), {"q": "petorca"})
        comuna = r.context["coincidencias"][0]
        self.assertEqual((comuna.n_noticias, comuna.n_normas), (1, 1))
 
    def test_la_portada_sigue_mostrando_las_tarjetas(self):
        r = self.client.get(reverse("core:inicio"))
        self.assertContains(r, 'class="tarjeta-comuna tema-petorca"')
 