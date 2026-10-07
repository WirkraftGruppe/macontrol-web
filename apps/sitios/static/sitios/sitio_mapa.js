/* Mapa clicable y buscador de direcciones del formulario de sitio. */
(function () {
  "use strict";

  var seccion = document.getElementById("sitio-ubicacion");
  if (!seccion || typeof L === "undefined") {
    return;
  }
  var campoLat = document.getElementById(seccion.dataset.campoLat);
  var campoLng = document.getElementById(seccion.dataset.campoLng);
  if (!campoLat || !campoLng) {
    return;
  }
  seccion.hidden = false;

  var entrada = document.getElementById("sitio-buscar");
  var boton = document.getElementById("sitio-buscar-boton");
  var mensaje = document.getElementById("sitio-mensaje");
  var lista = document.getElementById("sitio-resultados");

  var mapa = L.map("sitio-mapa").setView([-36.1, -57.8], 8);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; colaboradores de OpenStreetMap",
    referrerPolicy: "strict-origin-when-cross-origin",
  }).addTo(mapa);
  var marcador = null;

  function poner(lat, lng) {
    if (marcador) {
      marcador.setLatLng([lat, lng]);
    } else {
      marcador = L.marker([lat, lng]).addTo(mapa);
    }
  }

  function fijar(lat, lng, acercar) {
    poner(lat, lng);
    campoLat.value = lat.toFixed(6);
    campoLng.value = lng.toFixed(6);
    if (acercar) {
      mapa.setView([lat, lng], 16);
    }
  }

  function desdeCampos() {
    var lat = parseFloat(campoLat.value.replace(",", "."));
    var lng = parseFloat(campoLng.value.replace(",", "."));
    if (isFinite(lat) && isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
      poner(lat, lng);
      mapa.setView([lat, lng], 16);
    }
  }
  desdeCampos();
  campoLat.addEventListener("change", desdeCampos);
  campoLng.addEventListener("change", desdeCampos);

  mapa.on("click", function (evento) {
    fijar(evento.latlng.lat, evento.latlng.lng, false);
  });

  function valorDe(id) {
    var campo = document.getElementById(id);
    return campo ? campo.value.trim() : "";
  }

  entrada.value = [valorDe(seccion.dataset.campoDireccion), valorDe(seccion.dataset.campoLocalidad)]
    .filter(Boolean)
    .join(", ");

  function mostrarResultados(resultados) {
    lista.textContent = "";
    if (!resultados.length) {
      mensaje.textContent = "Sin resultados; pruebe con otra dirección o haga clic en el mapa.";
      return;
    }
    mensaje.textContent = "Elija una ubicación:";
    resultados.forEach(function (candidato) {
      var item = document.createElement("li");
      var opcion = document.createElement("button");
      opcion.type = "button";
      opcion.textContent = candidato.nombre;
      opcion.addEventListener("click", function () {
        fijar(candidato.lat, candidato.lng, true);
      });
      item.appendChild(opcion);
      lista.appendChild(item);
    });
  }

  function buscar() {
    var consulta = entrada.value.trim();
    if (!consulta) {
      mensaje.textContent = "Escriba una dirección para buscar.";
      return;
    }
    lista.textContent = "";
    mensaje.textContent = "Buscando…";
    fetch(seccion.dataset.urlBuscar, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": seccion.dataset.csrf,
      },
      body: "q=" + encodeURIComponent(consulta),
      credentials: "same-origin",
    })
      .then(function (respuesta) {
        return respuesta.json().then(function (datos) {
          if (!respuesta.ok) {
            throw new Error(datos.error);
          }
          return datos;
        });
      })
      .then(function (datos) {
        mostrarResultados(datos.resultados);
      })
      .catch(function (error) {
        mensaje.textContent =
          error.message ||
          "No se pudo consultar la ubicación; cárguela a mano en el mapa o en los campos.";
      });
  }

  boton.addEventListener("click", buscar);
  entrada.addEventListener("keydown", function (evento) {
    if (evento.key === "Enter") {
      evento.preventDefault();
      buscar();
    }
  });
})();
