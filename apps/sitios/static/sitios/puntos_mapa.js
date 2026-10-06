/* Mapa de puntos del sitio: un clic fija la latitud y la longitud del punto elegido. */
(function () {
  "use strict";

  var contenedor = document.getElementById("mapa-puntos");
  var origen = document.getElementById("datos-mapa");
  if (!contenedor || !origen || typeof L === "undefined") {
    return;
  }
  var datos = JSON.parse(origen.textContent);
  var selector = document.getElementById("mapa-punto");
  var mensaje = document.getElementById("mapa-mensaje");
  var ETIQUETAS = {
    al_dia: "Al día",
    proxima: "Próxima",
    vencida: "Vencida",
    sin_revisar: "Sin revisar",
  };

  var mapa = L.map(contenedor).setView([-36.1, -57.8], 8);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; colaboradores de OpenStreetMap",
    referrerPolicy: "strict-origin",
  }).addTo(mapa);

  var marcadores = {};
  var puntos = {};

  function icono(estado) {
    return L.divIcon({ className: "marcador marcador-" + estado, iconSize: [22, 22] });
  }

  function poner(punto) {
    var posicion = [punto.lat, punto.lng];
    if (marcadores[punto.id]) {
      marcadores[punto.id].setLatLng(posicion);
      return;
    }
    marcadores[punto.id] = L.marker(posicion, { icon: icono(punto.estado), title: punto.nombre })
      .bindTooltip(punto.nombre + " · " + (ETIQUETAS[punto.estado] || ""))
      .addTo(mapa);
  }

  var colocados = [];
  datos.puntos.forEach(function (punto) {
    puntos[punto.id] = punto;
    if (punto.lat !== null && punto.lng !== null) {
      poner(punto);
      colocados.push([punto.lat, punto.lng]);
    }
  });
  if (colocados.length) {
    mapa.fitBounds(colocados, { maxZoom: 17, padding: [30, 30] });
  } else if (datos.centro[0] !== null && datos.centro[1] !== null) {
    mapa.setView(datos.centro, 16);
  }

  mapa.on("click", function (evento) {
    var punto = puntos[selector.value];
    if (!punto) {
      mensaje.textContent = "Elija primero un punto.";
      return;
    }
    htmx.ajax("POST", punto.url, {
      source: contenedor,
      swap: "none",
      values: { latitud: evento.latlng.lat.toFixed(6), longitud: evento.latlng.lng.toFixed(6) },
      handler: function (elemento, respuesta) {
        if (respuesta.successful) {
          punto.lat = evento.latlng.lat;
          punto.lng = evento.latlng.lng;
          poner(punto);
          mensaje.textContent = "Ubicación de " + punto.nombre + " guardada.";
        } else {
          mensaje.textContent = "No se pudo guardar la ubicación de " + punto.nombre + ".";
        }
      },
    });
  });

  /* Contrato con apps/panel: <ul id="estado-puntos"> con un <li data-punto data-estado> por punto. */
  document.addEventListener("htmx:afterSwap", function () {
    var lista = document.getElementById("estado-puntos");
    if (!lista) {
      return;
    }
    lista.querySelectorAll("li[data-punto]").forEach(function (item) {
      var punto = puntos[item.dataset.punto];
      if (punto) {
        punto.estado = item.dataset.estado;
        if (marcadores[punto.id]) {
          marcadores[punto.id].setIcon(icono(punto.estado));
        }
      }
    });
  });
})();
