from django.core.management.base import BaseCommand
from comunas.models import Comuna, Monitoreo
from core.models import Fuente
 
 
class Command(BaseCommand):
    help = "Carga las comunas, los enlaces de monitoreo y las fuentes del entregable P2."
 
    def handle(self, *args, **opts):
        qp, _ = Comuna.objects.get_or_create(
            slug="quintero-puchuncavi",
            defaults={"nombre": "Quintero-Puchuncaví", "region": "Valparaíso"})
        pe, _ = Comuna.objects.get_or_create(
            slug="petorca", defaults={"nombre": "Petorca", "region": "Valparaíso"})
 
        dga = "https://dga.mop.gob.cl/estadisticas-estaciones-dga/"
        sma = "https://portal.sma.gob.cl/index.php/gestion-concon-quintero-y-puchuncavi/red-cqp/"
        pras = "https://pras.mma.gob.cl/quintero-puchuncavi/medida-quintero-puchuncavi-i-1-2/"
        monitoreos = [
            (qp, "hidrico", "Estaciones y estadísticas hídricas", "DGA", dga),
            (qp, "ambiental", "Red de monitoreo de calidad del aire", "SMA", sma),
            (qp, "ambiental", "Observatorio Ambiental (PRAS, medida 1.1.2)", "PRAS", pras),
            (pe, "hidrico", "Estaciones y estadísticas hídricas", "DGA", dga),
        ]
        for comuna, tipo, nombre, fuente, enlace in monitoreos:
            Monitoreo.objects.get_or_create(
                comuna=comuna, tipo=tipo, parametro=nombre,
                defaults={"fuente": fuente, "enlace_fuente": enlace})
 
        fuentes = [
            ("DGA", "Dirección General de Aguas (MOP): estaciones y estadísticas hídricas.",
             dga, "monitoreo"),
            ("SMA", "Superintendencia del Medio Ambiente: red de monitoreo de calidad del aire en Concón, Quintero y Puchuncaví.",
             sma, "monitoreo"),
            ("PRAS", "Programa para la Recuperación Ambiental y Social: Observatorio Ambiental de Quintero-Puchuncaví.",
             pras, "monitoreo"),
            ("SIMBIO", "Información ambiental por comuna del Ministerio del Medio Ambiente.",
             "https://simbio.mma.gob.cl/DPA/DetailsComuna/54", "monitoreo"),
            ("Ley Chile", "Biblioteca del Congreso Nacional: texto oficial de leyes y normas de Chile.",
             "https://www.leychile.cl/", "normativa"),
            ("MMA", "Ministerio del Medio Ambiente: noticias sobre Quintero y Puchuncaví.",
             "https://mma.gob.cl/tag/quintero-y-puchuncavi/", "noticias"),
        ]
        for nombre, descripcion, enlace, tipo in fuentes:
            Fuente.objects.get_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion, "enlace": enlace, "tipo": tipo})
 
        self.stdout.write(self.style.SUCCESS("Datos iniciales cargados."))

#documento que se debe de revisar