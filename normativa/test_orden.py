from datetime import date
 
from django.test import TestCase
from django.urls import reverse
 
from comunas.models import Comuna
from normativa.models import Norma
 
 
class OrdenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        comuna = Comuna.objects.create(
            nombre="Petorca", slug="petorca", region="Valparaíso")
        for nombre, fecha in [("N_2010", date(2010, 1, 1)), ("N_2020", date(2020, 1, 1)),
                              ("N_2015", date(2015, 1, 1)), ("N_SIN_FECHA", None)]:
            norma = Norma.objects.create(
                nombre=nombre, tipo_norma="Ley", ambito="COMUNAL", fecha_publicacion=fecha,
                enlace_fuente=f"https://www.leychile.cl/{nombre}")
            norma.comunas.add(comuna)
 
    def _respuesta(self, **parametros):
        return self.client.get(reverse("normativa:lista", args=["petorca"]), parametros)
 
    def _nombres(self, **parametros):
        return [n.nombre for n in self._respuesta(**parametros).context["pagina"]]
 
    def test_por_defecto_primero_la_mas_reciente(self):
        self.assertEqual(self._nombres(), ["N_2020", "N_2015", "N_2010", "N_SIN_FECHA"])
 
    def test_mas_antiguo_primero(self):
        self.assertEqual(
            self._nombres(orden="antiguo"), ["N_2010", "N_2015", "N_2020", "N_SIN_FECHA"])
 
    def test_orden_invalido_usa_el_orden_por_defecto(self):
        self.assertEqual(self._nombres(orden="x"), ["N_2020", "N_2015", "N_2010", "N_SIN_FECHA"])
 
    def test_el_selector_muestra_la_opcion_elegida(self):
        self.assertContains(self._respuesta(orden="antiguo"), 'value="antiguo" selected')
 
    def test_el_orden_se_conserva_al_cambiar_de_pagina(self):
        self.assertEqual(self._respuesta(orden="antiguo").context["consulta"], "orden=antiguo")
 
    def test_las_normas_sin_fecha_lo_indican(self):
        self.assertContains(self._respuesta(), "sin fecha registrada")