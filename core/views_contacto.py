from django.conf import settings
from django.contrib import messages
from django.core.mail import BadHeaderError, EmailMessage
from django.shortcuts import redirect, render
 
from .forms import ContactoForm
 
 
def _avisar_por_correo(m):
    """Envía el mensaje al equipo. Si falla, el mensaje igual queda guardado en el admin."""
    destino = getattr(settings, "CONTACTO_DESTINO", "")
    if not destino:
        return
    cuerpo = (
        f"Nombre: {m.nombre}\n"
        f"Correo: {m.correo}\n"
        f"Motivo: {m.get_motivo_display()}\n\n"
        f"{m.mensaje}"
    )
    correo = EmailMessage(
        subject=f"[Contacto] {m.get_motivo_display()}",
        body=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destino],
        reply_to=[m.correo],  # al responder, se contesta a quien escribió
    )
    try:
        correo.send()
    except (BadHeaderError, OSError):
        pass
 
 
def contacto(request):
    if request.method == "POST":
        form = ContactoForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["sitio_web"]:
                # Campo trampa rellenado: probablemente un robot. Se ignora sin avisar.
                return redirect("core:contacto")
            _avisar_por_correo(form.save())
            messages.success(request, "Recibimos tu mensaje. ¡Gracias por escribirnos!")
            return redirect("core:contacto")  # evita reenviar el formulario al recargar
    else:
        form = ContactoForm()
    return render(request, "core/contacto.html", {"form": form})