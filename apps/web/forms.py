"""Formularios del panel para el contenido del sitio público."""

import json

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import URLValidator

from .imagenes import reprocesar_imagen
from .models import ClienteDestacado, Configuracion, PaginaServicio, Sector


class ReprocesaImagenesMixin:
    """Reprocesa las imágenes nuevas y borra del storage la que se reemplaza."""

    # campo -> formato de salida
    formatos_imagen = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._anteriores = {
            campo: getattr(self.instance, campo).name for campo in self.formatos_imagen
        }

    def _reprocesar(self, campo):
        archivo = self.cleaned_data.get(campo)
        if isinstance(archivo, UploadedFile):
            return reprocesar_imagen(
                archivo, formato_salida=self.formatos_imagen[campo]
            )
        return archivo

    def save(self, commit=True):
        instancia = super().save(commit=commit)
        if commit:
            for campo, anterior in self._anteriores.items():
                actual = getattr(instancia, campo).name
                if anterior and anterior != actual:
                    getattr(instancia, campo).storage.delete(anterior)
        return instancia


class ListaDeObjetosField(forms.JSONField):
    """JSON que debe ser una lista de dicts con exactamente `claves`, no vacías."""

    def __init__(self, *, claves, **kwargs):
        self.claves = tuple(claves)
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.Textarea(attrs={"rows": 8}))
        super().__init__(**kwargs)

    def prepare_value(self, value):
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, indent=2)

    def clean(self, value):
        lista = super().clean(value)
        if lista in (None, ""):
            return []
        if not isinstance(lista, list):
            raise forms.ValidationError("Debe ser una lista de objetos JSON.")
        for numero, elemento in enumerate(lista, start=1):
            if not isinstance(elemento, dict) or set(elemento) != set(self.claves):
                raise forms.ValidationError(
                    f"El elemento {numero} debe tener exactamente las claves: "
                    f"{', '.join(self.claves)}."
                )
            if not all(isinstance(v, str) and v.strip() for v in elemento.values()):
                raise forms.ValidationError(
                    f"El elemento {numero} tiene valores vacíos o que no son texto."
                )
        return lista


class ConfiguracionForm(forms.ModelForm):
    direcciones = ListaDeObjetosField(
        claves=("localidad", "direccion"), label="Direcciones"
    )
    redes = ListaDeObjetosField(claves=("nombre", "url"), label="Redes sociales")

    def clean_redes(self):
        validar_https = URLValidator(schemes=["https"])
        redes = self.cleaned_data["redes"]
        for red in redes:
            try:
                validar_https(red["url"])
            except forms.ValidationError:
                raise forms.ValidationError(
                    f"La URL de «{red['nombre']}» debe ser una dirección https válida."
                ) from None
        return redes

    class Meta:
        model = Configuracion
        fields = [
            "razon_social",
            "eslogan",
            "presentacion",
            "telefono",
            "whatsapp",
            "correo",
            "horario",
            "direcciones",
            "redes",
        ]


class PaginaServicioForm(ReprocesaImagenesMixin, forms.ModelForm):
    formatos_imagen = {"imagen_portada": "JPEG"}

    metodos = ListaDeObjetosField(claves=("titulo", "descripcion"), label="Métodos")
    faq = ListaDeObjetosField(
        claves=("pregunta", "respuesta"), label="Preguntas frecuentes"
    )
    sectores = forms.MultipleChoiceField(
        label="Sectores",
        choices=Sector.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = PaginaServicio
        fields = [
            "titulo_seo",
            "resumen",
            "problema",
            "adicional",
            "metodos",
            "faq",
            "sectores",
            "imagen_portada",
            "publicado",
        ]

    def clean_imagen_portada(self):
        return self._reprocesar("imagen_portada")


class ClienteDestacadoForm(ReprocesaImagenesMixin, forms.ModelForm):
    formatos_imagen = {"logo": "PNG"}

    class Meta:
        model = ClienteDestacado
        fields = ["nombre", "logo", "orden", "activo"]

    def clean_logo(self):
        return self._reprocesar("logo")
