from django import forms
from .models import FotoArmario


class FotoArmarioForm(forms.ModelForm):
    class Meta:
        model = FotoArmario
        fields = ["imagen", "categoria"]

    def clean_imagen(self):
        imagen = self.cleaned_data["imagen"]

        if imagen.size > 10 * 1024 * 1024:
            raise forms.ValidationError(
                "La imagen no debe superar los 10 MB."
            )

        extensiones = (".jpg", ".jpeg", ".png")
        if not imagen.name.lower().endswith(extensiones):
            raise forms.ValidationError(
                "Solo se permiten archivos JPG, JPEG o PNG."
            )

        if imagen.image.format not in ("JPEG", "PNG"):
            raise forms.ValidationError(
                "El archivo debe ser una imagen JPG o PNG v\u00e1lida."
            )

        return imagen


class EditarPrendaForm(forms.ModelForm):
    class Meta:
        model = FotoArmario
        fields = ["nombre", "categoria"]
