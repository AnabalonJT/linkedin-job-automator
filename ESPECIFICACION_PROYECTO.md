# 📋 ESPECIFICACIÓN DEL PROYECTO: LinkedIn Job Automator

## 1. DESCRIPCIÓN EJECUTIVA

Sistema completo de automatización para realizar postulaciones a trabajos en LinkedIn con seguimiento y notificaciones en tiempo real. El sistema está diseñado para personas con TDAH que necesitan reducir la fricción en tareas repetitivas.

**Componentes principales:**
- 🔐 **Gestión de credenciales segura** (Python + Cryptography)
- 🔍 **Web scraper de LinkedIn** (Selenium + undetected-chromedriver)
- 📝 **Aplicador automático de formularios** (Selenium)
- 🎼 **Orquestación** (n8n)
- 📊 **Base de datos de aplicaciones** (Google Sheets)
- 📱 **Notificaciones** (Telegram Bot)
- 🐳 **Containerización** (Docker + Docker Compose)

---

## 2. ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────────────────────────┐
│                     N8N (Orquestador)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Workflow Principal                                       │   │
│  │ • Trigger: Schedule diario o manual                      │   │
│  │ • Buscar trabajos → Aplicar → Registrar → Notificar    │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────┬──────────────────────────────────────────────────┘
                │
    ┌───────────┼───────────┬──────────────┐
    │           │           │              │
    ▼           ▼           ▼              ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐
│ Scraper │ │ Applier  │ │ Telegram │ │ Google  │
│ Script  │ │ Script   │ │ Bot      │ │ Sheets  │
└────┬────┘ └────┬─────┘ └──────────┘ └────┬────┘
     │           │                          │
     └───────────┼──────────────────────────┘
                 │
          ┌──────▼──────┐
          │  Selenium   │
          │  Container  │
          └─────────────┘
                 │
          ┌──────▼──────┐
          │  LinkedIn   │
          │  Website    │
          └─────────────┘
```

---

## 3. ESPECIFICACIÓN DE REQUISITOS

### 3.1 REQUISITOS FUNCIONALES

#### 3.1.1 RF-001: Gestión Segura de Credenciales
- **Descripción:** El sistema debe almacenar y gestionar credenciales de manera segura
- **Criterios de aceptación:**
  - Las credenciales se encriptan con Fernet (AES-128)
  - Se requiere contraseña maestra para acceder
  - Las credenciales no se guardan en texto plano
  - Se puede actualizar sin perder otras credenciales
  - Existe interfaz para setup inicial

- **Archivos asociados:** `scripts/credentials_manager.py`

#### 3.1.2 RF-002: Búsqueda de Trabajos en LinkedIn
- **Descripción:** Buscar ofertas de trabajo según criterios configurados
- **Criterios de aceptación:**
  - Busca por palabras clave (skill-based)
  - Filtra por ubicación
  - Filtra por fecha de publicación (últimas 24h, semana, mes)
  - Filtra por tipo de empleo (Full-time, Contract)
  - Filtra por nivel de experiencia (Entry, Associate, Mid-Senior)
  - Solo busca trabajos con Easy Apply
  - Evita duplicados
  - Extrae: título, empresa, ubicación, URL, tipo de Easy Apply
  - Registra la fecha/hora de extracción

- **Archivos asociados:** `scripts/linkedin_scraper.py`

#### 3.1.3 RF-003: Aplicación Automática a Trabajos
- **Descripción:** Completar formularios de Easy Apply automáticamente
- **Criterios de aceptación:**
  - Detecta y completa campos de texto
  - Selecciona opciones en dropdowns/radio buttons
  - Detecta preguntas de texto libre y responde con templates
  - Carga CV apropiado según keywords del trabajo
  - Maneja preguntas múltiples en secuencia
  - Registra si se aplicó exitosamente
  - Detecta si requiere intervención manual
  - Maneja errores sin crashear el proceso
  - Espera timeouts apropiados entre acciones

- **Archivos asociados:** `scripts/linkedin_applier.py`

#### 3.1.4 RF-004: Registro de Aplicaciones
- **Descripción:** Guardar todas las aplicaciones realizadas en Google Sheets
- **Criterios de aceptación:**
  - Campos: Fecha, Empresa, Puesto, URL, Ubicación, CV usado, Estado, Último update, Notas
  - Sincroniza en tiempo real con Google Sheets
  - Evita duplicados
  - Permite seguimiento manual de estado
  - Permite agregar notas personalizadas
  - Estado: PENDIENTE, APLICADO, ENTREVISTA, PRUEBA, RECHAZADO, ACEPTADO

- **Archivos asociados:** `scripts/linkedin_applier.py`, `utils.py`

#### 3.1.5 RF-005: Notificaciones por Telegram
- **Descripción:** Notificar al usuario sobre eventos importantes
- **Criterios de aceptación:**
  - Notifica cuando comienza la ejecución
  - Notifica trabajos nuevos encontrados (resumen)
  - Notifica aplicaciones exitosas
  - Notifica errores críticos
  - Notifica cuando requiere intervención manual
  - Formato: Mensajes formateados con emojis
  - Incluye resumen de estadísticas

- **Archivos asociados:** `utils.py` (función `send_telegram_notification`)

#### 3.1.6 RF-006: Orquestación con n8n
- **Descripción:** Automatizar el flujo completo de ejecución
- **Criterios de aceptación:**
  - Ejecuta scraper automáticamente
  - Ejecuta applier automáticamente
  - Ejecuta notificaciones
  - Maneja errores en cualquier paso
  - Permite triggers: Schedule (cron), Manual, Webhook
  - Registra logs de ejecución
  - Permite pausa/reanudación
  - Configurable en UI

- **Archivos asociados:** `n8n/workflows/`

---

### 3.2 REQUISITOS NO FUNCIONALES

#### RNF-001: Seguridad
- Credenciales encriptadas en reposo
- No registrar contraseñas en logs
- Usar APIs autenticadas (Google Sheets, Telegram)
- Validar inputs

#### RNF-002: Rendimiento
- Scraping: 25 trabajos en < 5 minutos
- Aplicación: 20 trabajos en < 60 minutos (con delays entre aplicaciones)
- Respuesta a notificaciones: < 5 segundos

#### RNF-003: Confiabilidad
- Reintentos automáticos en fallos
- Logs detallados de cada ejecución
- Recuperación de fallos sin perder datos
- Manejo de excepciones robusto

#### RNF-004: Escalabilidad
- Soporta múltiples palabras clave de búsqueda
- Soporta múltiples ubicaciones
- Soporta múltiples CVs
- Base de datos creciente sin degradación

#### RNF-005: Usabilidad
- Interfaz de configuración simple
- Instalación en Docker simple (un comando)
- Logs claros y descriptivos
- Manejo intuitivo de errores

---

## 4. HISTORIAS DE USUARIO

### HU-001: Como usuario con TDAH, quiero guardar mis credenciales de forma segura
**Descripción:**
Necesito guardar mis credenciales de LinkedIn de manera segura sin preocuparme de que se guarden en texto plano.

**Criterios de aceptación:**
- [ ] Puedo ejecutar un comando que me pida credenciales
- [ ] Las credenciales se guardan encriptadas localmente
- [ ] Se requiere una contraseña maestra para desbloquear
- [ ] Si pierdo las credenciales, puedo volver a configurarlas
- [ ] Las credenciales no se guardan en git ni archivos visibles

**Tareas técnicas:**
- ✅ Implementar `credentials_manager.py` (YA HECHO)
- [ ] Crear script CLI para setup
- [ ] Documentar proceso en README

**Historias relacionadas:** RF-001

---

### HU-002: Como usuario, quiero que el sistema busque automáticamente trabajos que me interesen
**Descripción:**
Defino mis criterios de búsqueda una sola vez, y el sistema busca automáticamente trabajos que coincidan, sin que tenga que navegar LinkedIn manualmente.

**Criterios de aceptación:**
- [ ] Configuro palabras clave en `config.yaml`
- [ ] Configuro ubicaciones deseadas
- [ ] El sistema busca diariamente a la hora que defino
- [ ] Recibo notificación de nuevos trabajos encontrados
- [ ] Los trabajos se guardan en un archivo/base de datos
- [ ] Se evitan duplicados

**Tareas técnicas:**
- ✅ Implementar `linkedin_scraper.py` (YA HECHO)
- [ ] Integración con n8n (trigger schedule)
- [ ] Notificación Telegram

**Historias relacionadas:** RF-002, RF-005, RF-006

---

### HU-003: Como usuario, quiero postular automáticamente a trabajos con Easy Apply
**Descripción:**
Una vez que se encuentran trabajos, quiero que el sistema complete automáticamente los formularios de Easy Apply sin que tenga que hacerlo manualmente.

**Criterios de aceptación:**
- [ ] El sistema completa campos de texto
- [ ] El sistema selecciona opciones en dropdowns
- [ ] El sistema responde preguntas abiertas con templates
- [ ] El sistema elige el CV apropiado según el trabajo
- [ ] Se aplica a máximo 20 trabajos por ejecución
- [ ] Hay delays entre aplicaciones (evitar bloqueo)
- [ ] Si hay error, intenta nuevamente (reintentos)
- [ ] Si es muy complicado, marca para revisión manual

**Tareas técnicas:**
- ⚠️ Completar `linkedin_applier.py` (EN PROGRESO)
- [ ] Mejorar detección de preguntas
- [ ] Mejorar lógica de manejo de timeouts
- [ ] Integración con Google Sheets

**Historias relacionadas:** RF-003, RF-004

---

### HU-004: Como usuario, quiero ver todas mis aplicaciones en un solo lugar
**Descripción:**
Quiero mantener un registro de todas las empresas a las que he aplicado, cuándo, y el estado actual de cada aplicación.

**Criterios de aceptación:**
- [ ] Las aplicaciones se guardan automáticamente en Google Sheets
- [ ] Puedo ver: Fecha, Empresa, Puesto, URL, CV usado, Estado
- [ ] Puedo marcar manualmente el estado (Entrevista, Prueba, Rechazado, etc)
- [ ] Puedo agregar notas por aplicación
- [ ] Puedo buscar/filtrar por empresa o puesto
- [ ] Se sincroniza automáticamente después de cada aplicación

**Tareas técnicas:**
- ✅ Estructura de datos lista
- [ ] Implementar Google Sheets API integration
- [ ] Crear sheet template con columnas necesarias
- [ ] Sincronización automática

**Historias relacionadas:** RF-004

---

### HU-005: Como usuario, quiero recibir notificaciones en tiempo real
**Descripción:**
Quiero saber qué está haciendo el bot sin tener que revisar logs. Deseo notificaciones en Telegram cuando suceden eventos importantes.

**Criterios de aceptación:**
- [ ] Recibo notificación cuando comienza una búsqueda
- [ ] Recibo notificación con resumen de trabajos encontrados
- [ ] Recibo notificación de cada aplicación exitosa
- [ ] Recibo notificación de errores críticos
- [ ] Las notificaciones son claras y concisas
- [ ] Puedo desactivar notificaciones si lo deseo

**Tareas técnicas:**
- ✅ Función base está lista
- [ ] Integración en todo el flujo
- [ ] Crear templates de mensajes
- [ ] Testing con bot real

**Historias relacionadas:** RF-005

---

### HU-006: Como usuario, quiero que todo se ejecute automáticamente sin intervención manual
**Descripción:**
Quiero una solución totalmente automática que pueda correr en mi computadora con Docker, sin que tenga que ejecutar comandos manualmente cada día.

**Criterios de aceptación:**
- [ ] El sistema se ejecuta diariamente a una hora configurada
- [ ] Se configura enteramente desde UI de n8n
- [ ] Se puede pausar/reanudar desde la UI
- [ ] Si hay error, lo maneja gracefully sin detener el sistema
- [ ] Los logs se guardan para debugging
- [ ] Se puede ejecutar manualmente en cualquier momento

**Tareas técnicas:**
- [ ] Crear workflow n8n principal
- [ ] Configurar triggers (schedule + manual)
- [ ] Implementar error handling
- [ ] Documentar configuración

**Historias relacionadas:** RF-006

---

## 5. MODELO DE DATOS

### 5.1 Estructura de Trabajo (Job)
```json
{
  "job_id": "4346887275",
  "title": "Senior Backend Developer",
  "company": "TechCorp",
  "location": "Santiago, Chile",
  "url": "https://www.linkedin.com/jobs/view/4346887275/",
  "has_easy_apply": true,
  "application_type": "AUTO",
  "scraped_at": "2025-02-02 10:30:45",
  "description": "...", // Para matching de CV
  "salary_range": "$3000-$5000",
  "job_type": "Full-time",
  "seniority_level": "Mid-Senior level"
}
```

### 5.2 Estructura de Aplicación (Application)
```json
{
  "application_id": "uuid",
  "job_id": "4346887275",
  "job_title": "Senior Backend Developer",
  "company": "TechCorp",
  "job_url": "https://www.linkedin.com/jobs/view/4346887275/",
  "location": "Santiago, Chile",
  "applied_at": "2025-02-02 11:15:30",
  "cv_used": "software",
  "application_status": "APPLIED", // APPLIED, MANUAL_REQUIRED, ERROR
  "current_status": "PENDING", // PENDING, REVIEWING, INTERVIEW, TESTS, REJECTED, ACCEPTED
  "questions_asked": ["Question 1", "Question 2"],
  "notes": "",
  "last_updated": "2025-02-02 11:15:30",
  "has_tests": false
}
```

### 5.3 Estructura de Google Sheets
**Columnas (A-J):**
| A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|
| Fecha Aplicación | Empresa | Puesto | Ubicación | URL | CV Usado | Estado Aplicación | Estado Actual | Pruebas Pendientes | Notas |
| 2025-02-02 | TechCorp | Senior Backend Developer | Santiago, Chile | [link] | software | APPLIED | PENDING | No | - |

---

## 6. PLAN DE IMPLEMENTACIÓN

### FASE 1: Validación y Setup (⏳ 2-3 horas)
**Objetivo:** Asegurar que la infraestructura existe y funciona

- [ ] Revisar y validar `credentials_manager.py` (✅ DONE)
- [ ] Revisar y validar `linkedin_scraper.py` (✅ DONE)
- [ ] Revisar y validar `linkedin_applier.py` (⚠️ REVIEW)
- [ ] Completar funciones faltantes en `utils.py`
- [ ] Configurar variables de entorno (.env)
- [ ] Crear template de respuestas en JSON
- [ ] Documentar instalación en README

### FASE 2: Google Sheets Integration (⏳ 2-3 horas)
**Objetivo:** Poder guardar aplicaciones en Google Sheets automáticamente

- [ ] Crear clase `GoogleSheetsManager`
- [ ] Implementar autenticación OAuth2
- [ ] Crear template de sheet
- [ ] Implementar lectura/escritura de datos
- [ ] Manejo de duplicados
- [ ] Testing

### FASE 3: Notificaciones Telegram (⏳ 1-2 horas)
**Objetivo:** Notificar eventos en tiempo real

- [ ] Crear clase `TelegramNotifier`
- [ ] Integrar en scraper (inicio, resultados)
- [ ] Integrar en applier (éxitos, errores)
- [ ] Crear templates de mensajes
- [ ] Testing con bot real

### FASE 4: Orquestación n8n (⏳ 2-3 horas)
**Objetivo:** Automatizar todo el flujo

- [ ] Crear workflow principal en n8n
- [ ] Configurar trigger de schedule
- [ ] Configurar llamadas a scripts
- [ ] Implementar error handling
- [ ] Logging y debugging
- [ ] Testing end-to-end

### FASE 5: Docker & Deployment (⏳ 1-2 horas)
**Objetivo:** Sistema completamente containerizado

- [ ] Validar docker-compose.yml (✅ YA EXISTE)
- [ ] Crear Dockerfile para Python scripts (si es necesario)
- [ ] Documentar instalación con Docker
- [ ] Crear script de setup inicial
- [ ] Testing en ambiente limpio

### FASE 6: Documentación & Training (⏳ 2-3 horas)
**Objetivo:** Que el usuario pueda usar y mantener el sistema

- [ ] README completo con instrucciones
- [ ] Guía de configuración inicial
- [ ] Guía de troubleshooting
- [ ] Ejemplos de workflows
- [ ] Video tutorial (opcional)

---

## 7. CONFIGURACIÓN Y SETUP

### 7.1 Estructura de .env
```env
# Google Sheets
GOOGLE_SHEETS_ID=abc123xyz...
GOOGLE_CREDENTIALS_PATH=config/google_credentials.json

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmno...
TELEGRAM_CHAT_ID=987654321

# LinkedIn (si se usa 2FA, dejar vacío)
LINKEDIN_EMAIL=user@example.com
LINKEDIN_PASSWORD=password

# Ejecución
MAX_JOBS_TO_APPLY=20
DELAY_BETWEEN_APPLICATIONS=10
RETRY_ATTEMPTS=3
```

### 7.2 Estructura de config.yaml
```yaml
busqueda:
  palabras_clave: [...] # YA CONFIGURADO
  palabras_excluidas: [...] # YA CONFIGURADO
  ubicaciones: [...] # YA CONFIGURADO
  filtros: {...} # YA CONFIGURADO

cvs:
  software:
    path: config/CV...pdf # YA CONFIGURADO
    keywords: [...]

ejecucion:
  max_aplicaciones_por_run: 20 # YA CONFIGURADO
  tiempo_limite_minutos: 60
  delay_entre_aplicaciones_segundos: 10
  reintentos_en_error: 3

schedule:
  activo: true
  expresion_cron: "0 9 * * *"  # 9 AM diario
```

---

## 8. STACK TECNOLÓGICO

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Orquestación | n8n | Latest |
| Scraping | Selenium + undetected-chromedriver | 4.16.0 |
| Encriptación | cryptography (Fernet) | 41.0.7 |
| Google Sheets | gspread | 5.12.4 |
| Telegram | python-telegram-bot | 20.7 |
| Base de datos | JSON + Google Sheets | - |
| Containerización | Docker + Docker Compose | Latest |
| Chrome | Selenium Chrome Driver | v144 |
| Python | Python | 3.10+ |

---

## 9. RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|------------|--------|-----------|
| LinkedIn detecta bot y bloquea | Media | Alto | undetected-chromedriver, delays, rotation IP |
| Formularios cambian estructura | Alta | Medio | Selectores múltiples, error handling |
| Google Sheets quota excedida | Baja | Bajo | Batch writes, throttling |
| 2FA en LinkedIn | Baja | Alto | Detección manual, pausa automática |
| Timeout en aplicaciones | Media | Bajo | Reintentos, configuración flexible |
| Pérdida de credenciales | Baja | Muy Alto | Backup local, encriptación |

---

## 10. CHECKLIST DE IMPLEMENTACIÓN

### Setup Inicial
- [ ] Variables de entorno configuradas
- [ ] Credenciales de LinkedIn guardadas
- [ ] Google Credentials JSON descargado
- [ ] Telegram Bot Token y Chat ID obtenidos
- [ ] Google Sheets creado y compartido

### Módulos
- [ ] credentials_manager.py - ✅ Funcional
- [ ] linkedin_scraper.py - ✅ Funcional
- [ ] linkedin_applier.py - ⚠️ Revisar/completar
- [ ] utils.py - ⚠️ Completar funciones faltantes
- [ ] google_sheets_manager.py - ❌ Crear
- [ ] telegram_notifier.py - ⚠️ Completar integraciones

### Integraciones
- [ ] Google Sheets API - ❌ Implementar
- [ ] Telegram Bot API - ⚠️ Integrar completamente
- [ ] n8n Workflow - ❌ Crear

### Testing
- [ ] Test de credenciales
- [ ] Test de login LinkedIn
- [ ] Test de scraping (1 búsqueda)
- [ ] Test de aplicación manual
- [ ] Test de Google Sheets
- [ ] Test de Telegram
- [ ] Test end-to-end completo

### Documentación
- [ ] README actualizado
- [ ] Guía de instalación
- [ ] Guía de configuración
- [ ] Troubleshooting guide
- [ ] API documentation (interno)

---

## 11. PRÓXIMOS PASOS

1. ✅ **HECHO:** Análisis de requisitos y especificación
2. ⏭️ **SIGUIENTE:** Revisar código existente y completar `linkedin_applier.py`
3. ⏭️ **SIGUIENTE:** Implementar Google Sheets integration
4. ⏭️ **SIGUIENTE:** Crear y testear workflow n8n
5. ⏭️ **SIGUIENTE:** Implementar notificaciones Telegram
6. ⏭️ **SIGUIENTE:** Testing completo del sistema
7. ⏭️ **SIGUIENTE:** Documentación final

---

## 12. CONTACTO Y SOPORTE

**Autor del Sistema:** GitHub Copilot  
**Fecha de Creación:** 2025-02-02  
**Última Actualización:** 2025-02-02  

---

*Especificación completada. Sistema listo para fase de implementación.*
