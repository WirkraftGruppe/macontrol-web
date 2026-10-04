"""Tests de `presupuesto.sh` y `cambios.sh` (T8 de docs/planes/2026-09-23-esquema-agentes.md).

Se ejecutan con unittest (sin pytest):
    py -3 -m unittest discover -s .claude/hooks -p "test_presupuesto.py" -v

Cada test trabaja sobre repos git temporales (`tempfile`), con `core.autocrlf` en `false` y un
usuario local de prueba: no tocan el repo real del proyecto.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DIR_HOOKS = Path(__file__).resolve().parent
PRESUPUESTO = DIR_HOOKS / "presupuesto.sh"
CAMBIOS = DIR_HOOKS / "cambios.sh"


def texto(bytes_):
    """Decodifica una salida como UTF-8, sustituyendo lo que no se pueda decodificar."""
    return bytes_.decode("utf-8", errors="replace")


def git(repo, *argumentos):
    """Ejecuta git en el repo temporal y falla el test si git falla."""
    proceso = subprocess.run(["git", "-C", str(repo), *argumentos], capture_output=True, timeout=60)
    if proceso.returncode != 0:
        raise AssertionError(f"git {argumentos} falló: {texto(proceso.stderr)}")
    return texto(proceso.stdout)


def preparar_repo(repo):
    """Inicializa un repo temporal con config local (sin autocrlf) y usuario de prueba."""
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "core.autocrlf", "false")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "commit.gpgsign", "false")


def correr_presupuesto(*args, cwd=None):
    """Ejecuta presupuesto.sh con bash."""
    return subprocess.run(
        ["bash", PRESUPUESTO.as_posix(), *[str(a) for a in args]],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        timeout=60,
    )


def correr_cambios(*args, cwd=None):
    """Ejecuta cambios.sh con bash."""
    return subprocess.run(
        ["bash", CAMBIOS.as_posix(), *[str(a) for a in args]],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        timeout=60,
    )


class PresupuestoBase(unittest.TestCase):
    """Repo temporal con un commit base y algo de contenido versionado."""

    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("sin git")
        if shutil.which("bash") is None:
            self.skipTest("sin bash")
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        preparar_repo(self.repo)
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "archivo.md").write_text("línea 1\nlínea 2\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "docs(plan): demo")
        self.base = git(self.repo, "rev-parse", "HEAD").strip()

    def tearDown(self):
        self._tmp.cleanup()


class TestPresupuestoDentroDelMaximo(PresupuestoBase):
    def test_diff_bajo_el_maximo_sale_con_cero(self):
        with (self.repo / "docs" / "archivo.md").open("a", encoding="utf-8") as archivo:
            archivo.write("línea 3\nlínea 4\n")
        proceso = correr_presupuesto(self.repo, self.base, 400, "docs/archivo.md")
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 0, error)
        self.assertIn("total de líneas agregadas: 2", texto(proceso.stdout))


class TestPresupuestoSobreElMaximo(PresupuestoBase):
    def test_diff_sobre_el_maximo_sale_distinto_de_cero_y_lista_el_archivo(self):
        with (self.repo / "docs" / "archivo.md").open("a", encoding="utf-8") as archivo:
            archivo.write("línea 3\nlínea 4\nlínea 5\n")
        proceso = correr_presupuesto(self.repo, self.base, 1, "docs/archivo.md")
        salida = texto(proceso.stdout)
        self.assertNotEqual(proceso.returncode, 0)
        self.assertIn("total de líneas agregadas: 3", salida)
        self.assertIn("docs/archivo.md", salida)


class TestPresupuestoArchivoSinRastrearCuenta(PresupuestoBase):
    def test_archivo_nuevo_sin_rastrear_suma_sus_lineas(self):
        (self.repo / "docs" / "nuevo.md").write_text("a\nb\nc\n", encoding="utf-8")
        proceso = correr_presupuesto(self.repo, self.base, 400, "docs")
        salida = texto(proceso.stdout)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertIn("total de líneas agregadas: 3", salida)
        self.assertIn("docs/nuevo.md", salida)

    def test_archivo_sin_rastrear_sin_salto_de_linea_final_cuenta_esa_ultima_linea(self):
        (self.repo / "docs" / "sin_final.md").write_bytes(b"a\nb\nc")  # sin "\n" al final
        proceso = correr_presupuesto(self.repo, self.base, 400, "docs/sin_final.md")
        salida = texto(proceso.stdout)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertIn("total de líneas agregadas: 3", salida)

    def test_archivo_binario_no_suma_pero_se_lista(self):
        (self.repo / "docs" / "imagen.bin").write_bytes(b"\x00\x01binario\x02\x00")
        git(self.repo, "add", "docs/imagen.bin")
        proceso = correr_presupuesto(self.repo, self.base, 0, "docs")
        salida = texto(proceso.stdout)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertIn("total de líneas agregadas: 0", salida)
        self.assertIn("docs/imagen.bin", salida)


class TestPresupuestoBaseInexistente(PresupuestoBase):
    def test_base_inexistente_sale_distinto_de_cero(self):
        proceso = correr_presupuesto(self.repo, "deadbeef", 400, "docs")
        self.assertNotEqual(proceso.returncode, 0)
        self.assertIn("no existe el commit base", texto(proceso.stderr))


class TestPresupuestoUsoInvalido(unittest.TestCase):
    def setUp(self):
        if shutil.which("bash") is None:
            self.skipTest("sin bash")

    def test_sin_argumentos_sale_con_dos(self):
        proceso = correr_presupuesto()
        self.assertEqual(proceso.returncode, 2)
        self.assertIn("uso:", texto(proceso.stderr))

    def test_max_no_numerico_sale_con_dos(self):
        proceso = correr_presupuesto(".", "HEAD", "no-es-un-numero")
        self.assertEqual(proceso.returncode, 2)

    def test_repo_inexistente_sale_con_dos(self):
        with tempfile.TemporaryDirectory() as tmp:
            proceso = correr_presupuesto(Path(tmp) / "no-existe", "HEAD", 400)
            self.assertEqual(proceso.returncode, 2)


class TestCambiosConVariosWorktrees(unittest.TestCase):
    """`cambios.sh` sobre un repo con un worktree extra muestra su --stat."""

    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("sin git")
        if shutil.which("bash") is None:
            self.skipTest("sin bash")
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        preparar_repo(self.repo)
        (self.repo / "a.txt").write_text("contenido\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "inicial")

    def tearDown(self):
        self._tmp.cleanup()

    def test_worktree_extra_muestra_su_diff_stat_contra_main(self):
        extra = Path(self._tmp.name) / "extra"
        git(self.repo, "worktree", "add", "-b", "rama-extra", str(extra), "main")
        (extra / "b.txt").write_text("línea 1\nlínea 2\n", encoding="utf-8")
        git(extra, "add", "-A")
        git(extra, "commit", "-q", "-m", "T1: agrega b.txt")

        proceso = correr_cambios(self.repo, "main", "--stat")
        salida = texto(proceso.stdout)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertIn(self.repo.as_posix(), salida)
        self.assertIn(extra.as_posix(), salida)
        self.assertIn("rama-extra", salida)
        self.assertIn("b.txt", salida)
        self.assertIn("1 file changed", salida)

    def test_un_solo_worktree_se_muestra_igual_y_sale_con_cero(self):
        proceso = correr_cambios(self.repo, "main", "--stat")
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertIn(self.repo.as_posix(), texto(proceso.stdout))

    def test_rama_base_inexistente_sale_distinto_de_cero(self):
        proceso = correr_cambios(self.repo, "rama-que-no-existe")
        self.assertNotEqual(proceso.returncode, 0)

    def test_sin_argumentos_sale_con_dos(self):
        proceso = correr_cambios()
        self.assertEqual(proceso.returncode, 2)


# ---------------------------------------------------------------------------
# Marcador `<commit_base>` (T3 de docs/planes/2026-10-03-limites-ingreso.md)
# ---------------------------------------------------------------------------

def repo_con_plan(repo, registro=""):
    """Repo temporal con `docs(plan): demo` en la rama `plan/demo`; el Registro va en disco.

    Devuelve el hash completo del commit congelado. `registro` se escribe debajo del corte,
    con `{base}` reemplazado por ese hash.
    """
    preparar_repo(repo)
    plan = repo / "docs" / "planes" / "2026-01-01-demo.md"
    plan.parent.mkdir(parents=True)
    contenido = "# Plan: demo\n\n### T1 — algo\n\n## Registro de verificación\n\n"
    plan.write_text(contenido, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs(plan): demo")
    git(repo, "switch", "-q", "-c", "plan/demo")
    base = git(repo, "rev-parse", "HEAD").strip()
    plan.write_text(contenido + registro.replace("{base}", base), encoding="utf-8")
    return base


def test_marcador_commit_base_se_resuelve_del_registro(tmp_path):
    repo = tmp_path / "repo"
    repo_con_plan(repo, "commit_base: {base}\n")
    (repo / "nuevo.txt").write_text("a\nb\nc\n", encoding="utf-8")
    proceso = correr_presupuesto(repo, "<commit_base>", 5)
    salida = texto(proceso.stdout)
    assert proceso.returncode == 0, texto(proceso.stderr)
    assert "total de líneas agregadas: 4 (máximo: 5)" in salida
    assert "nuevo.txt" in salida  # 3 líneas del archivo nuevo + 1 de la línea commit_base del plan
    # Con el mismo marcador, un máximo menor al total sigue dando 1: el marcador no desactiva la medida.
    assert correr_presupuesto(repo, "<commit_base>", 3).returncode == 1


def test_marcador_sin_registro_sale_con_dos(tmp_path):
    repo = tmp_path / "repo"
    repo_con_plan(repo)  # el Registro no tiene la línea `commit_base:`
    proceso = correr_presupuesto(repo, "<commit_base>", 5)
    assert proceso.returncode == 2
    assert proceso.stdout == b""
    assert "commit_base sin resolver" in texto(proceso.stderr)


# ---------------------------------------------------------------------------
# Modo por subtarea `--subtarea T<n>` (T1 de docs/planes/2026-10-04-herramientas-plan.md)
# ---------------------------------------------------------------------------

def commitear(repo, asunto, archivo, lineas, modo="a"):
    """Agrega `lineas` líneas a `archivo` y commitea con ese asunto."""
    with (repo / archivo).open(modo, encoding="utf-8") as f:
        f.write("".join(f"{asunto} línea {i}\n" for i in range(lineas)))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", asunto)


def repo_con_base(tmp_path):
    """Repo temporal con un commit base; devuelve (repo, hash_base)."""
    repo = tmp_path / "repo"
    preparar_repo(repo)
    commitear(repo, "docs(plan): demo", "base.txt", 1)
    return repo, git(repo, "rev-parse", "HEAD").strip()


def test_modo_subtarea_mide_solo_commits_con_prefijo(tmp_path):
    repo, base = repo_con_base(tmp_path)
    commitear(repo, "T1: agrega a", "a.txt", 3)
    commitear(repo, "sin prefijo", "b.txt", 5)
    commitear(repo, "registro: algo", "c.txt", 2)
    (repo / "d.txt").write_text("x\ny\n", encoding="utf-8")  # sin commitear: no cuenta
    proceso = correr_presupuesto(repo, base, 10, "--subtarea", "T1")
    assert proceso.returncode == 0, texto(proceso.stderr)
    salida = texto(proceso.stdout)
    assert "total de líneas agregadas: 3 (máximo: 10)" in salida
    assert "a.txt" in salida and "b.txt" not in salida
    assert "sin commitear" in salida  # aviso de lo no commiteado
    error = texto(proceso.stderr)
    assert "sin prefijo" in error and "registro: algo" in error  # informativo por stderr
    assert correr_presupuesto(repo, base, 2, "--subtarea", "T1").returncode == 1
    # Sin ningún commit con el prefijo: total 0, exit 0 y el aviso.
    vacio = correr_presupuesto(repo, base, 10, "--subtarea", "T2")
    assert vacio.returncode == 0, texto(vacio.stderr)
    assert "total de líneas agregadas: 0" in texto(vacio.stdout)
    assert f"sin commits T2: desde {base}" in texto(vacio.stdout)


def test_dos_subtareas_mismo_archivo_no_se_suman(tmp_path):
    repo, base = repo_con_base(tmp_path)
    commitear(repo, "T1: primera", "compartido.txt", 2)
    commitear(repo, "T2: segunda", "compartido.txt", 4)
    t1 = correr_presupuesto(repo, base, 100, "--subtarea", "T1")
    t2 = correr_presupuesto(repo, base, 100, "--subtarea", "T2")
    assert "total de líneas agregadas: 2 " in texto(t1.stdout)
    assert "total de líneas agregadas: 4 " in texto(t2.stdout)


def test_modo_rutas_sigue_funcionando(tmp_path):
    repo, base = repo_con_base(tmp_path)
    commitear(repo, "sin prefijo", "a.txt", 3)  # el modo por rutas no mira los asuntos
    (repo / "b.txt").write_text("x\n", encoding="utf-8")  # sin rastrear: cuenta
    proceso = correr_presupuesto(repo, base, 10, "a.txt", "b.txt")
    assert proceso.returncode == 0, texto(proceso.stderr)
    assert "total de líneas agregadas: 4 (máximo: 10)" in texto(proceso.stdout)
    assert correr_presupuesto(repo, base, 3, "a.txt", "b.txt").returncode == 1


def test_modo_subtarea_ignora_merges_y_cuenta_sufijo_b(tmp_path):
    repo, base = repo_con_base(tmp_path)
    git(repo, "switch", "-q", "-c", "rama")
    commitear(repo, "T1: en la rama", "a.txt", 2)
    git(repo, "switch", "-q", "main")
    commitear(repo, "T1b: correccion", "b.txt", 3)
    commitear(repo, "T10: otra subtarea", "c.txt", 7)
    git(repo, "merge", "-q", "--no-ff", "-m", "T1: integra rama", "rama")
    t1 = correr_presupuesto(repo, base, 100, "--subtarea", "T1")
    assert t1.returncode == 0, texto(t1.stderr)
    assert "total de líneas agregadas: 5 " in texto(t1.stdout)  # 2 de T1 + 3 de T1b; ni merge ni T10
    assert "c.txt" not in texto(t1.stdout)
    # Con letra en el id solo cuenta el exacto.
    assert "total de líneas agregadas: 3 " in texto(correr_presupuesto(repo, base, 100, "--subtarea", "T1b").stdout)
    assert "total de líneas agregadas: 7 " in texto(correr_presupuesto(repo, base, 100, "--subtarea", "T10").stdout)


def test_modo_subtarea_rechaza_rutas_e_id_invalido(tmp_path):
    repo, base = repo_con_base(tmp_path)
    assert correr_presupuesto(repo, base, 10, "--subtarea", "T1", "a.txt").returncode == 2
    for invalido in ("", "T", "1", "t1", "T1B", "T1ab", "T1:", "X1"):
        assert correr_presupuesto(repo, base, 10, "--subtarea", invalido).returncode == 2, invalido
    assert correr_presupuesto(repo, base, 10, "--subtarea").returncode == 2


if __name__ == "__main__":
    unittest.main()
