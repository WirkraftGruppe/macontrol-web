# Infraestructura de Railway (IaC)

`railway.ts` declara el servicio `web` de Railway (comandos de build, inicio y previo al despliegue,
réplicas, dominio y volumen) como Infrastructure as Code. Postgres queda fuera: es un recurso
gestionado desde Railway (`partial = "web"`), y las variables también (`managed: false`).

Railway no lee esta carpeta al desplegar: los cambios se aplican a mano desde esta máquina.

## Uso

```bash
npm ci --prefix .railway     # instala la CLI de IaC (railway/iac)
railway config plan          # muestra qué cambiaría, sin tocar nada
railway config apply         # aplica el plan (solo con el plan revisado)
```

`plan` debe dar `0 to destroy`; si aparece un cambio "destructive" (por ejemplo desmontar `/data`),
no se aplica: se corrige `railway.ts` primero.
