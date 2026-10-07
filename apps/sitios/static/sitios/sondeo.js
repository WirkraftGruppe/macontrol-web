/* Pausa el sondeo HTMX cuando la pestaña está oculta (decisión 10 del plan).
   Los filtros de hx-trigger necesitan eval y la CSP lo impide; por eso se cancela acá. */
(function () {
  "use strict";

  document.addEventListener("htmx:beforeRequest", function (evento) {
    var origen = evento.detail && evento.detail.elt;
    if (document.hidden && origen && origen.hasAttribute("data-sondeo")) {
      evento.preventDefault();
    }
  });
})();
