from django.test import TestCase
from django.urls import reverse
 
from comunas.models import Comuna
from normativa.consultas import normas_de
from normativa.models import Norma
 
 
def crear_norma(nombre, ambito, comunas=()):
    norma = Norma.objects.create(
        nombre=nombre, tipo_norma="Ley", ambito=ambito,
        enlace_fuente=f"https://www.leychile.cl/{nombre}")
    norma.comunas.add(*comunas)
    return norma
 
 
class AlcanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.petorca = Comuna.objects.create(
            nombre="Petorca", slug="petorca", region="Valparaíso")
        cls.quintero = Comuna.objects.create(
            nombre="Quintero-Puchuncaví", slug="quintero-puchuncavi", region="Valparaíso")
        cls.nacional = crear_norma("NORMA_NACIONAL", "NACIONAL")  # sin comunas: aplica a todas
        cls.regional = crear_norma("NORMA_REGIONAL", "REGIONAL", [cls.petorca, cls.quintero])
        cls.local = crear_norma("NORMA_LOCAL_PETORCA", "COMUNAL", [cls.petorca])
        cls.manual = crear_norma("NORMA_MANUAL_PETORCA", "NACIONAL", [cls.petorca])
 
    def test_cada_comuna_ve_sus_normas_y_las_nacionales(self):
        self.assertEqual(
            set(normas_de(self.petorca)),
            {self.nacional, self.regional, self.local, self.manual})
        self.assertEqual(set(normas_de(self.quintero)), {self.nacional, self.regional})
 
    def test_no_repite_normas_asociadas_a_varias_comunas(self):
        self.assertEqual(normas_de(self.petorca).count(), 4)
 
    def test_la_pagina_muestra_las_nacionales_y_no_las_de_otra_comuna(self):
        r = self.client.get(reverse("normativa:lista", args=["quintero-puchuncavi"]))
        self.assertContains(r, "NORMA_NACIONAL")
        self.assertContains(r, "NORMA_REGIONAL")
        self.assertNotContains(r, "NORMA_LOCAL_PETORCA")
        self.assertNotContains(r, "NORMA_MANUAL_PETORCA")
 
    def test_filtro_por_alcance(self):
        r = self.client.get(reverse("normativa:lista", args=["petorca"]), {"ambito": "COMUNAL"})
        self.assertContains(r, "NORMA_LOCAL_PETORCA")
        self.assertNotContains(r, "NORMA_NACIONAL")
 
    def test_alcance_invalido_no_rompe(self):
        r = self.client.get(reverse("normativa:lista", args=["petorca"]), {"ambito": "otro"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "NORMA_NACIONAL")
 
    def test_los_contadores_cuentan_las_mismas_normas(self):
        detalle = self.client.get(reverse("comunas:detalle", args=["quintero-puchuncavi"]))
        self.assertContains(detalle, "2 normas</span>")
        portada = self.client.get(reverse("core:inicio"))
        cuenta = {c.slug: c.n_normas for c in portada.context["comunas"]}
        self.assertEqual(cuenta, {"petorca": 4, "quintero-puchuncavi": 2})