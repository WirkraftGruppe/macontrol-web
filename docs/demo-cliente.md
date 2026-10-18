# Demo para el cliente

Guía para mostrar MAControl en una computadora con Windows, con el sitio público y el panel visibles desde un teléfono.

## Requisitos

- La computadora y el teléfono deben estar en la misma red Wi-Fi.
- La primera vez, Windows pregunta si se permite el acceso de Python a la red: elegir **Permitir** (redes privadas). Si no apareció el aviso o se cerró, permitir Python en el Firewall de Windows y volver a arrancar.
- El entorno virtual `venv` ya instalado en la carpeta del proyecto.

## Cómo arrancar

1. Hacer doble clic en `demo.bat`, en la carpeta del proyecto.
2. El script prepara una base aparte (`demo.sqlite3`), carga los datos de ejemplo y muestra en pantalla las direcciones y las cuentas.
3. Dejar la ventana abierta mientras dure la demo: ahí corre el servidor.

Direcciones (la IP la muestra el script):

- Sitio público: `http://<ip>:8000/`
- Panel: `http://<ip>:8000/panel/`

Cuentas (clave de ambas: `demo1234`):

- `demo-admin`: administrador, ve el panel completo.
- `demo-empleado`: empleado, usa solo la aplicación móvil; el panel le está vedado.

## Recorrido

### 1. Sitio público

1. Inicio (`/`): presentación de la empresa y sus servicios.
2. Servicios (`/servicio/<servicio>/`): abrir uno desde el inicio.
3. Empresa (`/empresa/`).
4. Contacto (`/contacto/`): teléfono y WhatsApp.

### 2. Panel como `demo-admin`

Ingresar en `/panel/` con `demo-admin`.

1. Tablero (`/panel/`): resumen de visitas y alertas.
2. Mapa (`/panel/mapa/`): sitios coloreados según el estado de sus puntos.
3. Clientes (`/panel/clientes/`): abrir la ficha de un cliente.
4. Sitios (`/panel/sitios/`): abrir un sitio y mostrar el plano con sus puntos de control.
5. QR de un punto: desde el sitio, abrir el QR de un punto (`/panel/sitios/puntos/<n>/qr.png`).
6. Visitas (`/panel/visitas/`): abrir la ficha de una visita, con sus fotos y los productos aplicados.
7. Incidencias de ubicación: en el listado de visitas, filtrar por incidencias y abrir una.
8. Historial: el mismo listado de visitas, filtrado por proyecto o por empleado.

### 3. Desde el teléfono

Abrir en el teléfono `http://<ip>:8000/panel/`, ingresar con `demo-admin` y repetir el tablero, el mapa y la ficha de una visita. El panel se adapta a la pantalla pequeña.

## Qué no incluye la demo

No se escanean códigos QR: por decisión del usuario, el QR se muestra solo como imagen en el panel. Las visitas y las revisiones de ejemplo ya vienen cargadas.

## Cómo apagar

En la ventana de `demo.bat`, presionar Ctrl+C y confirmar. Cerrar la ventana también detiene el servidor.

## Cómo volver a cargar los datos

- Para restaurar los datos de ejemplo, volver a ejecutar `demo.bat`: `cargar_demo` se puede repetir sin duplicar.
- Para empezar de cero, apagar el servidor, borrar el archivo `demo.sqlite3` de la carpeta del proyecto y ejecutar `demo.bat` de nuevo.

## Llevar la demo a otra PC

En esta PC, desde la raíz del proyecto, generar el paquete:

```bash
./venv/Scripts/python.exe herramientas/empaquetar_demo.py
```

- La primera vez descarga Python embebido y las dependencias; con `--sin-descarga` usa la caché ya descargada.
- `--destino <carpeta>` cambia dónde se deja el resultado.
- El resultado es `dist/macontrol-demo.zip`.

En la otra PC:

1. Copiar el `.zip` (por ejemplo con un pendrive) y descomprimirlo.
2. Hacer doble clic en `demo.bat`.
3. Aceptar el aviso del firewall en redes privadas.
4. Desde el celular, en la misma Wi-Fi, abrir la dirección "Teléfono" que muestra la ventana.

La demo portátil no genera PDF. Para reiniciar los datos, apagar el servidor y borrar `demo.sqlite3`.
