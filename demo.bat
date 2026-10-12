@echo off
setlocal
rem Arranca la demo de MAControl para mostrarla desde el telefono en la red local.
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo No se encontro venv\Scripts\python.exe. Cree el entorno virtual e instale requirements.txt.
    exit /b 1
)

set "DJANGO_ENV=development"
set "PYTHONIOENCODING=utf-8"
rem Base aparte para no mezclar la demo con la de desarrollo.
set "RAIZ=%CD:\=/%"
set "DATABASE_URL=sqlite:///%RAIZ%/demo.sqlite3"

rem IPv4 privada de la interfaz con gateway, sin loopback, VPN ni adaptadores virtuales.
rem (dev.py rechaza IP publicas en ALLOWED_HOSTS).
set "IP="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.InterfaceAlias -notmatch 'vEthernet|Loopback|VPN' -and $_.IPv4Address.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)' } | Select-Object -First 1).IPv4Address.IPAddress"`) do set "IP=%%i"
if "%IP%"=="" (
    echo No se detecto la IP de la red local. Conectese a la red Wi-Fi e intente de nuevo.
    exit /b 1
)
set "ALLOWED_HOSTS=localhost,127.0.0.1,%IP%"

echo Preparando la base de la demo...
venv\Scripts\python.exe manage.py migrate --noinput
if errorlevel 1 (
    echo Fallo migrate.
    exit /b 1
)
venv\Scripts\python.exe manage.py cargar_demo
if errorlevel 1 (
    echo Fallo cargar_demo.
    exit /b 1
)

echo.
echo ================================================
echo  Sitio publico:  http://%IP%:8000/
echo  Panel:          http://%IP%:8000/panel/
echo.
echo  Administrador:  demo-admin     clave demo1234
echo  Empleado:       demo-empleado  clave demo1234
echo.
echo  Para apagar el servidor presione Ctrl+C.
echo ================================================
echo.
venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
endlocal
