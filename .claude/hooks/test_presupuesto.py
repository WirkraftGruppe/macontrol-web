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


if __name__ == "__main__":
    unittest.main()
