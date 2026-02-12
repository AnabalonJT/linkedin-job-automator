# n8n Orchestration Setup

## Overview
El workflow de n8n orquesta todo el proceso de automatización de LinkedIn:
1. **Scheduled Trigger** → Ejecuta cada día a las 9:00 AM
2. **Run Scraper** → `linkedin_scraper.py` busca trabajos nuevos
3. **Run Applier** → `linkedin_applier.py` postula a trabajos
4. **Sync to Google Sheets** → `google_sheets_manager.py` actualiza tracking
5. **Telegram Notification** → Notifica en Telegram cuando termina

## Architecture Flow

```
 ┌─────────────────────────────────────────────────────────────┐
 │         Daily Scheduled Trigger (09:00 AM)                  │
 │                                                               │
 │  ┌──────────────┐      ┌───────────┐      ┌──────────────┐  │
 │  │   Scraper    │  →   │ Applier   │  →   │ Google Sheets│  │
 │  │              │      │           │      │   Manager    │  │
 │  │ - LinkedIn   │      │ - LinkedIn│      │              │  │
 │  │   Search     │      │   Apply   │      │ - Update DB  │  │
 │  │ - Deduplica- │      │ - Telegram│      │ - Dashboard  │  │
 │  │   te vs Sheets      │   Notify  │      │              │  │
 │  │ - Cache Local│      │           │      │              │  │
 │  └──────────────┘      └───────────┘      └──────────────┘  │
 │                                                    │          │
 │                                                    ▼          │
 │                                           ┌──────────────┐   │
 │                                           │  Telegram    │   │
 │                                           │ Notification │   │
 │                                           │ (Final Msg)  │   │
 │                                           └──────────────┘   │
 │                                                               │
 └─────────────────────────────────────────────────────────────┘
```

## Data Flow & Deduplication

### Sesión: Cache Local
- **Entrada:** `jobs_found.json` (cache de trabajos previos)
- **Scraper:** Lee cache local, consulta Google Sheets para URLs aplicadas, filtra duplicados, guarda nuevos trabajos en `jobs_found.json`
- **Applier:** Lee `jobs_found.json` (cache), intenta postular, registra resultados
- **Google Sheets:** Lee resultados, actualiza la base de datos

```
                    Google Sheets (Fuente de Verdad)
                              ↓
                    get_all_applied_urls()
                              ↓
    jobs_found.json (Cache) + URLs aplicadas = Deduplicación
                              ↓
                         Scraper busca nuevos trabajos
                              ↓
                    Guarda en jobs_found.json (cache)
                              ↓
                    Applier usa cache local (sin más API calls)
```

## Setup Steps

### 1. Docker Compose (n8n + Selenium)

Asegúrate de que en `docker-compose.yml` esté configurado:

```yaml
version: '3'
services:
  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=your-password
    volumes:
      - ./n8n_data:/home/node/.n8n
      - .:/linkedin-job-automator  # Mount repo para acceso a scripts
    working_dir: /linkedin-job-automator
  
  selenium:
    image: selenium/standalone-chrome:latest
    ports:
      - "4444:4444"
```

### 2. Environment Variables en n8n

Configura en n8n Settings > Environment Variables:
- `GOOGLE_SHEETS_ID` → ID del spreadsheet
- `TELEGRAM_BOT_TOKEN` → Token del bot
- `TELEGRAM_CHAT_ID` → Chat ID destino
- `LINKEDIN_USERNAME` → Usuario LinkedIn
- `LINKEDIN_PASSWORD_ENCRYPTED` → Contraseña encriptada

### 3. Import Workflow

1. Ve a n8n UI: `http://localhost:5678`
2. Importa `n8n/workflows/linkedin_automation.json`
3. Reemplaza `{REPO_PATH}` con la ruta absoluta al repositorio
4. Configura las variables de entorno
5. Activa el Scheduled Trigger

### 4. Alternative: Ejecutar Scripts Directamente

Si prefieres ejecutar manualmente sin n8n:

```bash
# Scraper
python scripts/linkedin_scraper.py

# Applier
python scripts/linkedin_applier.py

# Sync Google Sheets
python scripts/google_sheets_manager.py
```

## Deduplication Strategy

### Problema Original
- Múltiples llamadas a LinkedIn API podrían buscar los mismos trabajos
- Trabajos ya aplicados podrían volver a ser postulados

### Solución Implementada
1. **Google Sheets es Fuente de Verdad:** `get_all_applied_urls()` extrae todas las URLs de la tabla "Postulaciones"
2. **Cache Local:** `jobs_found.json` almacena trabajos de la sesión actual
3. **Deduplicación Doble:**
   - URLs del cache local
   - URLs de Google Sheets (trabajos ya aplicados)
4. **Scraper:** Filtra búsquedas contra URLs combinadas, evita duplicados

### Una Llamada a API por Sesión
- Scraper hace UNA búsqueda en LinkedIn
- Google Sheets API se consulta UNA vez al inicio para obtener URLs aplicadas
- Los trabajos nuevos se usan desde `jobs_found.json` (cache) durante el applier
- Al final del ciclo, los resultados se suben a Google Sheets

## Monitoring

### Google Sheets Dashboard
La hoja "Dashboard" muestra automáticamente:
- Total de postulaciones
- Aplicadas automáticamente
- Requieren atención manual
- Tasa de automatización

### Telegram Notifications
Se envían notificaciones automáticas en:
- Éxito de postulación: ✅ `{Puesto} - {Empresa} - APPLIED`
- Fallo/Manual: ⚠️ `{Puesto} - {Empresa} - MANUAL/ERROR`
- Fin de ciclo: ✅ `LinkedIn Job Automation - Ciclo completado`

## Troubleshooting

### n8n no puede ejecutar Python scripts
- Asegúrate de que Python esté en el PATH dentro del contenedor
- Usa la ruta completa: `/usr/bin/python3` o similar

### Google Sheets conexión falla
- Verifica que la hoja esté compartida con el email del service account
- Confirma que `config/google_credentials.json` existe y es válido

### Telegram no recibe mensajes
- Verifica `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`
- Prueba manualmente: `python scripts/telegram_notifier.py`

## Next Steps

- [ ] Refinar preguntas automáticas en `respuestas_comunes.json`
- [ ] Agregar more workflows (búsqueda por múltiples keywords)
- [ ] Implementar retry logic en caso de fallo
- [ ] Analytics dashboard mejorado
