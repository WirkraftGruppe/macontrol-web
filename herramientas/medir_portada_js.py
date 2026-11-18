"""Mide el comportamiento del JS de la portada (reproducción, pausas y diálogo).

Lo llama `medir_portada.py` con el mismo navegador y la misma URL. La evaluación de
las observaciones (`evaluar_observaciones`) es pura y se testea sin navegador.
"""

from medir_portada import OBJETIVO_MINIMO, comprobar, evaluar

FONDO = "document.querySelector('#hero .hero-video')"
INSTITUCIONAL = "document.querySelector('#video-dialogo video')"
BOTON_CERRAR = (
    "e => { const r = e.getBoundingClientRect(); return [r.width, r.height]; }"
)


def evaluar_observaciones(obs):
    """Convierte lo observado en el navegador (un dict) en una lista de mediciones."""
    pulsaciones = obs["aria_pressed"]
    ancho, alto = obs["cerrar"]
    return [
        comprobar("fondo se reproduce", obs["reproduce"]),
        comprobar("movimiento reducido: fondo pausado", obs["reducido_pausado"]),
        comprobar("se pausa al sacar la portada del viewport", obs["pausa_fuera"]),
        comprobar("se pausa al abrir el diálogo", obs["pausa_dialogo"]),
        comprobar("al cerrar, el institucional queda pausado", obs["cerrado_pausado"]),
        comprobar(
            "botón de pausa alterna aria-pressed",
            pulsaciones == ["true", "false"],
            str(pulsaciones),
        ),
        evaluar("objetivo móvil cerrar diálogo ancho", ancho, minimo=OBJETIVO_MINIMO),
        evaluar("objetivo móvil cerrar diálogo alto", alto, minimo=OBJETIVO_MINIMO),
        comprobar(
            "sin JS: Ver video es enlace al mp4",
            obs["href_sin_js"].endswith(".mp4"),
            obs["href_sin_js"],
        ),
        comprobar("sin JS: título y Llamar ahora visibles", obs["visibles_sin_js"]),
    ]


def _esperar(pagina, expresion):
    """True si la expresión se cumple antes de 8 s.

    Sondea con `evaluate` y no con `wait_for_function`: esa ruta usa `eval`, que la
    CSP del sitio bloquea (y no se usa `bypass_csp` para medir con la CSP real).
    """
    for _ in range(80):
        if pagina.evaluate(expresion):
            return True
        pagina.wait_for_timeout(100)
    return False


def observar_con_js(navegador, base):
    """Observaciones con JS en 375×812: reproducción, pausas, diálogo y cierre."""
    contexto = navegador.new_context(viewport={"width": 375, "height": 812})
    p = contexto.new_page()
    p.goto(base + "/", wait_until="load")
    obs = {"reproduce": _esperar(p, f"!{FONDO}.paused && {FONDO}.currentTime > 0")}
    boton = p.locator("#hero .hero-pausa")
    obs["aria_pressed"] = []
    for _ in range(2):
        boton.click()
        obs["aria_pressed"].append(boton.get_attribute("aria-pressed"))
    p.evaluate("window.scrollTo(0, document.querySelector('#hero').offsetHeight + 300)")
    obs["pausa_fuera"] = _esperar(p, f"{FONDO}.paused")
    p.evaluate("window.scrollTo(0, 0)")
    _esperar(p, f"!{FONDO}.paused")
    p.click("#ver-video")
    abierto = p.evaluate("document.querySelector('#video-dialogo').open")
    obs["pausa_dialogo"] = abierto and _esperar(p, f"{FONDO}.paused")
    obs["cerrar"] = p.eval_on_selector(".video-cerrar", BOTON_CERRAR)
    p.click(".video-cerrar")
    obs["cerrado_pausado"] = _esperar(p, f"{INSTITUCIONAL}.paused")
    contexto.close()
    return obs


def observar_sin_js_ni_movimiento(navegador, base):
    """Observaciones con movimiento reducido y con JavaScript desactivado."""
    contexto = navegador.new_context(reduced_motion="reduce")
    p = contexto.new_page()
    p.goto(base + "/", wait_until="load")
    p.wait_for_timeout(1500)
    obs = {"reducido_pausado": p.evaluate(f"{FONDO}.paused")}
    contexto.close()
    contexto = navegador.new_context(java_script_enabled=False)
    p = contexto.new_page()
    p.goto(base + "/", wait_until="load")
    obs["href_sin_js"] = p.get_attribute("#ver-video", "href") or ""
    obs["visibles_sin_js"] = p.is_visible("#hero h1") and p.is_visible(
        "#hero .btn-primario"
    )
    contexto.close()
    return obs


def medir_comportamiento(navegador, base):
    obs = {
        **observar_con_js(navegador, base),
        **observar_sin_js_ni_movimiento(navegador, base),
    }
    return evaluar_observaciones(obs)
