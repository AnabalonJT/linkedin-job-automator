# 🔧 ANÁLISIS DETALLADO DE COMPONENTES

## 1. MÓDULO: Gestión de Credenciales

### Archivo
`scripts/credentials_manager.py`

### Estado
**✅ 100% FUNCIONAL**

### Funcionalidades
- ✅ Encriptación Fernet (AES-128)
- ✅ Contraseña maestra con PBKDF2
- ✅ Save/Load credenciales
- ✅ CLI interactivo
- ✅ Validación de contraseña

### Cómo usar
```bash
# Setup inicial
python scripts/credentials_manager.py setup

# Probar lectura
python scripts/credentials_manager.py test

# Ver credenciales guardadas (con máscara)
python scripts/credentials_manager.py
# Opción 3

# Eliminar todo
python scripts/credentials_manager.py delete
```

### Variables de entorno necesarias
```env
# Ninguna específica para este módulo
# Usa contraseña maestra en lugar de variables
```

### Integración con otros módulos
```python
from scripts.utils import Config

config = Config()
credentials = config.get_linkedin_credentials(password="mi_contraseña_maestra")
# Retorna: {'username': '...', 'password': '...'}
```

### Notas técnicas
- Salt aleatorio de 16 bytes
- 100,000 iteraciones PBKDF2
- Base64 URL-safe encoding
- Manejo seguro de memoria (no imprime contraseñas)

---

## 2. MÓDULO: Web Scraper LinkedIn

### Archivo
`scripts/linkedin_scraper.py`

### Estado
**⚠️ 95% FUNCIONAL - REQUIERE VALIDACIÓN**

### Responsabilidades
1. **Setup Chrome Driver** - Configuración anti-detección
2. **Login LinkedIn** - Con soporte a cookies y 2FA manual
3. **Search Jobs** - Búsqueda con criterios
4. **Extract Job Data** - Parsing de tarjetas
5. **Check Easy Apply** - Verificar disponibilidad

### Flujo Típico
```python
from scripts.linkedin_scraper import LinkedInScraper
from scripts.utils import Config, Logger

config = Config()
logger = Logger()
scraper = LinkedInScraper(config, logger, headless=False)

try:
    # Setup driver
    scraper.setup_driver()
    
    # Login
    if scraper.login(email, password):
        # Search
        jobs = scraper.search_jobs(
            keywords="Senior Backend Developer",
            location="Santiago, Chile",
            num_jobs=25
        )
        
        # Procesar resultados
        for job in jobs:
            print(f"{job['title']} - {job['company']}")
finally:
    scraper.close()
```

### Datos de Salida
```json
{
  "title": "Senior Backend Developer",
  "company": "TechCorp",
  "location": "Santiago, Chile",
  "url": "https://www.linkedin.com/jobs/view/4346887275/",
  "has_easy_apply": true,
  "application_type": "AUTO",
  "scraped_at": "2025-02-02 10:30:45"
}
```

### Configuración (config.yaml)
```yaml
busqueda:
  palabras_clave:
    - "Senior Backend Developer"
    - "Full Stack Engineer"
  ubicaciones:
    - "Santiago, Chile"
    - "Providencia, Chile"
  filtros:
    fecha_publicacion: "past-week"
    tipo_empleo: ["Full-time", "Contract"]
    nivel_experiencia: ["Mid-Senior level"]
    trabajo_remoto: true
    solo_easy_apply: true
```

### ⚠️ PROBLEMAS POTENCIALES

1. **Selectores CSS pueden cambiar**
   - LinkedIn actualiza su HTML frecuentemente
   - Solución: Selectores múltiples (fallback)
   - Acción: Validar después de LinkedIn updates

2. **Detección como bot**
   - undetected-chromedriver ayuda pero no es 100% seguro
   - Solución: Delays entre clicks, random scrolling
   - Acción: Monitorear 2FA

3. **Timeout en carga**
   - A veces LinkedIn carga lento
   - Solución: Aumentar waits (actualmente 5-10s)
   - Acción: Configurar timeouts en config.yaml

### ✅ VALIDAR ANTES DE USAR

```bash
# Test de scraper
python scripts/linkedin_scraper.py

# Debe:
# 1. Pedir credenciales (o usar guardadas)
# 2. Hacer login en LinkedIn
# 3. Buscar trabajos
# 4. Mostrar 5+ trabajos encontrados
# 5. Guardar en data/logs/jobs_found.json
```

### Mejoras Necesarias
- [ ] Mejorar detección de elementos dinámicos
- [ ] Agregar extracción de salario
- [ ] Agregar extracción de descripción
- [ ] Mejorar manejo de scroll infinito
- [ ] Agregar retry automático en timeout

---

## 3. MÓDULO: Aplicador Automático

### Archivo
`scripts/linkedin_applier.py`

### Estado
**⚠️ 70% FUNCIONAL - REQUIERE COMPLETAR**

### Responsabilidades
1. **Hacer click en Easy Apply** - Detectar y clickear botón
2. **Procesar formulario** - Navegar múltiples pasos
3. **Llenar campos** - Detectar y completar inputs
4. **Responder preguntas** - Usar templates
5. **Seleccionar CV** - Elegir CV apropiado
6. **Registrar resultado** - Guardar en Google Sheets

### Flujo Típico
```python
from scripts.linkedin_applier import LinkedInApplier

applier = LinkedInApplier(driver, config, logger)

# Aplicar a un trabajo
job = {
    'url': 'https://www.linkedin.com/jobs/view/123/',
    'title': 'Senior Backend Developer',
    'company': 'TechCorp'
}

result = applier.apply_to_job(job)

# Resultado
result = {
    'job_url': '...',
    'job_title': 'Senior Backend Developer',
    'company': 'TechCorp',
    'success': True,  # O False
    'status': 'APPLIED',  # O 'MANUAL', 'ERROR'
    'error': None,  # Si hay error
    'questions_encountered': ['Pregunta 1', 'Pregunta 2'],
    'cv_used': 'software'
}
```

### ⚠️ PROBLEMAS A RESOLVER

1. **`process_application_form()` INCOMPLETA**
   - Línea 155 termina sin implementar la lógica
   - Necesita: Procesar múltiples pasos del formulario
   - Status: CRÍTICO

2. **Detección de campos**
   - Necesita detectar: text inputs, textareas, selects, radios, checkboxes
   - Actual: Básico
   - Necesita: Mejorado

3. **Respuestas a preguntas**
   - Necesita leer preguntas (text de labels)
   - Matchear con respuestas en `respuestas_comunes.json`
   - Si no hay match: marcar para revisión manual

4. **Timeouts**
   - Necesita: Esperas configurables entre pasos
   - Actual: Hardcoded
   - Mejora: Hacer configurable en config.yaml

### ✅ COMPLETAR ESTAS FUNCIONES

```python
def process_application_form(self, job, result) -> bool:
    """
    PENDIENTE: Implementar lógica completa
    
    Pseudocódigo:
    1. max_steps = 10 (evitar loops infinitos)
    2. current_step = 0
    3. while current_step < max_steps:
        a. Buscar botón "Next" o "Submit"
        b. Si encuentra "Submit": completar formulario y presionar
        c. Si encuentra "Next": completar este paso y presionar
        d. Si no encuentra nada: salir (formulario completo)
        e. Esperar delay configurado
        f. current_step += 1
    4. return True si éxito
    """
    pass
```

### Datos Necesarios para Responder Preguntas

```json
{
  "informacion_personal": {
    "nombre_completo": "José Tomás Anabalón",
    "email": "jtanabalon@miuandes.cl",
    "telefono": "+56983931281",
    "linkedin_url": "https://www.linkedin.com/in/jtanabalon/"
  },
  "anos_experiencia": {
    "desarrollo_software_general": {
      "anos": "4",
      "detalle": "4+ años de experiencia..."
    }
  },
  "preguntas_configuradas": {
    "notice_period": "Immediate",
    "willing_to_relocate": "No",
    "trabajar_remoto": "Yes, I prefer to work remotely"
  }
}
```

### Plan de Completar Este Módulo

**Paso 1: Implementar `process_application_form()`**
- Detectar pasos múltiples
- Llenar campos automáticamente
- Responder preguntas de texto
- Navegar a siguiente paso

**Paso 2: Mejorar detección de campos**
- Text inputs
- Textareas
- Dropdowns (select)
- Radio buttons
- Checkboxes
- Datepickers

**Paso 3: Integrar selección de CV**
- Leer descripción del trabajo
- Matchear con keywords de CVs
- Seleccionar CV más apropiado

**Paso 4: Manejo de errores**
- Si hay error: no crashear
- Marcar como MANUAL_REQUIRED
- Continuar con siguiente trabajo

**Paso 5: Integración con Google Sheets**
- Guardar resultado automáticamente
- Actualizar estado en Google Sheets

---

## 4. MÓDULO: Utilidades Compartidas

### Archivo
`scripts/utils.py`

### Estado
**⚠️ 80% FUNCIONAL - FUNCIONES FALTANTES**

### Clases Disponibles

#### Logger
```python
logger = Logger(log_dir="data/logs")
logger.info("Mensaje informativo")
logger.success("✓ Éxito")
logger.warning("⚠️ Advertencia")
logger.error("❌ Error")
```

#### Config
```python
config = Config(config_dir="config")
yaml_cfg = config.load_yaml_config("config.yaml")
json_cfg = config.load_json_config("respuestas_comunes.json")
creds = config.get_linkedin_credentials()
telegram = config.get_telegram_config()
sheets_id = config.get_google_sheets_id()
cv_paths = config.get_cv_paths()
```

### Funciones Disponibles

✅ `clean_text(text)` - Limpiar espacios
✅ `extract_job_id_from_url(url)` - Extraer ID de LinkedIn
✅ `should_skip_job(title, desc, config)` - Filtro por keywords
✅ `select_cv_by_keywords(job, cvs, config)` - Elegir CV
✅ `format_job_data(job_data)` - Formatear para Google Sheets
✅ `send_telegram_notification(message, config)` - Notificaciones
✅ `is_job_already_applied(url, list)` - Verificar duplicados
✅ `validate_config_files()` - Validar archivos necesarios

### Funciones FALTANTES

```python
# PENDIENTE: Google Sheets Manager
class GoogleSheetsManager:
    def __init__(self, credentials_file, sheet_id):
        pass
    
    def add_application(self, app_data):
        pass
    
    def update_status(self, job_url, status):
        pass
    
    def get_existing_applications(self):
        pass
    
    def add_note(self, job_url, note):
        pass

# PENDIENTE: Mejorar Telegram
class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        pass
    
    def notify_job_found(self, jobs_count, jobs_list):
        pass
    
    def notify_application_success(self, job_title, company):
        pass
    
    def notify_error(self, error_message):
        pass
    
    def notify_summary(self, stats):
        pass
```

### Acciones Necesarias
- [ ] Crear `GoogleSheetsManager` class completa
- [ ] Mejorar `TelegramNotifier` con múltiples métodos
- [ ] Agregar retry logic
- [ ] Agregar rate limiting
- [ ] Agregar batch operations para Google Sheets

---

## 5. ARCHIVOS DE CONFIGURACIÓN

### 5.1 config.yaml
**Estado:** ✅ COMPLETO Y FUNCIONAL

**Contenido:**
- ✅ Palabras clave de búsqueda
- ✅ Palabras a excluir
- ✅ Ubicaciones
- ✅ Filtros (fecha, tipo, experiencia)
- ✅ Configuración de CVs
- ✅ Parámetros de ejecución

**Acciones:** Ninguna, ya está listo

### 5.2 respuestas_comunes.json
**Estado:** ✅ COMPLETO PERO NECESITA REVISIÓN

**Contenido:**
- ✅ Información personal (nombre, email, teléfono)
- ✅ Años de experiencia (por skill)
- ✅ Respuestas a preguntas comunes

**Acciones necesarias:**
- [ ] Revisar y actualizar información personal
- [ ] Agregar/quitar respuestas según necesario
- [ ] Traducir a idioma del formulario si es necesario

### 5.3 .env
**Estado:** ❌ NO EXISTE

**Necesita crear con:**
```env
# Google Sheets API
GOOGLE_SHEETS_ID=your_sheet_id_here
GOOGLE_CREDENTIALS_PATH=config/google_credentials.json

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Ejecución
MAX_JOBS_TO_APPLY=20
DELAY_BETWEEN_APPLICATIONS=10
RETRY_ATTEMPTS=3
HEADLESS_MODE=true
```

### 5.4 google_credentials.json
**Estado:** ❌ NO EXISTE

**Cómo obtener:**
1. Ir a [Google Cloud Console](https://console.cloud.google.com)
2. Crear proyecto
3. Habilitar Google Sheets API
4. Crear Service Account
5. Descargar JSON
6. Guardar en `config/google_credentials.json`

---

## 6. DATOS Y ALMACENAMIENTO

### 6.1 Cookies de LinkedIn
**Ubicación:** `data/cookies/linkedin_cookies.json`

**Propósito:** Guardar sesión entre ejecuciones

**Formato:**
```json
[
  {
    "domain": ".linkedin.com",
    "name": "JSESSIONID",
    "value": "...",
    "path": "/",
    "secure": true,
    "httpOnly": true
  }
]
```

### 6.2 Trabajos Encontrados
**Ubicación:** `data/logs/jobs_found.json`

**Propósito:** Histórico de todos los trabajos encontrados

**Formato:** Array de objetos Job

### 6.3 Aplicaciones Realizadas
**Ubicación:** `data/logs/application_results.json`

**Propósito:** Histórico de intentos de aplicación (backup local)

**Formato:** Array de objetos Application

### 6.4 Google Sheets (Principal)
**Propósito:** Registro centralizado y accesible de todas las aplicaciones

**Columnas:**
| Fecha | Empresa | Puesto | Ubicación | URL | CV Usado | Estado Aplicación | Estado Actual | Pruebas | Notas |

---

## 7. INTEGRACIONES EXTERNAS

### 7.1 LinkedIn
- **Endpoint:** https://www.linkedin.com
- **Método:** Web Scraping con Selenium
- **Auth:** Username + Password
- **Seguridad:** Encriptada con Fernet

### 7.2 Google Sheets
- **API:** Google Sheets API v4
- **Auth:** Service Account JSON
- **Método:** gspread library
- **Permisos:** Read + Write

**Setup necesario:**
1. Crear Service Account
2. Compartir Google Sheet con email del Service Account
3. Guardar JSON credentials

### 7.3 Telegram
- **API:** Telegram Bot API
- **Auth:** Bot Token
- **Método:** python-telegram-bot library
- **Función:** Notificaciones en tiempo real

**Setup necesario:**
1. Crear Bot con @BotFather
2. Obtener Bot Token
3. Obtener Chat ID (enviar /start al bot, obtener en logs)

---

## 8. FLUJO COMPLETO DE EJECUCIÓN

```
┌─ n8n Trigger (Schedule 9 AM)
│
├─ INIT
│  ├─ Load config.yaml
│  ├─ Load credentials
│  └─ Send Telegram: "Iniciando búsqueda..."
│
├─ SEARCH PHASE
│  ├─ Setup Chrome driver
│  ├─ Login LinkedIn
│  ├─ Para cada palabra clave:
│  │  └─ Search jobs (25 máx)
│  ├─ Filtrar por keywords excluidas
│  ├─ Evitar duplicados (check Google Sheets)
│  └─ Send Telegram: "Encontrados X trabajos"
│
├─ APPLICATION PHASE
│  ├─ Para cada trabajo (máximo 20):
│  │  ├─ Navegaren a job URL
│  │  ├─ Hacer click en Easy Apply
│  │  ├─ Procesar formulario multi-paso
│  │  ├─ Responder preguntas
│  │  ├─ Cargar CV apropiado
│  │  ├─ Enviar aplicación
│  │  ├─ Guardar resultado en Google Sheets
│  │  ├─ Send Telegram: "Aplicación exitosa"
│  │  └─ Esperar delay (10 segundos)
│  │
│  └─ Si hay error en algún trabajo:
│     ├─ Registrar error
│     ├─ Marcar como MANUAL_REQUIRED
│     └─ Continuar con siguiente
│
├─ FINALIZATION
│  ├─ Calcular estadísticas
│  ├─ Guardar logs
│  └─ Send Telegram: Resumen completo
│
└─ END
   └─ Chrome driver close
```

---

## 9. PUNTOS CRÍTICOS DE VALIDACIÓN

### Antes de Producción
- [ ] ✅ Credentials manager funciona
- [ ] ⚠️ Scraper encuentra trabajos reales
- [ ] ⚠️ Applier completa formularios
- [ ] ❌ Google Sheets sincroniza
- [ ] ❌ Telegram notifica
- [ ] ❌ n8n orquesta sin errores
- [ ] ❌ End-to-end test completo

### Monitoreo Ongoing
- [ ] Logs se guardan correctamente
- [ ] No hay pérdida de datos
- [ ] LinkedIn no bloquea el bot
- [ ] Google Sheets no excede quota
- [ ] Telegram notificaciones llegan

---

## 10. Resumen de Accionables

### COMPLETAR (CRÍTICO)
- [ ] Implementar `process_application_form()` en linkedin_applier.py
- [ ] Crear `GoogleSheetsManager` en utils.py
- [ ] Crear archivo `.env` con credenciales
- [ ] Crear workflow n8n

### MEJORAR (IMPORTANTE)
- [ ] Validar selectores CSS de LinkedIn
- [ ] Mejorar detección de campos del formulario
- [ ] Mejorar error handling en applier
- [ ] Integrar Google Sheets en applier

### DOCUMENTAR (IMPORTANTE)
- [ ] README completo
- [ ] Setup guide
- [ ] User guide
- [ ] Troubleshooting

### TESTEAR (CRÍTICO)
- [ ] Cada módulo independientemente
- [ ] Flujo completo end-to-end
- [ ] Casos límite y errores

---

*Análisis detallado completado*  
*Próximo paso: Comenzar implementación Fase 0*
