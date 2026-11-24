from datetime import date
from io import StringIO
 
from django.core.management import call_command
from django.test import TestCase
 
from comunas.models import Comuna, Monitoreo
from noticias.models import Noticia
from noticias.rss import urls_para
from normativa.models import Norma
 
TODAS = {"quintero", "puchuncavi"}
 
 
def separar():
    call_command("separar_quintero_puchuncavi", stdout=StringIO())
 
 
def slugs(objeto):
    return {c.slug for c in objeto.comunas.all()}
 
 
class SeparacionTests(TestCase):
    def setUp(self):
        self.antigua = Comuna.objects.create(
            nombre="Quintero-Puchuncaví", slug="quintero-puchuncavi", region="Valparaíso")
        Monitoreo.objects.create(
            comuna=self.antigua, tipo="ambiental", parametro="Red de calidad del aire",
            fuente="SMA", enlace_fuente="https://portal.sma.gob.cl/")
        self.noticia = Noticia.objects.create(
            titulo="Zona", fecha=date(2024, 6, 10), fuente="MMA",
            enlace="https://mma.gob.cl/zona/")
        self.noticia.comunas.add(self.antigua)
        self.general = Norma.objects.create(
            nombre="General", tipo_norma="Ley", ambito="COMUNAL",
            enlace_fuente="https://www.leychile.cl/general")
        self.general.comunas.add(self.antigua)
        self.de_quintero = Norma.objects.create(
            nombre="Ordenanza de Quintero", tipo_norma="Ordenanza", ambito="COMUNAL",
            enlace_fuente="https://www.leychile.cl/quintero",
            enlace_bcn="http://datos.bcn.cl/recurso/cl/orz/municipalidad-de-quintero/2007-12-29/1")
        self.de_quintero.comunas.add(self.antigua)
 
    def test_crea_las_dos_comunas_y_elimina_la_antigua(self):
        separar()
        self.assertFalse(Comuna.objects.filter(slug="quintero-puchuncavi").exists())
        quintero = Comuna.objects.get(slug="quintero")
        puchuncavi = Comuna.objects.get(slug="puchuncavi")
        self.assertEqual((quintero.nombre, puchuncavi.nombre), ("Quintero", "Puchuncaví"))
        self.assertEqual(quintero.region, "Valparaíso")
 
    def test_copia_el_monitoreo_a_las_dos(self):
        separar()
        for slug in TODAS:
            self.assertEqual(Monitoreo.objects.filter(comuna__slug=slug, fuente="SMA").count(), 1)
 
    def test_noticias_y_normas_generales_quedan_en_las_dos(self):
        separar()
        self.assertEqual(slugs(self.noticia), TODAS)
        self.assertEqual(slugs(self.general), TODAS)
 
    def test_la_ordenanza_municipal_queda_solo_en_su_comuna(self):
        separar()
        self.assertEqual(slugs(self.de_quintero), {"quintero"})
 
    def test_se_puede_ejecutar_dos_veces(self):
        separar()
        separar()
        self.assertEqual(Comuna.objects.filter(slug__in=TODAS).count(), 2)
        self.assertEqual(Monitoreo.objects.filter(fuente="SMA").count(), 2)
 
    def test_cada_comuna_nueva_busca_en_el_canal_de_la_zona(self):
        for nombre, slug, busqueda in (
            ("Quintero", "quintero", "https://mma.gob.cl/?s=Quintero&feed=rss2"),
            ("Puchuncaví", "puchuncavi", "https://mma.gob.cl/?s=Puchuncav%C3%AD&feed=rss2"),
        ):
            urls = urls_para(Comuna(nombre=nombre, slug=slug, region="Valparaíso"))
            self.assertIn("https://mma.gob.cl/tag/quintero-y-puchuncavi/feed/", urls)
            self.assertIn(busqueda, urls)