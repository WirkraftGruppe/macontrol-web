"""Tests de `pendientes.py` (consolidado de pendientes por plan)."""
import json
import subprocess
import sys
from pathlib import Path

DIR_HOOKS = Path(__file__).resolve().parent
SCRIPT = DIR_HOOKS / "pendientes.py"

CORTE = "## Registro de verificación\n\n(vacío)\n\n## Pendientes que deja este plan\n\n"


def plan(raiz, nombre, problemas="", decisiones="", cierra="", arriba=""):
    """Escribe docs/planes/<nombre>.md con la sección de pendientes debajo del corte."""
    carpeta = Path(raiz) / "docs" / "planes"
    carpeta.mkdir(parents=True, exist_ok=True)
    cuerpo = (
        f"# Plan\n\n{arriba}\n{CORTE}"
        f"### Problemas\n\n{problemas}\n### Decisiones\n\n{decisiones}\n### Cierra\n\n{cierra}\n"
    )
    (carpeta / f"{nombre}.md").write_text(cuerpo, encoding="utf-8")


def correr(raiz, *args, env=None):
    """Ejecuta pendientes.py con --raiz y devuelve el proceso (stdout en bytes)."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--raiz", str(raiz), *args],
        capture_output=True,
        timeout=60,
        env=env,
    )


def como_json(raiz):
    proceso = correr(raiz, "--json")
    assert proceso.returncode == 0, proceso.stderr
    return json.loads(proceso.stdout.decode("utf-8"))


def test_abiertos_son_abiertos_menos_cerrados(tmp_path):
    plan(
        tmp_path,
        "2026-01-01-uno",
        problemas="- P-uno-1 [menor] primero\n- P-uno-2 [importante] segundo\n  sub-viñeta larga\n",
    )
    plan(tmp_path, "2026-01-02-dos", cierra="- cierra: P-uno-1 — se corrigió\n")
    datos = como_json(tmp_path)
    assert [p["id"] for p in datos["abiertos"]] == ["P-uno-2"]
    assert datos["abiertos"][0]["severidad"] == "importante"
    assert "sub-viñeta larga" in datos["abiertos"][0]["texto"]
    assert datos["avisos"] == []


def test_id_duplicado_avisa(tmp_path):
    plan(tmp_path, "2026-01-01-uno", problemas="- P-uno-1 [menor] a\n- P-uno-1 [menor] b\n")
    datos = como_json(tmp_path)
    assert any("duplicado" in a and "P-uno-1" in a for a in datos["avisos"])


def test_cierre_de_id_inexistente_avisa(tmp_path):
    plan(tmp_path, "2026-01-01-uno", cierra="- cierra: P-uno-9 — nada\n")
    datos = como_json(tmp_path)
    assert any("inexistente" in a and "P-uno-9" in a for a in datos["avisos"])


def test_id_con_slug_ajeno_avisa(tmp_path):
    plan(tmp_path, "2026-01-01-uno", problemas="- P-otro-1 [menor] x\n")
    datos = como_json(tmp_path)
    assert any("slug" in a and "P-otro-1" in a for a in datos["avisos"])


def test_severidad_y_forma_invalida_avisan_con_archivo_y_linea(tmp_path):
    plan(tmp_path, "2026-01-01-uno", problemas="- P-uno-1 [grave] x\nlinea suelta\n")
    datos = como_json(tmp_path)
    assert any("severidad" in a for a in datos["avisos"])
    assert any("2026-01-01-uno.md:" in a and "forma" in a for a in datos["avisos"])


def test_seccion_arriba_del_corte_se_ignora(tmp_path):
    arriba = "## Pendientes que deja este plan\n\n### Problemas\n\n- P-uno-7 [menor] de ejemplo\n"
    plan(tmp_path, "2026-01-01-uno", problemas="- P-uno-1 [menor] real\n", arriba=arriba)
    datos = como_json(tmp_path)
    assert [p["id"] for p in datos["abiertos"]] == ["P-uno-1"]


def test_sin_planes_sale_con_cero(tmp_path):
    proceso = correr(tmp_path)
    assert proceso.returncode == 0
    assert json.loads(correr(tmp_path, "--json").stdout) == {"abiertos": [], "avisos": []}


def test_json_trae_el_slug_del_plan(tmp_path):
    plan(tmp_path, "2026-10-03-pendientes-heredados", problemas="- P-pendientes-heredados-1 [menor] x\n")
    assert como_json(tmp_path)["abiertos"][0]["plan"] == "pendientes-heredados"


def test_salida_utf8_con_caracteres_fuera_de_cp1252(tmp_path):
    plan(tmp_path, "2026-01-01-uno", problemas="- P-uno-1 [menor] ａｄｍ\n")
    entorno = {"PYTHONIOENCODING": "cp1252", "SYSTEMROOT": "C:\Windows"}
    proceso = correr(tmp_path, env=entorno)
    assert proceso.returncode == 0
    assert "ａｄｍ" in proceso.stdout.decode("utf-8")


def test_salida_de_texto_agrupa_por_severidad_y_avisos_al_final(tmp_path):
    plan(
        tmp_path,
        "2026-01-01-uno",
        problemas="- P-uno-1 [menor] m\n- P-uno-2 [bloqueante] b\n- P-uno-2 [menor] dup\n",
    )
    salida = correr(tmp_path).stdout.decode("utf-8")
    assert salida.index("P-uno-2") < salida.index("P-uno-1") < salida.index("duplicado")
