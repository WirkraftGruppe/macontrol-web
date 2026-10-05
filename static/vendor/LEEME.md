# Librerías de terceros vendorizadas

Archivos de distribución copiados sin modificar desde los tarballs oficiales de npm.
Integridad: `cd static/vendor && sha256sum -c SHA256SUMS`.

| Paquete | Versión | Tarball | Fecha |
|---|---|---|---|
| htmx.org | 2.0.11 | https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.11.tgz | 2026-10-04 |
| leaflet | 1.9.4 | https://registry.npmjs.org/leaflet/-/leaflet-1.9.4.tgz | 2026-10-04 |

Archivos: `htmx/htmx.min.js` (de `package/dist/`), `leaflet/leaflet.js`, `leaflet/leaflet.css` y `leaflet/images/*` (de `package/dist/`).

`.gitattributes` fija `* -text` para que git no convierta finales de línea y los hashes coincidan.
