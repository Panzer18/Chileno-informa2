from datetime import date
 
from django.test import TestCase
from django.urls import reverse
 
from comunas.models import Comuna
from noticias.models import Noticia
 
 
def crear_noticia(titulo, comuna):
    n = Noticia.objects.create(
        titulo=titulo, fecha=date(2024, 6, 10), fuente="MMA",
        enlace="https://mma.gob.cl/")
    n.comunas.add(comuna)
    return n
 
 
class BuscadorFiltrosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.petorca = Comuna.objects.create(
            nombre="Petorca", slug="petorca", region="Valparaíso")
        cls.quintero = Comuna.objects.create(
            nombre="Quintero-Puchuncaví", slug="quintero-puchuncavi", region="Valparaíso")
        cls.n_pet = crear_noticia("Sequía en la provincia", cls.petorca)
        cls.n_qp = crear_noticia("Calidad del aire en la bahía", cls.quintero)
 
    def test_filtro_por_comuna_sin_texto(self):
        r = self.client.get(reverse("core:buscar"), {"comuna": "petorca"})
        self.assertEqual(list(r.context["noticias"]), [self.n_pet])
 
    def test_buscar_en_noticias(self):
        r = self.client.get(reverse("core:buscar"), {"q": "sequía", "en": "noticias"})
        self.assertEqual(list(r.context["noticias"]), [self.n_pet])
 
    def test_buscar_solo_en_leyes_excluye_noticias(self):
        r = self.client.get(reverse("core:buscar"), {"q": "sequía", "en": "leyes"})
        self.assertEqual(list(r.context["noticias"]), [])
 
    def test_buscar_solo_en_comunas_excluye_noticias(self):
        r = self.client.get(reverse("core:buscar"), {"q": "petorca", "en": "comunas"})
        self.assertIn(self.petorca, r.context["coincidencias"])
        self.assertEqual(list(r.context["noticias"]), [])
 
    def test_valores_invalidos_no_rompen(self):
        r = self.client.get(
            reverse("core:buscar"), {"q": "x", "en": "otro", "comuna": "no-existe"})
        self.assertEqual(r.status_code, 200)
 
    def test_detalle_muestra_resumen_de_contenidos(self):
        r = self.client.get(reverse("comunas:detalle", args=["petorca"]))
        self.assertContains(r, "1 noticia</span>")
        self.assertContains(r, "Sin fuentes cargadas aún")
        self.assertContains(r, "Sin normas cargadas aún")
 
    def test_mensaje_sin_noticias_orienta_al_usuario(self):
        Comuna.objects.create(nombre="Otra", slug="otra", region="X")
        r = self.client.get(reverse("noticias:lista", args=["otra"]))
        self.assertContains(r, "No hay noticias cargadas para esta comuna")
        self.assertContains(r, "https://mma.gob.cl/")