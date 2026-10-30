from comunas.models import Comuna

def menu_comunas(request):
    """Disponible en todas las plantillas: el menú desplegable de comunas."""
    return {"menu_comunas": Comuna.objects.all()}
