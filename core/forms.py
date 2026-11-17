from django import forms
from .models import Mensaje
 
 
class ContactoForm(forms.ModelForm):
    # Campo trampa contra spam: las personas no lo ven y los robots suelen rellenarlo.
    sitio_web = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )
 
    class Meta:
        model = Mensaje
        fields = ["nombre", "correo", "motivo", "mensaje"]
        widgets = {"mensaje": forms.Textarea(attrs={"rows": 6})}
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["motivo"].choices = [("", "Selecciona un motivo")] + list(Mensaje.MOTIVOS)
 