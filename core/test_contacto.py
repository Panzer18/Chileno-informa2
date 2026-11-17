from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
 
from core.models import Mensaje
 
DATOS = {
    "nombre": "Ana",
    "correo": "ana@ejemplo.cl",
    "motivo": "consulta",
    "mensaje": "Hola, tengo una consulta.",
    "sitio_web": "",
}
 
 
@override_settings(CONTACTO_DESTINO="equipo@ejemplo.cl")
class ContactoTests(TestCase):
    def test_pagina_carga(self):
        r = self.client.get(reverse("core:contacto"))
        self.assertContains(r, "Contáctanos")
 
    def test_enlace_en_el_menu(self):
        r = self.client.get(reverse("core:inicio"))
        self.assertContains(r, 'href="/contacto/"')
 
    def test_envio_valido_guarda_y_envia_correo(self):
        r = self.client.post(reverse("core:contacto"), DATOS)
        self.assertRedirects(r, reverse("core:contacto"))
        self.assertEqual(Mensaje.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["equipo@ejemplo.cl"])
        self.assertEqual(mail.outbox[0].reply_to, ["ana@ejemplo.cl"])
 
    def test_muestra_mensaje_de_exito(self):
        r = self.client.post(reverse("core:contacto"), DATOS, follow=True)
        self.assertContains(r, "Recibimos tu mensaje")
 
    def test_correo_invalido_no_guarda(self):
        r = self.client.post(reverse("core:contacto"), {**DATOS, "correo": "no-es-un-correo"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Mensaje.objects.count(), 0)
 
    def test_motivo_vacio_no_guarda(self):
        r = self.client.post(reverse("core:contacto"), {**DATOS, "motivo": ""})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Mensaje.objects.count(), 0)
 
    def test_campo_trampa_descarta_el_mensaje(self):
        self.client.post(reverse("core:contacto"), {**DATOS, "sitio_web": "spam"})
        self.assertEqual(Mensaje.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
 
    def test_sin_destino_guarda_pero_no_envia(self):
        with self.settings(CONTACTO_DESTINO=""):
            self.client.post(reverse("core:contacto"), DATOS)
        self.assertEqual(Mensaje.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)