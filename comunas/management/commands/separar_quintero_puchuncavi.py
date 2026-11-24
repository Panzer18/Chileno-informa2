from django.core.management.base import BaseCommand
from django.db import transaction
 
from comunas.models import Comuna, Monitoreo
 
SLUG_ANTIGUO = "quintero-puchuncavi"
NUEVAS = (("quintero", "Quintero"), ("puchuncavi", "Puchuncaví"))
 
 
def destino_norma(norma, quintero, puchuncavi):
    """Comunas a las que pasa una norma de la comuna antigua.
 
    Las ordenanzas de una municipalidad van solo a su comuna; el resto
    (normas regionales, nacionales o de la zona) queda en las dos.
    """
    enlace = (getattr(norma, "enlace_bcn", "") or norma.enlace_fuente or "").lower()
    if "municipalidad-de-quintero" in enlace:
        return [quintero]
    if "municipalidad-de-puchuncavi" in enlace:
        return [puchuncavi]
    return [quintero, puchuncavi]
 
 
class Command(BaseCommand):
    help = "Separa la comuna Quintero-Puchuncaví en dos comunas: Quintero y Puchuncaví."
 
    def handle(self, *args, **opciones):
        antigua = Comuna.objects.filter(slug=SLUG_ANTIGUO).first()
        if antigua is None:
            self.stdout.write("No existe la comuna Quintero-Puchuncaví: no hay nada que separar.")
            return
 
        with transaction.atomic():
            quintero, puchuncavi = [
                Comuna.objects.get_or_create(
                    slug=slug, defaults={"nombre": nombre, "region": antigua.region})[0]
                for slug, nombre in NUEVAS
            ]
 
            copiados = 0
            for m in antigua.monitoreos.all():
                for comuna in (quintero, puchuncavi):
                    _, creado = Monitoreo.objects.get_or_create(
                        comuna=comuna, tipo=m.tipo, parametro=m.parametro,
                        defaults={
                            "fuente": m.fuente, "valor": m.valor,
                            "fecha_medicion": m.fecha_medicion,
                            "enlace_fuente": m.enlace_fuente,
                            "ultima_revision": m.ultima_revision,
                        })
                    copiados += creado
 
            normas = list(antigua.normas.all())
            for norma in normas:
                norma.comunas.add(*destino_norma(norma, quintero, puchuncavi))
 
            noticias = list(antigua.noticias.all())
            for noticia in noticias:
                noticia.comunas.add(quintero, puchuncavi)
 
            antigua.delete()
 
        self.stdout.write(self.style.SUCCESS("Comuna separada en Quintero y Puchuncaví."))
        self.stdout.write(
            f"Monitoreos copiados: {copiados} | Normas traspasadas: {len(normas)} "
            f"| Noticias traspasadas: {len(noticias)}")
        self.stdout.write(
            "Para afinar las asociaciones, ejecuta de nuevo: actualizar_ordenanzas_bcn, "
            "actualizar_normativa_bcn y actualizar_noticias.")