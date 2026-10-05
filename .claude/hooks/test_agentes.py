"""Tests de los agentes de `.claude/agents/` (T3 de docs/planes/2026-10-04-herramientas-plan.md).

Se ejecutan con pytest:
    py -3 -m pytest .claude/hooks/test_agentes.py -q
"""
from pathlib import Path

import pytest
import yaml

DIR_AGENTES = Path(__file__).resolve().parent.parent / "agents"
ARCHIVOS = sorted(DIR_AGENTES.glob("*.md"))


def leer_frontmatter(ruta):
    """Devuelve el texto YAML entre los dos `---` iniciales del archivo."""
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    assert lineas and lineas[0] == "---", f"{ruta.name}: no empieza con ---"
    fin = lineas.index("---", 1)
    return "\n".join(lineas[1:fin])


def test_hay_agentes():
    assert ARCHIVOS, "no hay agentes en .claude/agents"


@pytest.mark.parametrize("ruta", ARCHIVOS, ids=lambda r: r.name)
def test_frontmatter_de_agentes_es_yaml_valido(ruta):
    datos = yaml.safe_load(leer_frontmatter(ruta))
    assert isinstance(datos, dict), f"{ruta.name}: el frontmatter no es un mapa"
    assert datos.get("name") == ruta.stem, f"{ruta.name}: name no coincide con el archivo"
    descripcion = datos.get("description")
    assert isinstance(descripcion, str) and descripcion.strip(), (
        f"{ruta.name}: description vacía"
    )


def test_juez_plan_cubre_recuentos_absolutos():
    """El juez de plan marca como bloqueante el recuento absoluto que el plan altera."""
    texto = (DIR_AGENTES / "juez-plan.md").read_text(encoding="utf-8")
    assert "recuento absoluto" in texto, "juez-plan.md no menciona el recuento absoluto"
    inicio = texto.index("recuento absoluto")
    contexto = texto[inicio : inicio + 800]
    assert "bloqueante" in contexto, "el recuento absoluto no se marca como bloqueante"
    assert "cierra exactamente" in contexto, "falta la forma relativa (cierra exactamente N)"
    assert "plan sin código" in contexto, "falta la excepción del plan sin código"
