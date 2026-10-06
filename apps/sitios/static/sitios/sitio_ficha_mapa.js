/* Mapa de solo lectura de la ficha del sitio: un marcador en la ubicación del sitio. */
(function () {
  "use strict";

  var contenedor = document.getElementById("mapa-sitio");
  var origen = document.getElementById("datos-mapa");
  if (!contenedor || !origen || typeof L === "undefined") {
    return;
  }
  var sitio = JSON.parse(origen.textContent).sitio;
  if (sitio.lat === null || sitio.lng === null) {
    return;
  }

  var mapa = L.map(contenedor).setView([sitio.lat, sitio.lng], 16);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; colaboradores de OpenStreetMap",
    referrerPolicy: "strict-origin-when-cross-origin",
  }).addTo(mapa);
  // El nombre viene de la base de datos: el tooltip usa textContent.
  var nombre = document.createElement("span");
  nombre.textContent = sitio.nombre;
  L.marker([sitio.lat, sitio.lng]).addTo(mapa).bindTooltip(nombre);
})();
