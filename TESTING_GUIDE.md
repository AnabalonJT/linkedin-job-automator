# 🧪 Testing & Validation Guide

## 🚀 Paso 1: Levantar Docker Compose

```bash
# Navega al directorio del proyecto
cd f:\Proyectos\linkedin-job-automator

# Levanta los servicios (n8n + Selenium)
docker-compose up -d

# Verifica que los servicios estén corriendo
docker-compose ps
```

Deberías ver:
```
NAME                              STATUS
linkedin-automator-n8n           Up (healthy)
linkedin-automator-selenium      Up
```

### Acceso a los servicios

| Servicio | URL | Usuario | Contraseña |
|----------|-----|---------|-----------|
| n8n | http://localhost:5678 | admin | admin |
| Selenium Grid | http://localhost:4444 | - | - |
| Selenium VNC (debug) | localhost:7900 | - | secret |

---

## ✅ Paso 2: Validación de Credenciales

### 2.1 Verificar Google Sheets

```bash
# Activar venv
& venv\Scripts\Activate.ps1

# Probar conexión
python scripts/google_sheets_manager.py
```

Espera ver:
```
📊 Google Sheets Manager - Prueba
============================================================
✓ Autenticado con Google Sheets
✓ Hoja 'Postulaciones' encontrada
```

**Si falla:**
- Verifica que `GOOGLE_SHEETS_ID` esté en `.env`
- Confirma que el sheet está compartido con: `n8n-linkedin-bot@linkedin-automator-485522.iam.gserviceaccount.com`
- Valida que `config/google_credentials.json` existe

### 2.2 Verificar Telegram (si está configurado)

```bash
# Probar notificación
python -c "
from scripts.telegram_notifier import TelegramNotifier
notifier = TelegramNotifier()
notifier.send_message('✅ <b>Test</b> desde LinkedIn Automator')
"
```

Deberías recibir el mensaje en Telegram.

**Si falla:**
- Verifica `TELEGRAM_BOT_TOKEN` en `.env`
- Verifica `TELEGRAM_CHAT_ID` en `.env`
- Asegúrate de haber iniciado una conversación con el bot

### 2.3 Verificar LinkedIn Credentials

```bash
# Configurar/validar credenciales
python scripts/credentials_manager.py
```

Debería mostrar:
```
✓ Credenciales de LinkedIn guardadas (encriptadas)
```

---

## 🧪 Paso 3: Test Manual de Scripts

### 3.1 Test del Scraper

```bash
& venv\Scripts\Activate.ps1
python scripts/linkedin_scraper.py
```

**Qué validar:**
- ✅ Chrome se abre y hace login
- ✅ Busca trabajos en LinkedIn
- ✅ Guarda en `data/logs/jobs_found.json`
- ✅ Deduplicación contra Google Sheets (verifica logs)

**Output esperado:**
```
🚀 LinkedIn Job Scraper - Prueba
============================================================
✓ Chrome driver configurado exitosamente
✓ Login exitoso usando cookies guardadas
✓ Cargados 50 trabajos del cache local
✓ 5 trabajos ya aplicados en Google Sheets
✓ Cache local guardado: 55 trabajos totales
```

### 3.2 Test del Applier

```bash
& venv\Scripts\Activate.ps1
python scripts/linkedin_applier.py
```

**Qué validar:**
- ✅ Chrome se abre
- ✅ Intenta postular a los primeros 3 trabajos
- ✅ Envía notificaciones por Telegram
- ✅ Guarda resultados en `application_results.json`

**Output esperado:**
```
🤖 LinkedIn Job Applier - Prueba
============================================================
✓ Telegram notifier inicializado
--- Trabajo 1/3 ---
============================================================
Aplicando a: {Job Title} - {Company}
  ✓ Botón Easy Apply encontrado
  ✓ Click en Easy Apply realizado
  ... (pasos del formulario)
  ✓ Notificación enviada por Telegram
```

### 3.3 Test de Google Sheets Sync

```bash
& venv\Scripts\Activate.ps1
python scripts/google_sheets_manager.py
```

**Qué validar:**
- ✅ Lee `application_results.json`
- ✅ Actualiza tabla "Postulaciones"
- ✅ Actualiza tabla "Dashboard" con métricas
- ✅ Carga preguntas en "Preguntas_Pendientes"

**Output esperado:**
```
📊 Google Sheets Manager - Prueba
============================================================
✓ Autenticado con Google Sheets
📤 Subiendo 3 resultados a Google Sheets...
✓ Hoja 'Postulaciones' encontrada
  ✓ Agregado a Google Sheets: {Job}
...
📊 Actualizando dashboard...
✓ Dashboard actualizado: 150 postulaciones, 120 automáticas
✅ Proceso completado
```

---

## 🔄 Paso 4: Test del Workflow n8n

### 4.1 Abrir n8n

1. Ve a **http://localhost:5678**
2. Login: `admin` / `admin`
3. Click en **+ Create New Workflow** o **Import**

### 4.2 Importar Workflow

**Opción A: Importar desde JSON**
1. Ir a Workflows → Import
2. Seleccionar `n8n/workflows/linkedin_automation.json`
3. Ajustar rutas si es necesario

**Opción B: Crear manualmente**
1. Crear 5 nodos como se describe en `N8N_ORCHESTRATION.md`

### 4.3 Configurar Variables de Entorno en n8n

1. Settings → Environment Variables
2. Agregar:
   ```
   GOOGLE_SHEETS_ID = <tu-id>
   TELEGRAM_BOT_TOKEN = <tu-token>
   TELEGRAM_CHAT_ID = <tu-chat-id>
   ```

### 4.4 Test Manual del Workflow

1. Seleccionar el workflow "LinkedIn Job Automator"
2. Click en ▶️ **Test Workflow**
3. Debería ejecutar:
   - Scraper
   - Applier
   - Google Sheets Sync
   - Telegram notification

**Verifica en logs:**
```
✓ Scraper ejecutado: 5 nuevos trabajos
✓ Applier ejecutado: 3 intentos
✓ Google Sheets sincronizado
✓ Telegram notificación enviada
```

### 4.5 Activar Scheduled Trigger (Opcional)

1. Click en el nodo "Scheduled Trigger"
2. Cambiar CRON a: `0 10 * * *` (10:00 AM diario)
3. Activar workflow (toggle en la esquina superior)
4. n8n ejecutará automáticamente cada día

---

## 📊 Paso 5: Validación End-to-End

### Flujo Completo (Sin Docker)

```bash
# Terminal 1: Scraper
& venv\Scripts\Activate.ps1
python scripts/linkedin_scraper.py
# Espera a que termine (busca ~10 min)

# Terminal 2: Applier (después que scraper termina)
& venv\Scripts\Activate.ps1
python scripts/linkedin_applier.py
# Espera a que termine (~15 min)

# Terminal 3: Google Sheets Sync
& venv\Scripts\Activate.ps1
python scripts/google_sheets_manager.py
# Debería terminar en ~30 seg
```

### Flujo Completo (Con Docker n8n)

1. Levanta Docker: `docker-compose up -d`
2. Abre n8n: http://localhost:5678
3. Importa workflow
4. Click en Test Workflow
5. Espera a que termine (~25 min total)

---

## 🔍 Debugging

### Ver logs de Docker

```bash
# n8n logs
docker logs linkedin-automator-n8n -f

# Selenium logs
docker logs linkedin-automator-selenium -f

# Ambos
docker-compose logs -f
```

### Ver VNC (debug Chrome visualmente)

```bash
# Abre VNC viewer y conecta a: localhost:7900
# Contraseña: secret
# Verás Chrome ejecutándose en tiempo real
```

### Problemas Comunes

| Problema | Solución |
|----------|----------|
| "Chrome driver no encontrado" | Selenium container debe estar corriendo: `docker-compose ps` |
| "Google Sheets no conecta" | Verifica GOOGLE_SHEETS_ID en .env y permisos en el sheet |
| "Telegram no envía" | Verifica tokens en .env, prueba manualmente |
| "n8n no puede ejecutar Python" | Asegúrate de que los scripts tienen ruta absoluta o relativa correcta |
| "Timeout en Scraper" | LinkedIn puede bloquear. Aumenta delays en `linkedin_scraper.py` |

---

## ✅ Checklist de Testing

### Antes de Ejecutar

- [ ] Docker está instalado y corriendo
- [ ] `.env` tiene todas las variables
- [ ] Google Sheet está compartido con service account
- [ ] Telegram bot fue creado y configurado
- [ ] LinkedIn cookies están actualizadas
- [ ] `jobs_found.json` existe (al menos con [])

### Ejecución

- [ ] Docker compose levanta sin errores
- [ ] n8n accesible en localhost:5678
- [ ] Google Sheets test pasa
- [ ] Telegram test recibe mensaje
- [ ] Scraper busca trabajos
- [ ] Applier postula exitosamente
- [ ] Google Sheets se actualiza
- [ ] Telegram notificaciones llegan

### Post-Ejecución

- [ ] `data/logs/jobs_found.json` tiene nuevos trabajos
- [ ] `data/logs/application_results.json` tiene resultados
- [ ] Google Sheets tabla "Postulaciones" actualizada
- [ ] Google Sheets "Dashboard" muestra métricas
- [ ] Telegram recibió notificaciones

---

## 📈 Métricas Esperadas

Después de una ejecución completa:

```
Scraper:
  - Búsqueda: ~5-20 nuevos trabajos (si no hay duplicados)
  - Deduplicación: Filtra URLs existentes

Applier:
  - Intenta postular: 3+ trabajos
  - Éxito: 0-3 (depende de preguntas sin respuesta)
  - Manual: 0-3 (requieren atención)

Google Sheets:
  - Nuevas filas en "Postulaciones"
  - Dashboard actualizado
  - Preguntas sin respuesta en "Preguntas_Pendientes"

Telegram:
  - 3+ notificaciones de intentos
  - 1 notificación final de ciclo completado
```

---

## 🎯 Próximas Sesiones

Después de validar que todo funciona:

1. **Refinar Respuestas Automáticas**
   - Agregar respuestas a preguntas que causaron bloqueos
   - Mejorar matching de patrones

2. **Monitoreo en Producción**
   - Ejecutar diariamente vía n8n scheduler
   - Revisar Google Sheets Dashboard cada semana
   - Responder preguntas pendientes

3. **Optimización**
   - Ajustar delays según necesidad
   - Aumentar número de trabajos buscados
   - Agregar más keywords de búsqueda

---

## 💡 Tips

- Mantén `VNC` abierto mientras ejecutas para ver qué está haciendo
- Revisa `data/logs/debug_*.png` si hay errores
- Guarda screenshots de nuevas preguntas para agregar respuestas después
- Ejecuta primero sin Docker para entender el flujo
- Una vez validado, usa Docker para automatización
