# Estructura de Datos - Campo `is_new`

## Implementación

Se agregó un campo `is_new` a cada trabajo en `jobs_found.json` para optimizar el flujo de trabajo:

### Estructura del JSON

```json
{
  "title": "Software Engineer",
  "company": "Tech Corp",
  "url": "https://linkedin.com/jobs/view/123456",
  "location": "Remote",
  "has_easy_apply": true,
  "posted_date": "2025-02-03",
  "source": "linkedin",
  "description": "We are looking for...",
  "is_new": true
}
```

## Campos

- **`is_new`**: `boolean` (nuevo campo)
  - `true`: Trabajo encontrado en LinkedIn que aún no ha sido procesado
  - `false`: Trabajo que ya existe en Google Sheets (no procesar de nuevo)

## Flujo de Trabajo

### 1. Scraper (linkedin_scraper.py)

```
┌─────────────────────────────────┐
│ 1. Cargar Google Sheets         │
│    → Marcar todos con          │
│    → is_new = false            │
└──────────────┬──────────────────┘
               │
               ↓
┌─────────────────────────────────┐
│ 2. Buscar en LinkedIn            │
│    → Encontrar nuevos           │
│    → Marcar con                 │
│    → is_new = true              │
└──────────────┬──────────────────┘
               │
               ↓
┌─────────────────────────────────┐
│ 3. Guardar en jobs_found.json   │
│    → [25 del Sheets + 10 nuevos]│
│    → Total: 35 trabajos         │
│    → 25 con is_new: false       │
│    → 10 con is_new: true        │
└─────────────────────────────────┘
```

### 2. Applier (linkedin_applier.py)

```
┌──────────────────────────────────┐
│ Cargar jobs_found.json           │
│ ↓                                │
│ Filtrar SOLO is_new: true        │
│ ↓                                │
│ Procesar solo los nuevos         │
│ ↓                                │
│ Agregar a Google Sheets          │
└──────────────────────────────────┘
```

### 3. Google Sheets

El campo `is_new` **NO** se agrega a Google Sheets porque:
- No está en la lista de headers de `add_job_application()`
- La función `.get()` en Google Sheets solo toma los campos especificados
- El sheet mantiene limpio sin datos internos

## Ventajas

✅ **Eficiencia**: Un archivo JSON (`jobs_found.json`) en lugar de dos (`jobs_found.json` + `new_jobs_to_apply.json`)

✅ **Claridad**: Campo explícito que marca si un trabajo es nuevo

✅ **Reinicio automático**: Al reexecutar el scraper:
- Se reemplaza `jobs_found.json` completamente
- Los trabajos del Sheets actual se marcan como `is_new: false`
- Solo los nuevos encontrados tienen `is_new: true`
- No hay "trabajos viejos" que "reactivarse"

✅ **Sin duplicados**: El sistema es idempotente
- Si ejecutas applier dos veces, solo postula a `is_new: true`
- Los trabajos ya agregados siguen con `is_new: true` hasta la próxima ejecución del scraper

## Ciclo Completo (por día)

```
09:00 AM → Scraper
  • Carga Google Sheets (0 nuevos hoy)
  • Busca en LinkedIn (25 nuevos)
  • Guarda jobs_found.json: 25 nuevos (is_new: true)

09:05 AM → Applier
  • Lee jobs_found.json
  • Filtra is_new: true (25 trabajos)
  • Postula a 25
  • Agrega a Google Sheets

09:25 AM → Sync
  • Verifica Dashboard existe
  • Las fórmulas se actualizan solas

09:26 AM → Telegram
  • Notificación única con estadísticas
  • Muestra: 25 encontrados, 25 intentos, etc.

MAÑANA 09:00 AM → Scraper nuevamente
  • Carga Google Sheets (ahora 25 trabajos)
  • Esos 25 se marcan: is_new: false
  • Busca en LinkedIn (30 nuevos)
  • Guarda jobs_found.json: 55 totales (25 old + 30 new)
  
  ✓ Sin duplicados
  ✓ Solo postula a los 30 nuevos
```
