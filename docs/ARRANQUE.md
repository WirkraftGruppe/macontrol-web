# Cómo arrancar el repositorio

1. Ejecutar `py -3 instalar_base.py` en esta carpeta (ya hecho si está leyendo esto); después puede borrar el instalador.

2. Copiar desde TerritoryOS los hooks de Python y las skills técnicas (son genéricos; los `.sh` de este zip ya están adaptados). En PowerShell:

```powershell
$src = "C:\Users\Emanuel\Desktop\WEB\TerritoryOS"
$dst = "C:\Users\Emanuel\Desktop\WEB\MaControl"
robocopy "$src\.claude\hooks" "$dst\.claude\hooks" verificar_plan.py test_verificar_plan.py test_contexto.py test_presupuesto.py congelado.sh presupuesto.sh cambios.sh
robocopy "$src\.claude\hooks\fixtures" "$dst\.claude\hooks\fixtures" /E
foreach ($s in "django-conventions","django-expert","django-patterns","django-security","django-fullstack-developer","postgresql-table-design","python-best-practices","python-performance-optimization","test-driven-development","systematic-debugging","frontend-design","web-design-guidelines") {
  robocopy "$src\.agents\skills\$s" "$dst\.agents\skills\$s" /E
}
```
No copiar `settings.local.json` (es local de cada proyecto) ni las skills de móvil, de API o de JWT (`react-native-*`, `mobile-*`, `vercel-*`, `django-rest-framework`, `jwt-security`, `api-*`): este repositorio es solo el sitio público.

3. Entorno:
```powershell
cd $dst
git init -b main
python -m venv venv
```

4. Primer commit de la base (sin código Django todavía):
```powershell
git add -A
git commit -m "docs: base del repositorio (esquema de agentes, modelo, diseño, contenido fuente)"
```

5. Abrir Claude Code en la carpeta, entrar en modo plan y pegar el prompt de `docs/prompts/00-arranque.md`. El plan que resulte se congela con `docs(plan): esqueleto` y se ejecuta con el flujo de `CLAUDE.md`.

6. Después del esqueleto, los planes siguientes en orden sugerido: modelo de contenido (Servicio, Configuracion, ClienteDestacado) → admin con vista previa y login con límite de intentos → páginas públicas (home, servicio, empresa, contacto) → SEO y despliegue (`docs/despliegue.md`: base nueva con `migrate`, `loaddata contenido_inicial` y `createsuperuser`).
