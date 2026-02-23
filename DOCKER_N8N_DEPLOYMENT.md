# Docker & N8N - Guía de Despliegue con IA

## 🎯 Respuesta Rápida

**¿Cambiar algo en n8n?** → NO ✅  
**¿Cambiar runner.py?** → NO ✅  
El sistema ya está listo, solo reconstruir containers.

---

## 📋 Arquitectura Actual

```
N8N (Orquestador)
  ↓
HTTP Request a http://runner:5000/run/applier
  ↓
Runner Container (Flask)
  ├─ Instala requirements.txt (con openai, pdfplumber, etc)
  └─ Ejecuta: python scripts/linkedin_applier.py
    ├─ Importa: IAIntegration
    ├─ Carga: openrouter_client, cv_processor, ia_classifier
    └─ Responde preguntas con IA automáticamente
```

---

## 🚀 Comandos Exactos para Docker

### Paso 1: Detener Containers Actuales
```powershell
docker-compose down
```
**Qué hace**: Para los 3 containers (n8n, selenium, runner)

### Paso 2: Eliminar Containers Antiguos (Opcional pero recomendado)
```powershell
docker-compose down -v
```
**Qué hace**: Detiene Y elimina volúmenes (limpia datos de n8n si quieres empezar fresh)

### Paso 3: Reconstruir con Nuevas Dependencias
```powershell
docker-compose build --no-cache
```
**Qué hace**: Reconstruye la imagen del runner con:
- requirements.txt actualizado
- Nuevas dependencias: openai, pdfplumber, python-docx, requests

### Paso 4: Iniciar Containers
```powershell
docker-compose up -d
```
**Qué hace**: Inicia los 3 containers en background:
- n8n: http://localhost:5678
- selenium: http://localhost:4444
- runner: http://localhost:5000

### Paso 5: Verificar que todo esté corriendo
```powershell
docker-compose ps
```
**Esperado**:
```
NAME                              STATUS
linkedin-automator-n8n            Up (healthy)
linkedin-automator-selenium       Up
linkedin-automator-runner         Up
```

### Paso 6: Ver logs del runner (para debug)
```powershell
docker-compose logs -f runner
```
**Ctrl+C para salir**

---

## 📊 Qué Script Va en Qué Nodo N8N

Abre n8n en http://localhost:5678

### N8N Workflow: "LinkedIn Job Automator - Orquestación"

```
┌─────────────────────────────────────────────────────────────────┐
│ NODO 1: Scheduled Trigger                                       │
│ Ejecución cada día a las 9 AM                                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌─────────────────▼────────────────────────────────────────────────┐
│ NODO 2: Run Scraper (runner)                                     │
│ URL: http://runner:5000/run/scraper                             │
│ Script: linkedin_scraper.py                                     │
│ Función: Busca trabajos nuevos en LinkedIn                     │
│ Output: lista de trabajos en jobs_found.json                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌─────────────────▼────────────────────────────────────────────────┐
│ NODO 3: Run Applier (runner) ⭐ CON IA                           │
│ URL: http://runner:5000/run/applier                            │
│ Script: linkedin_applier.py (+ IA Integration)                 │
│ Función: Aplica a trabajos nuevos                              │
│ ⭐ AHORA CON IA:                                                │
│    • Clasifica trabajos (software vs engineer)                │
│    • Elige CV correcto automáticamente                         │
│    • Responde preguntas con IA (confianza >= 0.85)            │
│    • Guarda stats de automatización                            │
│ Output: results en application_results.json                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌─────────────────▼────────────────────────────────────────────────┐
│ NODO 4: Sync to Google Sheets (runner)                          │
│ URL: http://runner:5000/run/sync                               │
│ Script: google_sheets_manager.py                               │
│ Función: Sube resultados a Google Sheets                       │
│ Output: Datos en Sheets + Dashboard actualizado               │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌─────────────────▼────────────────────────────────────────────────┐
│ NODO 5: Telegram Notification                                   │
│ URL: http://runner:5000/notify/telegram                        │
│ Script: telegram_notifier.py                                   │
│ Función: Envía resumen por Telegram                            │
│ ⭐ AHORA INCLUYE:                                              │
│    • Stats de IA (% automatizado, confianza promedio)         │
│    • CVs recomendados (software: X, engineer: Y)  │
│    • Tasa de automatización vs antes                           │
│ Output: Mensaje en Telegram                                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
         [COMPLETADO]
```

---

## 🔄 Flujo Completo en N8N

**Ejemplo de ejecución diaria:**

```
9:00 AM - Triggered por scheduler
  │
  ├─► SCRAPER (linkedin_scraper.py)
  │   • Busca 50 trabajos en LinkedIn
  │   • Encuentra 10 nuevos con Easy Apply
  │   • Guarda en jobs_found.json
  │
  ├─► APPLIER (linkedin_applier.py) ⭐ CON IA
  │   Para cada uno de los 10 trabajos:
  │   • Clasifica: ¿Software o Engineer?
  │   • Recomendación: "Use CV software" (0.92 confianza)
  │   • Easy Apply click
  │   • Q1: "¿Experiencia?" 
  │     → IA responde (0.87 confianza) → AUTO-SUBMIT ✓
  │   • Q2: "¿Salario?"
  │     → IA responde (0.62 confianza) → MANUAL ⚠️
  │   • ...
  │   Resultado: 8/10 aplicaciones completadas (80% auto)
  │
  ├─► SYNC (google_sheets_manager.py)
  │   • Agrega 8 resultados a Google Sheets
  │   • Actualiza dashboard
  │
  ├─► NOTIFY (telegram_notifier.py)
  │   Mensaje → Telegram:
  │   "LinkedIn Automator:
  │    ✓ 8 aplicaciones enviadas
  │    🤖 IA Stats: 80% automatizado, confianza: 0.87/1.0"
  │
DONE ✅
```

---

## 📦 Container Runner - Qué se instala

Cuando corre `docker-compose up`, el container runner:

```bash
# 1. Instala requirements.txt
pip install -r requirements.txt --no-cache-dir

# Esto incluye:
# - selenium==4.16.0
# - requests==2.31.0 ✅
# - openai==1.3.0 ✅ NUEVO
# - pdfplumber==0.10.3 ✅ NUEVO
# - python-docx==0.8.11 ✅ NUEVO
# - ... (todas las otras)

# 2. Inicia Flask server
python scripts/runner_server.py

# 3. Server escucha en :5000
# GET  /run/scraper → Ejecuta linkedin_scraper.py
# GET  /run/applier → Ejecuta linkedin_applier.py (+ IA)
# GET  /run/sync    → Ejecuta google_sheets_manager.py
# GET  /notify/telegram → Notifica por Telegram
```

---

## ⚡ Prueba Rápida

### Opción 1: Probar desde PowerShell (sin Docker)
```powershell
cd F:\Proyectos\linkedin-job-automator
python scripts/linkedin_applier.py
```

**Qué verás**:
```
🤖 Inicializando módulos IA...
  ✓ CVs cargados: software, engineer
  ✓ Clasificador inicializado (threshold: 0.85)
✓ Módulos IA inicializados correctamente

Aplicando a: Senior Python Developer - TechCorp
  🤖 IA recomienda CV: software (conf: 0.92)
  ✓ Respondido [IA]: Experience with Python? → 7+ years
  ...
```

### Opción 2: Probar Docker
```powershell
# 1. Reconstruir
docker-compose build --no-cache

# 2. Iniciar
docker-compose up -d

# 3. Ver logs del runner
docker-compose logs -f runner

# 4. Probar endpoint
curl http://localhost:5000/run/applier

# 5. Ver respuesta
(web browser) → http://localhost:4444/downloads para ver Selenium UI
```

---

## 🛠️ Checklist Antes de Producción

- [ ] docker-compose.yml actualizado (✅ Ya está)
- [ ] requirements.txt con nuevas dependencias (✅ Ya está)
- [ ] .env con OPENROUTER_API_KEY (✅ Ya está)
- [ ] CV files en config/ directory (✅ Verificador)
- [ ] runner_server.py sin cambios (✅ No necesita)
- [ ] n8n workflow sin cambios (✅ Automático)
- [ ] Containers docker corriendo:
  ```powershell
  docker-compose ps
  # Debería mostrar 3 containers "Up"
  ```

---

## 📝 Cambios CERO Necesarios En:

| Componente | ¿Cambios? | Por qué |
|------------|-----------|--------|
| n8n workflow | ❌ No | Los endpoints siguen igual |
| runner_server.py | ❌ No | Solo llama al script |
| docker-compose.yml | ❌ No | Configuración ya activa |
| linkedin_scraper.py | ❌ No | Sigue igual |
| google_sheets_manager.py | ❌ No | Sigue igual |
| telegram_notifier.py | ❌ No | Sigue igual |
| **linkedin_applier.py** | ✅ SÍ | ✅ **Ya actualizado con IA** |

---

## 🚀 Resumen Final

```powershell
# Paso a paso para poner en producción

# 1. Detener todo
docker-compose down

# 2. Reconstruir containers con nuevas dependencias
docker-compose build --no-cache

# 3. Iniciar
docker-compose up -d

# 4. Verificar
docker-compose ps
# → Debe mostrar 3 containers "Up"

# 5. Ver logs
docker-compose logs -f runner
# → Debe mostrar que instala las nuevas dependencias openai, pdfplumber, etc

# LISTO! ✅
# Cada día a las 9 AM n8n ejecutará:
# 1. Scraper → busca trabajos
# 2. Applier (+ IA) → aplica + responde preguntas con IA
# 3. Sync → sube a Google Sheets
# 4. Notify → Telegram con stats IA
```

---

## 📞 Si Algo No Funciona

### Error: "ModuleNotFoundError: No module named 'openai'"
```powershell
# El container runner no instaló las dependencias
# Solución:
docker-compose build --no-cache  # Reconstruir
docker-compose up -d             # Reiniciar
```

### Error: "OpenRouter API Key not found"
```python
# Verificar .env tiene:
# OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx

# Si falta, actualizar .env en raíz del proyecto
```

### Error: "CV files not found"
```python
# Verificar archivos existen:
dir config\CV*.pdf

# Si falta, actualizar .env:
# CV_SOFTWARE_PATH=config\CV Software Engineer Anabalon.pdf
# CV_ENGINEER_PATH=config\CV Automatización_Data Anabalón.pdf
```

### Ver logs de ejecución:
```powershell
docker-compose logs runner           # Últimos logs
docker-compose logs -f runner        # Seguir en vivo (Ctrl+C salir)
docker-compose logs runner --tail=50 # Últimas 50 líneas
```

---

**¿Listo? Ejecuta:**
```powershell
docker-compose down && docker-compose build --no-cache && docker-compose up -d && docker-compose ps
```

**Eso es TODO.** 🚀
