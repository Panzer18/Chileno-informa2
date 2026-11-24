from django.db.models import Q
 
from .models import Norma
 
 
def normas_de(comuna):
    """Normas que se muestran en una comuna.
 
    Incluye las asociadas a ella y las nacionales que no están asociadas a
    ninguna comuna (aplican a todas). Una norma nacional asociada
    expresamente a otras comunas no aparece aquí.
    """
    return Norma.objects.filter(
        Q(comunas=comuna) | Q(ambito="NACIONAL", comunas__isnull=True)
    ).distinct()