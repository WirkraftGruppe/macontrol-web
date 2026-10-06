/* Editor del plano: marcadores arrastrables (x, y en fracción 0 a 1) y alta de puntos con clic. */
(function () {
  "use strict";

  var contenedor = document.getElementById("plano-editor");
  var origen = document.getElementById("datos-plano");
  if (!contenedor || !origen || typeof L === "undefined") {
    return;
  }
  var datos = JSON.parse(origen.textContent);
  var mensaje = document.getElementById("plano-mensaje");
  var formulario = document.getElementById("plano-alta");
  var ETIQUETAS = {
    al_dia: "Al día",
    proxima: "Próxima",
    vencida: "Vencida",
    sin_revisar: "Sin revisar",
  };

  var limites = [[0, 0], [datos.alto, datos.ancho]];
  var mapa = L.map(contenedor, {
    crs: L.CRS.Simple,
    minZoom: -4,
    maxZoom: 2,
    attributionControl: false,
  });
  L.imageOverlay(datos.imagen, limites).addTo(mapa);
  mapa.fitBounds(limites);
  mapa.setMaxBounds(L.latLngBounds(limites).pad(0.25));

  function fraccion(valor) {
    return Math.min(1, Math.max(0, valor));
  }

  /* y crece hacia abajo en el plano y hacia arriba en Leaflet. */
  function aLatLng(x, y) {
    return L.latLng(datos.alto * (1 - y), datos.ancho * x);
  }

  function deLatLng(latlng) {
    return { x: fraccion(latlng.lng / datos.ancho), y: fraccion(1 - latlng.lat / datos.alto) };
  }

  function icono(estado, sinPosicion) {
    var clase = "marcador marcador-" + estado + (sinPosicion ? " marcador-sin-posicion" : "");
    return L.divIcon({ className: clase, iconSize: [22, 22] });
  }

  function avisar(texto) {
    mensaje.textContent = texto;
  }

  var marcadores = {};

  function guardar(marcador, punto) {
    var nueva = deLatLng(marcador.getLatLng());
    htmx.ajax("POST", punto.url, {
      source: contenedor,
      swap: "none",
      values: { x: nueva.x.toFixed(4), y: nueva.y.toFixed(4) },
      handler: function (elemento, respuesta) {
        if (respuesta.successful) {
          punto.x = nueva.x;
          punto.y = nueva.y;
          marcador.getElement().classList.remove("marcador-sin-posicion");
          avisar("Posición de " + punto.nombre + " guardada.");
        } else {
          marcador.setLatLng(aLatLng(punto.x === null ? 0.5 : punto.x, punto.y === null ? 0.5 : punto.y));
          avisar("No se pudo guardar la posición de " + punto.nombre + ".");
        }
      },
    });
  }

  // El nombre viene de la base de datos: el tooltip se arma con textContent.
  function textoTooltip(punto) {
    var el = document.createElement("span");
    el.textContent = punto.nombre + " · " + (ETIQUETAS[punto.estado] || "");
    return el;
  }

  datos.puntos.forEach(function (punto) {
    var sinPosicion = punto.x === null || punto.y === null;
    var marcador = L.marker(aLatLng(sinPosicion ? 0.5 : punto.x, sinPosicion ? 0.5 : punto.y), {
      draggable: true,
      icon: icono(punto.estado, sinPosicion),
      title: punto.nombre,
    }).addTo(mapa);
    marcador.bindTooltip(textoTooltip(punto));
    marcador.on("dragend", function () {
      guardar(marcador, punto);
    });
    marcadores[punto.id] = marcador;
  });

  var provisorio = null;
  mapa.on("click", function (evento) {
    if (!formulario) {
      return;
    }
    var posicion = deLatLng(evento.latlng);
    document.getElementById("plano-alta-x").value = posicion.x.toFixed(4);
    document.getElementById("plano-alta-y").value = posicion.y.toFixed(4);
    if (provisorio) {
      provisorio.setLatLng(evento.latlng);
    } else {
      provisorio = L.marker(evento.latlng, { icon: icono("sin_revisar", true) }).addTo(mapa);
    }
    formulario.hidden = false;
    document.getElementById("plano-alta-nombre").focus();
  });

  /* Contrato con apps/panel: <ul id="estado-puntos"> con un <li data-punto data-estado> por punto. */
  document.addEventListener("htmx:afterSwap", function () {
    var lista = document.getElementById("estado-puntos");
    if (!lista) {
      return;
    }
    lista.querySelectorAll("li[data-punto]").forEach(function (item) {
      var marcador = marcadores[item.dataset.punto];
      if (marcador) {
        var sinPosicion = marcador.getElement().classList.contains("marcador-sin-posicion");
        marcador.setIcon(icono(item.dataset.estado, sinPosicion));
      }
    });
  });
})();
