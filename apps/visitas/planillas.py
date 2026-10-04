"""Validación de los datos de una planilla contra el esquema de su servicio."""

from datetime import date


def _es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


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
    if tipo == "texto" and not isinstance(valor, str):
        return ["Debe ser un texto."]
    if tipo == "numero" and not _es_numero(valor):
        return ["Debe ser un número."]
    if tipo == "booleano" and not isinstance(valor, bool):
        return ["Debe ser verdadero o falso."]
    if tipo == "fecha" and not _es_fecha_iso(valor):
        return ["Debe ser una fecha válida con formato AAAA-MM-DD."]
    if tipo == "opcion":
        # `in` sobre una lista con un valor no hashable (dict, lista) no falla.
        if isinstance(valor, (dict, list)) or valor not in opciones:
            return ["Debe ser una de las opciones permitidas."]
    if tipo == "opcion_multiple":
        if not isinstance(valor, list):
            return ["Debe ser una lista de opciones."]
        if any(isinstance(v, (dict, list)) or v not in opciones for v in valor):
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
