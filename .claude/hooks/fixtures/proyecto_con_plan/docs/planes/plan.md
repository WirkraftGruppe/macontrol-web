# Plan: de juguete para test_verificar_plan.py

- **slug**: `juguete`

## Subtareas

### T1 — Tarea hecha cuyos criterios pasan

- **Depende de**: —
- **Qué hacer**: nada. Un bloque de código con comentarios no debe cortar la subtarea:

  ```bash
  # esto no es un encabezado
  ```
- **Criterios**:
  - `[cmd]` `true`
  - `[cmd-falla]` `false`
  - `[existe]` `docs/bitacora.md`
  - `[no-existe]` `docs/no-existe.md`
  - `[grep-1]` `grep -n "Plan activo" docs/bitacora.md`
  - `[grep-0]` `grep -n "TEXTO-QUE-NO-ESTA-EN-NINGUN-LADO" docs/bitacora.md`
  - `[test]` `test -e docs/planes/plan.md`

### T2 — Tarea pendiente cuyo criterio falla

- **Depende de**: T1
- **Criterios**:
  - `[cmd]` `false`

## Criterios de cierre global

- `[cmd]` `true`

## Registro de verificación

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | pendiente |
