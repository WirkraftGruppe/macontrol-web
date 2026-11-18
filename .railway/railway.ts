import { defineRailway, github, project, service, volume } from "railway/iac";

// Declaración del servicio "web" de Railway (Infrastructure as Code).
// Esta carpeta no la lee Railway al desplegar: se aplica a mano con `railway config apply`.

// partial "web": este repositorio gestiona solo sus propios recursos del entorno (Postgres queda fuera).
export const partial = "web";

export default defineRailway(() => {
  // El volumen lleva región y tamaño explícitos: sin ellos el plan los deja en null
  // y propone cambiar el volumen existente. Declararlo evita que el plan desmonte "/data" (destructivo).
  const media = volume("web-media", { region: "us-east4-eqdc4a", sizeMB: 50000 });

  const web = service("web", {
    source: github("WirkraftGruppe/macontrol-web", { branch: "main", checkSuites: false }),
    build: { buildCommand: "python manage.py collectstatic --noinput", buildEnvironment: "V3", builder: "RAILPACK" },
    start: "gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --worker-class gthread --threads 8 --timeout 60",
    // Un solo comando previo: migra la base y crea la tabla de caché.
    preDeploy: "python manage.py migrate --noinput && python manage.py createcachetable",
    replicas: { "us-east4-eqdc4a": 1 },
    domains: ["www.macontrol.com.ar"],
    // Los archivos subidos (media) viven en el volumen montado en /data.
    volumeMounts: { "/data": media },
  });

  return project("macontrol-web", {
    // Las variables se administran en Railway, no desde este archivo.
    variables: { managed: false },
    resources: [media, web],
  });
});
