"""Validación de los datos de una planilla contra el esquema de su servicio."""

import math
from datetime import date

MAX_LARGO_TEXTO = 2000
MAX_DIGITOS_NUMERO = 15
TIPOS = ("texto", "numero", "booleano", "opcion", "opcion_multiple", "fecha")


def _es_numero(valor):
    """Número finito, no booleano y con a lo sumo `MAX_DIGITOS_NUMERO` dígitos."""
    return (
        isinstance(valor, (int, float))
        and not isinstance(valor, bool)
        and (isinstance(valor, int) or math.isfinite(valor))
        and abs(valor) < 10**MAX_DIGITOS_NUMERO
    )


def _es_opcion(valor, opciones):
    """Pertenencia con tipo estricto: `True` no es la opción `1` ni `False` la `0`."""
    if isinstance(valor, (dict, list)):
        return False
    return any(
        isinstance(valor, bool) == isinstance(opcion, bool) and valor == opcion
        for opcion in opciones
    )


def _es_fecha_iso(valor):
    if not isinstance(valor, str) or len(valor) != 10:
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def _errores_de_campo(campo, valor):
    """Mensajes de error de un valor presente según el tipo del campo."""
    tipo = campo["tipo"]
    opciones = campo.get("opciones") or []
    if tipo not in TIPOS:
        return ["Tipo de campo desconocido."]
    if tipo == "texto":
        if not isinstance(valor, str):
            return ["Debe ser un texto."]
        if len(valor) > MAX_LARGO_TEXTO:
            return [f"No puede superar los {MAX_LARGO_TEXTO} caracteres."]
    if tipo == "numero" and not _es_numero(valor):
        return ["Debe ser un número."]
    if tipo == "booleano" and not isinstance(valor, bool):
        return ["Debe ser verdadero o falso."]
    if tipo == "fecha" and not _es_fecha_iso(valor):
        return ["Debe ser una fecha válida con formato AAAA-MM-DD."]
    if tipo == "opcion":
        if not _es_opcion(valor, opciones):
            return ["Debe ser una de las opciones permitidas."]
    if tipo == "opcion_multiple":
        if not isinstance(valor, list):
            return ["Debe ser una lista de opciones."]
        if not all(_es_opcion(v, opciones) for v in valor):
            return ["Todos los valores deben ser opciones permitidas."]
        if len({repr(v) for v in valor}) != len(valor):
            return ["No puede repetir opciones."]
    return []


def validar_datos(esquema, datos) -> dict[str, list[str]]:
    """Valida `datos` contra `esquema`; devuelve errores por clave (vacío si es válido).

    Rechaza obligatorios faltantes, tipos incorrectos, opciones fuera de la lista y
    claves que el esquema no declara. Un error global usa la clave `datos`.
    """
    if not isinstance(datos, dict):
        return {"datos": ["Debe ser un objeto con los valores de la planilla."]}
    errores = {}
    claves = set()
    for campo in esquema:
        clave = campo["clave"]
        claves.add(clave)
        if datos.get(clave) is None:
            if campo.get("obligatorio"):
                errores[clave] = ["Este campo es obligatorio."]
            continue
        mensajes = _errores_de_campo(campo, datos[clave])
        if mensajes:
            errores[clave] = mensajes
    for clave in datos:
        if clave not in claves:
            errores[clave] = ["Campo desconocido en esta planilla."]
    return errores


def _valor_legible(campo, valor):
    if valor is None or valor == "" or valor == []:
        return "—"
    if campo["tipo"] == "booleano":
        return "Sí" if valor else "No"
    if campo["tipo"] == "opcion_multiple":
        return ", ".join(str(v) for v in valor)
    return str(valor)


def filas_planilla(esquema, datos):
    """Filas `(etiqueta, valor legible)` en el orden del esquema copiado."""
    datos = datos or {}
    return [
        (campo["etiqueta"], _valor_legible(campo, datos.get(campo["clave"])))
        for campo in esquema
    ]
