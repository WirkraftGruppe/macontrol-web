"""Arma la carpeta portátil `macontrol-demo/` (y su zip) para correr la demo en otra PC.

Uso, desde la raíz del proyecto y con el Python del venv:

    ./venv/Scripts/python.exe herramientas/empaquetar_demo.py [--destino dist] [--sin-descarga]

El resultado queda en `<destino>/macontrol-demo/` y `<destino>/macontrol-demo.zip`.
La carpeta lleva Python embebido, las dependencias de `requirements.txt`, el código
versionado, un `demo.bat` y un `LEEME.txt`. No lleva pip ni WeasyPrint funcional:
el paquete portátil no genera PDF.

La caché (`dist/cache/` del checkout principal, compartida por los worktrees) guarda el
Python embebido y las wheels. Con `--sin-descarga` no se usa la red: si falta algo en la
caché, el script falla nombrando qué falta.
"""

import argparse
import hashlib
import re
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION_PYTHON = "3.13.15"
NOMBRE_EMBEBIDO = f"python-{VERSION_PYTHON}-embed-amd64.zip"
URL_EMBEBIDO = f"https://www.python.org/ftp/python/{VERSION_PYTHON}/{NOMBRE_EMBEBIDO}"
TAMANO_EMBEBIDO = 11009825
# SHA-256 publicado por python.org: está en el paquete de firma
# `<URL_EMBEBIDO>.sigstore` (campo messageSignature.messageDigest.digest, en base64).
# Coincide con el calculado sobre el archivo descargado el 2026-10-12.
SHA256_EMBEBIDO = "d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf"

NOMBRE_PAQUETE = "macontrol-demo"
RUTAS_CODIGO = [
    "apps",
    "config",
    "templates",
    "static",
    "manage.py",
    "requirements.txt",
    "docs/demo-cliente.md",
]
# Carpetas y patrones que nunca viajan, aunque estuvieran versionados.
PARTES_EXCLUIDAS = {"venv", "worktrees", ".git", "media", ".claude", "__pycache__"}

PTH = "python313.zip\n.\nLib\\site-packages\n..\nimport site\n"

DEMO_BAT = r"""@echo off
setlocal
chcp 65001 >nul
rem Arranca la demo de MAControl desde esta carpeta, sin instalar nada en la PC.
cd /d "%~dp0"

set "DJANGO_ENV=development"
set "PYTHONIOENCODING=utf-8"
set "DATABASE_URL=sqlite:///demo.sqlite3"

rem IPv4 privada de la interfaz con gateway, sin loopback, VPN ni adaptadores virtuales.
rem (dev.py rechaza IP publicas en ALLOWED_HOSTS).
set "IP="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.InterfaceAlias -notmatch 'vEthernet|Loopback|VPN' -and $_.IPv4Address.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)' } | Select-Object -First 1).IPv4Address.IPAddress"`) do set "IP=%%i"
if "%IP%"=="" (
    set "ALLOWED_HOSTS=localhost,127.0.0.1"
    echo AVISO: no se detecto la IP de la red local. La demo solo abrira en esta PC.
    echo Conecte la PC a la red Wi-Fi y vuelva a abrir demo.bat para usarla desde el telefono.
) else (
    set "ALLOWED_HOSTS=localhost,127.0.0.1,%IP%"
)

echo Preparando la base de la demo...
python\python.exe manage.py migrate --noinput
if errorlevel 1 (
    echo Fallo migrate.
    exit /b 1
)
python\python.exe manage.py cargar_demo
if errorlevel 1 (
    echo Fallo cargar_demo.
    exit /b 1
)

echo.
echo ================================================
echo  Notebook: http://localhost:8000/
if not "%IP%"=="" echo  Teléfono (misma Wi-Fi): http://%IP%:8000/
echo  Panel:    http://localhost:8000/panel/
echo.
echo  Administrador:  demo-admin     clave demo1234
echo  Empleado:       demo-empleado  clave demo1234
echo.
echo  Para apagar el servidor presione Ctrl+C.
echo ================================================
echo.
if not "%DEMO_SIN_NAVEGADOR%"=="1" start "" http://localhost:8000/
python\python.exe manage.py runserver 0.0.0.0:8000 --noreload
endlocal
"""

LEEME = """MAControl - demo portátil

Esta carpeta corre la demo sin instalar nada: trae su propio Python.
1. Copie la carpeta completa a la PC (Windows 10 u 11, 64 bits).
2. Haga doble clic en demo.bat. La primera vez prepara la base y tarda unos segundos.
3. En la notebook se abre http://localhost:8000/ en el navegador.
4. Desde el teléfono, con la misma red Wi-Fi, abra la dirección "Teléfono" que muestra la ventana.
5. Windows pregunta por el firewall: acepte el acceso en redes privadas para usar el teléfono.
6. Usuarios de prueba: demo-admin y demo-empleado, clave demo1234.
7. Para apagar, cierre la ventana negra o presione Ctrl+C.
La demo guarda sus datos en demo.sqlite3 dentro de esta carpeta; borrarlo la reinicia.
Esta versión no genera PDF.
"""


class ErrorEmpaquetado(Exception):
    """Falla esperable del empaquetado, con un mensaje claro para quien lo corre."""


def raiz_proyecto() -> Path:
    return Path(__file__).resolve().parent.parent


def dir_cache(raiz: Path) -> Path:
    """Caché `dist/cache/` del checkout principal (los worktrees la comparten)."""
    resultado = subprocess.run(
        ["git", "-C", str(raiz), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(resultado.stdout.strip()).parent / "dist" / "cache"


def sha256_archivo(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def embebido_valido(ruta: Path) -> bool:
    return (
        ruta.is_file()
        and ruta.stat().st_size == TAMANO_EMBEBIDO
        and sha256_archivo(ruta) == SHA256_EMBEBIDO
    )


def obtener_embebido(cache: Path, sin_descarga: bool) -> Path:
    """Devuelve el zip del Python embebido verificado, descargándolo si hace falta."""
    ruta = cache / NOMBRE_EMBEBIDO
    if not embebido_valido(ruta):
        if sin_descarga:
            raise ErrorEmpaquetado(
                f"Falta en la caché (o no coincide el SHA-256) {ruta}; "
                "corra sin --sin-descarga para descargarlo."
            )
        cache.mkdir(parents=True, exist_ok=True)
        print(f"Descargando {URL_EMBEBIDO}")
        urllib.request.urlretrieve(URL_EMBEBIDO, ruta)  # noqa: S310 (URL fija https)
        if not embebido_valido(ruta):
            ruta.unlink(missing_ok=True)
            raise ErrorEmpaquetado(
                f"{NOMBRE_EMBEBIDO} descargado no coincide con el tamaño o el SHA-256 esperados."
            )
    return ruta


def _borrar_solo_lectura(funcion, ruta, _info):
    Path(ruta).chmod(stat.S_IWRITE)
    funcion(ruta)


def limpiar_destino(paquete: Path) -> None:
    """Borra solo la carpeta del paquete y su zip, nada más del destino."""
    if paquete.exists():
        shutil.rmtree(paquete, onexc=_borrar_solo_lectura)
    paquete.with_suffix(".zip").unlink(missing_ok=True)


def preparar_python(embebido: Path, paquete: Path) -> Path:
    destino = paquete / "python"
    with zipfile.ZipFile(embebido) as zf:
        zf.extractall(destino)
    (destino / "python313._pth").write_text(PTH, encoding="ascii", newline="\n")
    return destino


def pip(args: list[str]) -> str:
    """Corre el pip del Python que ejecuta el script; falla con su salida si no termina en 0."""
    resultado = subprocess.run(
        [sys.executable, "-m", "pip", *args, "--disable-pip-version-check"],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        salida = (resultado.stdout + resultado.stderr).strip()
        sin_wheel = re.search(r"No matching distribution found for (\S+)", salida)
        if sin_wheel:
            raise ErrorEmpaquetado(
                f"El paquete {sin_wheel.group(1)} no tiene wheel para win_amd64/cp313 "
                f"(no se compila desde fuente).\n{salida}"
            )
        raise ErrorEmpaquetado(f"pip {args[0]} falló:\n{salida}")
    return resultado.stdout


OPCIONES_PLATAFORMA = [
    "--only-binary",
    ":all:",
    "--platform",
    "win_amd64",
    "--python-version",
    "3.13",
    "--implementation",
    "cp",
]


def instalar_dependencias(raiz: Path, cache: Path, python: Path, sin_descarga: bool) -> None:
    wheels = cache / "wheels"
    requisitos = str(raiz / "requirements.txt")
    if sin_descarga:
        if not wheels.is_dir() or not any(wheels.glob("*.whl")):
            raise ErrorEmpaquetado(
                f"Faltan las wheels en la caché ({wheels}); corra sin --sin-descarga."
            )
    else:
        wheels.mkdir(parents=True, exist_ok=True)
        print("Descargando wheels de requirements.txt")
        pip(["download", *OPCIONES_PLATAFORMA, "-d", str(wheels), "-r", requisitos])
    print("Instalando dependencias en el Python embebido")
    pip(
        [
            "install",
            "--no-index",
            "--find-links",
            str(wheels),
            *OPCIONES_PLATAFORMA,
            "--target",
            str(python / "Lib" / "site-packages"),
            "-r",
            requisitos,
        ]
    )


def archivos_codigo(raiz: Path) -> list[str]:
    salida = subprocess.run(
        ["git", "-C", str(raiz), "ls-files", "-z", "--", *RUTAS_CODIGO],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    archivos = []
    for relativa in filter(None, salida.split("\0")):
        partes = Path(relativa).parts
        nombre = partes[-1]
        if PARTES_EXCLUIDAS & set(partes) or nombre.endswith(".sqlite3") or nombre.startswith(".env"):
            continue
        archivos.append(relativa)
    return archivos


def copiar_codigo(raiz: Path, paquete: Path) -> int:
    archivos = archivos_codigo(raiz)
    for relativa in archivos:
        destino = paquete / relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raiz / relativa, destino)
    return len(archivos)


def escribir_textos(paquete: Path) -> None:
    """`demo.bat` con CRLF (cmd lo exige) y `LEEME.txt` con CRLF para el Bloc de notas."""
    for nombre, texto in (("demo.bat", DEMO_BAT), ("LEEME.txt", LEEME)):
        (paquete / nombre).write_bytes(texto.replace("\n", "\r\n").encode("utf-8"))


def verificar_config(paquete: Path) -> None:
    """Comprueba que el embebido importa `config` y Django desde la carpeta del paquete."""
    resultado = subprocess.run(
        [str(paquete / "python" / "python.exe"), "-B", "-c", "import config, django"],
        cwd=paquete,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise ErrorEmpaquetado(
            f"El Python embebido no importa config/django:\n{resultado.stderr.strip()}"
        )


def comprimir(paquete: Path) -> Path:
    ruta_zip = paquete.with_suffix(".zip")
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for archivo in sorted(paquete.rglob("*")):
            if archivo.is_file():
                zf.write(archivo, Path(paquete.name) / archivo.relative_to(paquete))
    return ruta_zip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Empaqueta la demo portátil de MAControl.")
    parser.add_argument("--destino", default="dist", help="carpeta de salida (por defecto dist)")
    parser.add_argument(
        "--sin-descarga",
        action="store_true",
        help="no usa la red: toma el embebido y las wheels de la caché",
    )
    args = parser.parse_args(argv)

    raiz = raiz_proyecto()
    destino = Path(args.destino).resolve()
    paquete = destino / NOMBRE_PAQUETE
    try:
        cache = dir_cache(raiz)
        embebido = obtener_embebido(cache, args.sin_descarga)
        limpiar_destino(paquete)
        python = preparar_python(embebido, paquete)
        instalar_dependencias(raiz, cache, python, args.sin_descarga)
        cantidad = copiar_codigo(raiz, paquete)
        escribir_textos(paquete)
        verificar_config(paquete)
        ruta_zip = comprimir(paquete)
    except ErrorEmpaquetado as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    megas = ruta_zip.stat().st_size / (1024 * 1024)
    print(f"Archivos de código copiados: {cantidad}")
    print(f"Zip: {ruta_zip} ({megas:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
