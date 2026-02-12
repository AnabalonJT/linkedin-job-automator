# ⚡ Quick Test Summary

## 🎯 Lo Que Necesitas Hacer Ahora

### Opción 1: Test Rápido (10 minutos)

```powershell
# 1. Abrir PowerShell en el proyecto
cd f:\Proyectos\linkedin-job-automator

# 2. Ejecutar validación
& .\quickstart.ps1

# 3. Seleccionar opción 1 (Scraper) para test
```

**Esperarás:**
- Chrome se abre automáticamente
- Busca trabajos en LinkedIn
- Guarda en `data/logs/jobs_found.json`
- ✅ Si ves "✓ Cache local guardado" = TODO OK

---

### Opción 2: Test Completo (25 minutos)

```powershell
# 1. Activar venv
& .\venv\Scripts\Activate.ps1

# 2. Ejecutar todo en orden
python scripts/linkedin_scraper.py      # ~10 min
python scripts/linkedin_applier.py      # ~10 min
python scripts/google_sheets_manager.py # ~1 min
```

**Qué validar:**
- ✅ Scraper busca nuevos trabajos
- ✅ Applier intenta postular
- ✅ Google Sheets se actualiza
- ✅ Telegram envía notificaciones (si configurado)

---

### Opción 3: Docker + n8n (30 minutos)

```powershell
# 1. Levantar Docker
docker-compose up -d

# 2. Esperar 30 segundos
Start-Sleep -Seconds 30

# 3. Abrir n8n
Start-Process "http://localhost:5678"

# 4. Login (admin/admin)
# 5. Importar workflow: n8n/workflows/linkedin_automation.json
# 6. Click en "Test Workflow"
```

**Qué validar:**
- ✅ n8n accesible en localhost:5678
- ✅ Workflow importa sin errores
- ✅ Los 5 nodos se ejecutan en orden
- ✅ Ver logs que todo funcionó

---

## 🔑 Puntos Clave de Validación

### Antes de Ejecutar
```powershell
# Verifica que tengas:
- [ ] .env con GOOGLE_SHEETS_ID (obligatorio)
- [ ] config/google_credentials.json (obligatorio)
- [ ] .env con TELEGRAM_* (opcional pero recomendado)
- [ ] Python 3.8+ en virtual environment
- [ ] Todos los paquetes en requirements.txt
```

### Durante la Ejecución
```
Scraper: Busca trabajos y evita duplicados
  ✅ "✓ Cache local guardado: X trabajos"
  
Applier: Postula a trabajos
  ✅ "✓ Notificación enviada por Telegram"
  
Google Sheets: Sincroniza resultados
  ✅ "✓ Dashboard actualizado"
```

### Después de Ejecutar
```
Revisa:
  ✅ data/logs/jobs_found.json (cache con trabajos)
  ✅ data/logs/application_results.json (resultados)
  ✅ Google Sheets tabla "Postulaciones" (nuevas filas)
  ✅ Google Sheets "Dashboard" (métricas actualizadas)
  ✅ Telegram (notificaciones recibidas)
```

---

## 🚨 Si Algo Falla

### Google Sheets Error
```
Error: "A sheet with the name 'Postulaciones' already exists"
Solución: Los nombres de hojas tienen mayúsculas/minúsculas diferentes
  → Abre el Google Sheet y asegúrate que se llamen exactamente:
     - "Postulaciones"
     - "Dashboard"
     - "Preguntas_Pendientes"
```

### Telegram Error
```
Error: "TELEGRAM_BOT_TOKEN not configured"
Solución: Agrega a .env:
  TELEGRAM_BOT_TOKEN=<tu-token>
  TELEGRAM_CHAT_ID=<tu-id>
```

### LinkedIn Timeout
```
Error: "Timeout esperando elemento"
Solución: Aumenta delays en linkedin_scraper.py:
  time.sleep(5) → time.sleep(10)
  LinkedIn puede estar bloqueando por muchas requests
```

### Chrome Driver Error
```
Error: "Selenium cannot connect to Chrome"
Solución 1: Asegúrate que Selenium está corriendo en Docker
  docker-compose ps
  
Solución 2: Ejecuta sin Docker
  Usa undetected_chromedriver del proyecto
```

---

## 📊 Expected Output Examples

### Scraper Success
```
🚀 LinkedIn Job Scraper - Prueba
============================================================
✓ Chrome driver configurado exitosamente
✓ Login exitoso usando cookies guardadas
✓ Cargados 50 trabajos del cache local
✓ 5 trabajos ya aplicados en Google Sheets
✓ Cache local guardado: 55 trabajos totales
```

### Applier Success
```
🤖 LinkedIn Job Applier - Prueba
--- Trabajo 1/3 ---
Aplicando a: Data Engineer - NP Group
  ✓ Botón Easy Apply encontrado
  ✓ CV subido: software
  ✓ Notificación enviada por Telegram
```

### Google Sheets Success
```
📊 Google Sheets Manager - Prueba
✓ Autenticado con Google Sheets
✓ Hoja 'Postulaciones' encontrada
  ✓ Agregado: Data Engineer - APPLIED
✓ Dashboard actualizado: 100 postulaciones, 80 automáticas
✅ Proceso completado
```

---

## ✅ Checklist Final

Antes de considerar el proyecto "listo":

- [ ] Todos los scripts se ejecutan sin errores
- [ ] Google Sheets se actualiza con nuevos datos
- [ ] Telegram recibe notificaciones
- [ ] Docker levanta sin problemas
- [ ] n8n workflow importa y ejecuta
- [ ] Scheduler de n8n puede activarse (opcional)

---

## 🎉 Una Vez Que Todo Funciona

### Próximas Sesiones

1. **Refinar Respuestas Automáticas**
   - Ejecutar scraper+applier
   - Revisar "Preguntas_Pendientes" en Google Sheets
   - Agregar nuevas respuestas a `respuestas_comunes.json`
   - Re-ejecutar para más automatización

2. **Automatización Diaria (n8n)**
   - Activar scheduler en workflow (09:00 AM)
   - Monitorear ejecuciones en logs
   - Revisar Dashboard cada semana

3. **Optimización**
   - Aumentar número de trabajos buscados
   - Agregar más keywords
   - Mejorar matching de CVs

---

## 💬 Quick Reference

| Comando | Qué hace | Tiempo |
|---------|----------|--------|
| `.\quickstart.ps1` | Menú interactivo | 1 min |
| `python scripts/linkedin_scraper.py` | Busca trabajos | ~10 min |
| `python scripts/linkedin_applier.py` | Postula | ~10 min |
| `python scripts/google_sheets_manager.py` | Sincroniza Sheets | ~1 min |
| `docker-compose up -d` | Levanta n8n | ~30 seg |
| `docker-compose ps` | Ver estado servicios | 1 seg |
| `docker-compose logs -f` | Ver logs en tiempo real | Continuo |

---

**¡Listo para comenzar! 🚀**
