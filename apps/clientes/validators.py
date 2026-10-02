"""Validadores del módulo de clientes."""

from django.core.exceptions import ValidationError

PESOS_CUIT = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def validar_cuit(valor):
    """Valida el dígito verificador del CUIT (módulo 11).

    Si el valor no son exactamente 11 dígitos no hace nada: ese error lo
    informa el RegexValidator del campo.
    """
    if not (len(valor) == 11 and valor.isascii() and valor.isdigit()):
        return
    suma = sum(int(d) * p for d, p in zip(valor[:10], PESOS_CUIT))
    resto = 11 - suma % 11
    if resto == 11:
        esperado = 0
    elif resto == 10:
        esperado = 9
    else:
        esperado = resto
    if esperado != int(valor[10]):
        raise ValidationError("El dígito verificador del CUIT no es válido.")
