/* Portada del inicio: pausa del video de fondo y diálogo del video institucional.
 * Sin dependencias. Sin el script, el fondo se reproduce solo y el botón
 * "Ver video" es un enlace directo al archivo. */
(function () {
  "use strict";

  var portada = document.getElementById("hero");
  var fondo = portada && portada.querySelector(".hero-video");
  var botonPausa = portada && portada.querySelector(".hero-pausa");
  if (!fondo || !botonPausa) {
    return;
  }

  var dialogo = document.getElementById("video-dialogo");
  var enlaceVideo = document.getElementById("ver-video");
  var movimientoReducido = window.matchMedia("(prefers-reduced-motion: reduce)");

  var pausadoPorUsuario = movimientoReducido.matches;
  var enVista = true;
  var dialogoAbierto = false;

  function reproducir() {
    var promesa = fondo.play();
    if (promesa && promesa.catch) {
      promesa.catch(function () {});
    }
  }

  /* Reproduce solo si nadie lo impide: el usuario, la salida de pantalla o el diálogo. */
  function sincronizar() {
    if (!pausadoPorUsuario && enVista && !dialogoAbierto) {
      reproducir();
    } else {
      fondo.pause();
    }
  }

  function mostrarEstado() {
    botonPausa.setAttribute("aria-pressed", pausadoPorUsuario ? "true" : "false");
    botonPausa.setAttribute(
      "aria-label",
      pausadoPorUsuario ? "Reanudar el video de fondo" : "Pausar el video de fondo"
    );
  }

  /* Detiene el fondo y lo devuelve al poster. */
  function volverAlPoster() {
    fondo.pause();
    fondo.removeAttribute("autoplay");
    fondo.load();
  }

  botonPausa.hidden = false;
  mostrarEstado();
  if (pausadoPorUsuario) {
    volverAlPoster();
  }

  botonPausa.addEventListener("click", function () {
    pausadoPorUsuario = !pausadoPorUsuario;
    mostrarEstado();
    sincronizar();
  });

  movimientoReducido.addEventListener("change", function (evento) {
    pausadoPorUsuario = evento.matches;
    mostrarEstado();
    if (pausadoPorUsuario) {
      volverAlPoster();
    } else {
      sincronizar();
    }
  });

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entradas) {
      enVista = entradas[entradas.length - 1].isIntersecting;
      sincronizar();
    }).observe(portada);
  }

  if (dialogo && enlaceVideo && typeof dialogo.showModal === "function") {
    var institucional = dialogo.querySelector("video");
    var cerrar = dialogo.querySelector(".video-cerrar");

    enlaceVideo.addEventListener("click", function (evento) {
      evento.preventDefault();
      dialogoAbierto = true;
      sincronizar();
      dialogo.showModal();
      var promesa = institucional.play();
      if (promesa && promesa.catch) {
        promesa.catch(function () {});
      }
    });

    cerrar.addEventListener("click", function () {
      dialogo.close();
    });

    /* Un clic sobre el fondo oscuro cae en el propio <dialog>, no en su contenido. */
    dialogo.addEventListener("click", function (evento) {
      if (evento.target === dialogo) {
        dialogo.close();
      }
    });

    /* Se dispara al cerrar con el botón, con Escape o con el fondo. */
    dialogo.addEventListener("close", function () {
      institucional.pause();
      dialogoAbierto = false;
      sincronizar();
    });
  }
})();
