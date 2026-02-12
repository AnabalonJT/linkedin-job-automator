# 🧪 Cómo Probar Todo - Paso a Paso

## 3 Opciones Rápidas

### Opción A: Test Manual (15 minutos)

**Sin Docker, solo scripts Python:**

```powershell
# 1. Abre PowerShell en el proyecto
cd f:\Proyectos\linkedin-job-automator

# 2. Activa el venv
& .\venv\Scripts\Activate.ps1

# 3. Ejecuta el scraper
python scripts/linkedin_scraper.py
# Verás Chrome abrirse, buscar trabajos, y guardar en jobs_found.json
# Espera ~10 minutos

# 4. Una vez termine, ejecuta el applier
python scripts/linkedin_applier.py
# Chrome postula a trabajos y envía notificaciones Telegram
# Espera ~10 minutos

# 5. Finalmente, sincroniza Google Sheets
python scripts/google_sheets_manager.py
# Sube resultados a Google Sheets
# Toma ~1 minuto
```

**✅ Si todo funciona:**
- Chrome se abre y hace acciones
- Google Sheets se actualiza (ve el tab "Postulaciones")
- Telegram recibe notificaciones (si configuraste)
- Terminal muestra ✓ (éxito) en todos los pasos

---

### Opción B: Test Docker + n8n (20 minutos)

**Con Docker para automatización:**

```powershell
# 1. Levanta Docker
docker-compose up -d

# Espera 30 segundos

# 2. Abre n8n
Start-Process "http://localhost:5678"

# 3. Login con admin/admin

# 4. Importa workflow
#    - Click "Workflows" → "New"
#    - Click "Import"
#    - Selecciona: n8n/workflows/linkedin_automation.json

# 5. Test el workflow
#    - Click ▶️ "Test Workflow"
#    - Espera a que termine

# 6. Ver logs
docker-compose logs linkedin-automator-n8n -f
```

**✅ Si todo funciona:**
- n8n accesible en localhost:5678
- Workflow ejecuta los 5 nodos en orden
- Ver ejecuciones completadas en Executions tab

---

### Opción C: Test Rápido Solo Validación (1 minuto)

**Verificar que todo está configurado:**

```powershell
# Activa venv
& .\venv\Scripts\Activate.ps1

# Ejecuta validación
python scripts/validate_setup.py

# Debería mostrar:
# ✅ Python 3.8+
# ✅ Virtual environment activo
# ✅ Todos los paquetes instalados
# ✅ .env con credenciales
# ✅ Google Sheets conectado
# ✅ Telegram configurado
# ✅ Todos los scripts presentes
```

**Si algo falla, arreglalo antes de hacer Opción A o B**

---

## 🎯 Test Recomendado: Opción A (Manual)

**Por qué primero:**
1. Ves exactamente qué está haciendo
2. Chrome se abre visualmente
3. Puedes debuggear si hay errores
4. Entiendes el flujo

**Instrucciones cortas:**

```powershell
cd f:\Proyectos\linkedin-job-automator
& .\venv\Scripts\Activate.ps1
python scripts/linkedin_scraper.py
python scripts/linkedin_applier.py
python scripts/google_sheets_manager.py
```

---

## 📝 Qué Esperar en Cada Paso

### Paso 1: Scraper
```
🚀 LinkedIn Job Scraper - Prueba
============================================================
✓ Chrome driver configurado exitosamente
✓ Login exitoso
✓ Buscando trabajos...
✓ Encontrados: 15 trabajos nuevos
✓ Cache local guardado: 65 trabajos totales
```

**Verifica:**
- Chrome se abre
- Ve LinkedIn login
- Ve búsqueda
- `data/logs/jobs_found.json` se actualiza

### Paso 2: Applier
```
🤖 LinkedIn Job Applier - Prueba
============================================================
✓ Telegram notifier inicializado
--- Trabajo 1/3 ---
Aplicando a: Data Engineer - NP Group
  ✓ Botón Easy Apply encontrado
  ✓ Formulario rellenado
  ✓ Aplicación completada
  ✓ Notificación enviada por Telegram
--- Trabajo 2/3 ---
...
RESUMEN: Exitosas 2/3, Fallidas 1/3
```

**Verifica:**
- Chrome postula
- Telegram recibe notificaciones
- `data/logs/application_results.json` se actualiza

### Paso 3: Google Sheets
```
📊 Google Sheets Manager - Prueba
============================================================
✓ Autenticado con Google Sheets
✓ Hoja 'Postulaciones' encontrada
  ✓ Agregado: Data Engineer - APPLIED
  ✓ Agregado: Full Stack - MANUAL
  ✓ Agregado: AI Developer - APPLIED
✓ Dashboard actualizado: 100 postulaciones
✅ Proceso completado
```

**Verifica:**
- Google Sheet tiene nuevas filas
- Dashboard muestra números actualizados
- Preguntas_Pendientes se llena si hay preguntas sin respuesta

---

## 🆘 Si Algo No Funciona

### Chrome no se abre
```
Error: "Chrome WebDriver error"
Solución: 
  - Asegúrate de tener Chrome instalado
  - O usa docker-compose up para Selenium container
```

### Google Sheets error
```
Error: "Worksheet not found"
Solución:
  - Abre tu Google Sheet
  - Asegúrate que las hojas se llamen EXACTAMENTE:
    "Postulaciones", "Dashboard", "Preguntas_Pendientes"
  - Comprueba que está compartido con el email del service account
```

### Telegram no funciona
```
Error: "TELEGRAM_BOT_TOKEN not configured"
Solución:
  - Abre .env
  - Agrega TELEGRAM_BOT_TOKEN=<tu-token>
  - Agrega TELEGRAM_CHAT_ID=<tu-chat-id>
```

### LinkedIn te bloquea
```
Error: "Timeout esperando elemento"
Solución:
  - LinkedIn puede estar bloqueando
  - Aumenta delays: Abre linkedin_scraper.py
  - Busca time.sleep(5) y cámbialo a time.sleep(10)
```

---

## 🎉 Una Vez Que Todo Funciona

**¡Felicidades! El proyecto está completamente funcional.**

### Siguiente: Refinamiento

1. Abre Google Sheets → Pestaña "Preguntas_Pendientes"
2. Nota las preguntas que causaron que se marquen como MANUAL
3. Abre `config/respuestas_comunes.json`
4. Agrega respuestas para esas preguntas
5. Ejecuta de nuevo para más automatización

### Luego: Automatización Diaria

1. Abre Docker n8n (Opción B)
2. Activa el Scheduled Trigger (click en el nodo, toggle "active")
3. Cambia CRON a: `0 09 * * *` (cada día 9 AM)
4. El workflow ejecutará automáticamente cada mañana

---

## 📞 Resumen de Archivos de Referencia

Si necesitas ayuda:

| Problema | Archivo |
|----------|---------|
| "¿Cómo hago test?" | TESTING_GUIDE.md |
| "¿Cómo configuro Telegram?" | TELEGRAM.md |
| "¿Cuál es la arquitectura?" | N8N_ORCHESTRATION.md |
| "¿Qué está completado?" | ESTADO_PROYECTO.md |
| "¿Cómo uso n8n?" | N8N_ORCHESTRATION.md |

---

**¡Ya estás listo para probar! 🚀**
