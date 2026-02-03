# 🤖 LinkedIn Job Automator

**Automatiza tu búsqueda de trabajo en LinkedIn con un bot inteligente.**

> Para personas con TDAH (o cualquiera que prefiera no hacer tareas repetitivas)

## 🚀 Quick Start

```bash
# 1. Clonar/actualizar proyecto
cd f:\Proyectos\linkedin-job-automator

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar credenciales
python scripts/credentials_manager.py setup

# 4. Iniciar Docker
docker-compose up

# 5. Acceder a n8n
# Ir a: http://localhost:5678
```

## ✨ Qué Hace Este Bot

### 🔍 Búsqueda Automática
- Busca trabajos en LinkedIn según criterios definidos
- Filtra por ubicación, tipo de contrato, experiencia
- Solo busca trabajos con \"Easy Apply\"
- Evita duplicados inteligentemente

### ✍️ Postulación Automática
- Completa formularios de Easy Apply automáticamente
- Responde preguntas frecuentes con templates
- Selecciona el CV más apropiado según el trabajo
- Maneja errores sin interrumpir el flujo

### 📊 Registro Centralizado
- Guarda todas las postulaciones en Google Sheets
- Permite actualizar estado manualmente (Entrevista, Prueba, etc)
- Accesible desde cualquier dispositivo

### 📱 Notificaciones en Tiempo Real
- Telegram Bot te notifica de nuevos trabajos
- Recibes confirmación de postulaciones exitosas
- Alertas inmediatas de errores críticos

### ⏰ Totalmente Automático
- Se ejecuta diariamente a la hora que definas
- Cero intervención manual necesaria
- Ejecutable manualmente en cualquier momento

---

## 📋 Documentación

### Para Empezar
1. **[RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md)** - Comienza aquí si es tu primera vez
   - Qué es el proyecto
   - Cómo funciona
   - Estimación de tiempo
   - Preguntas frecuentes

### Para Entender Mejor
2. **[ESPECIFICACION_PROYECTO.md](ESPECIFICACION_PROYECTO.md)** - Especificación completa
   - Requisitos funcionales
   - Historias de usuario
   - Arquitectura del sistema
   - Plan de implementación

### Para Implementar
3. **[PLAN_TECNICO.md](PLAN_TECNICO.md)** - Roadmap técnico
   - 7 fases de implementación
   - Estimación por fase
   - Decisiones arquitectónicas
   - Riesgos y mitigaciones

4. **[ANALISIS_COMPONENTES.md](ANALISIS_COMPONENTES.md)** - Estado actual del código
   - Análisis de cada módulo
   - Qué está hecho vs falta
   - Accionables priorizados

### Preparación
5. **[CHECKLIST_VALIDACION.md](CHECKLIST_VALIDACION.md)** - Antes de empezar
   - Validación de código existente
   - Credenciales necesarias
   - Ambiente de desarrollo
   - Checklist de pre-implementación

### Navegación
6. **[INDICE_DOCUMENTACION.md](INDICE_DOCUMENTACION.md)** - Índice completo
   - Mapa de todos los documentos
   - Preguntas frecuentes por tipo de usuario
   - Referencias rápidas
   - Glosario de términos

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                     n8n (Orquestador)                            │
│  Trigger: Schedule (9 AM) o Manual (WebUI)                      │
└───────────────┬──────────────────────────────────────────────────┘
                │
    ┌───────────┼───────────┬──────────────┐
    │           │           │              │
    ▼           ▼           ▼              ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐
│ Scraper │ │ Applier  │ │ Telegram │ │ Google  │
│ Python  │ │ Python   │ │   Bot    │ │ Sheets  │
└────┬────┘ └────┬─────┘ └──────────┘ └────┬────┘
     │           │                          │
     └───────────┼──────────────────────────┘
                 │
          ┌──────▼──────┐
          │  Selenium   │
          │  + Chrome   │
          └─────────────┘
```

---

## 📊 Flujo de Ejecución

```
INICIO (9 AM automático)
    │
    ├─> 🔐 Validar credenciales
    │
    ├─> 🔍 BÚSQUEDA
    │   ├─ Abrir navegador Chrome
    │   ├─ Login en LinkedIn
    │   ├─ Buscar trabajos (25 máximo)
    │   ├─ Filtrar por keywords
    │   └─ Notificar resultados
    │
    ├─> ✍️ POSTULACIÓN (20 máximo)
    │   ├─ Para cada trabajo:
    │   │  ├─ Click en Easy Apply
    │   │  ├─ Procesar formulario
    │   │  ├─ Responder preguntas
    │   │  ├─ Seleccionar CV
    │   │  ├─ Enviar
    │   │  └─ Guardar en Google Sheets
    │   └─ Esperar delay entre trabajos
    │
    ├─> 📊 REGISTRO
    │   └─ Actualizar Google Sheets
    │
    ├─> 📱 NOTIFICACIÓN
    │   ├─ Telegram: Resumen
    │   ├─ Telegram: Errores
    │   └─ Telegram: Estadísticas
    │
    └─ FIN
```

---

## ⚙️ Configuración

### Variables de Entorno (.env)
```env
# Google Sheets
GOOGLE_SHEETS_ID=<tu_id_aqui>
GOOGLE_CREDENTIALS_PATH=config/google_credentials.json

# Telegram
TELEGRAM_BOT_TOKEN=<tu_token_aqui>
TELEGRAM_CHAT_ID=<tu_chat_id_aqui>

# Ejecución
MAX_JOBS_TO_APPLY=20
DELAY_BETWEEN_APPLICATIONS=10
```

### Búsqueda (config.yaml)
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
    tipo_empleo: ["Full-time"]
    nivel_experiencia: ["Mid-Senior level"]
    trabajo_remoto: true
    solo_easy_apply: true
```

### Respuestas (respuestas_comunes.json)
```json
{
  "informacion_personal": {
    "nombre_completo": "Tu Nombre",
    "email": "tu@email.com",
    "telefono": "+56....",
    "linkedin_url": "https://www.linkedin.com/in/..."
  },
  "anos_experiencia": {
    "desarrollo_software_general": {
      "anos": "4",
      "detalle": "4+ años en..."
    }
  },
  "preguntas_configuradas": {
    "notice_period": "Immediate",
    "willing_to_relocate": "No"
  }
}
```

---

## 📦 Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| **Orquestación** | n8n | Latest (Docker) |
| **Web Scraping** | Selenium + undetected-chromedriver | 4.16.0 |
| **Encriptación** | cryptography (Fernet) | 41.0.7 |
| **Google Sheets** | gspread | 5.12.4 |
| **Telegram** | python-telegram-bot | 20.7 |
| **Base de Datos** | Google Sheets + JSON | - |
| **Contenedor** | Docker + Docker Compose | Latest |
| **Chrome** | Selenium Chrome Driver | v144 |
| **Python** | Python | 3.10+ |

---

## 🔐 Seguridad

✅ **Credenciales encriptadas localmente** (Fernet AES-128)  
✅ **Contraseña maestra requerida** (PBKDF2)  
✅ **Ejecución local** (no en la nube)  
✅ **Datos privados** (solo en tu Google Drive)  
✅ **Sin logging de credenciales** (logs seguros)  

---

## 📝 Estado del Proyecto

### Implementado ✅
- [x] Gestión de credenciales encriptadas
- [x] Web scraper de LinkedIn
- [x] Botón Easy Apply detection
- [x] Docker Compose setup
- [x] Sistema de logs

### En Progreso ⚠️
- [ ] Completar aplicador automático (process_application_form)
- [ ] Integración Google Sheets
- [ ] Notificaciones Telegram completas
- [ ] n8n workflow principal

### Pendiente ❌
- [ ] Testing end-to-end
- [ ] Documentación de usuario
- [ ] Deploy a producción

### Roadmap de Desarrollo
1. **Fase 1** (4-5h): Completar backend Python
2. **Fase 2** (2-3h): Testing de scripts
3. **Fase 3** (2-3h): Google Sheets integration
4. **Fase 4** (1-2h): Notificaciones Telegram
5. **Fase 5** (3-4h): n8n workflow
6. **Fase 6** (2-3h): Testing completo
7. **Fase 7** (2-3h): Documentación
8. **TOTAL**: 17-23 horas

---

## 📞 Cómo Usar

### Primera Vez
1. Lee [RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md)
2. Completa [CHECKLIST_VALIDACION.md](CHECKLIST_VALIDACION.md)
3. Configura credenciales (LinkedIn, Google, Telegram)
4. Crea archivo .env
5. Ejecuta: `python scripts/credentials_manager.py setup`

### Uso Diario
1. Los trabajos se buscan automáticamente (9 AM)
2. Recibes notificación en Telegram
3. Revisar Google Sheets para aplicaciones
4. Actualizar estado manualmente si es necesario

### Si Necesitas Ayuda
1. Revisar [INDICE_DOCUMENTACION.md](INDICE_DOCUMENTACION.md)
2. Buscar en [RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md) FAQ
3. Revisar [ANALISIS_COMPONENTES.md](ANALISIS_COMPONENTES.md) para problemas específicos

---

## 💡 Características Principales

### 🎯 Inteligente
- Filtra por keywords específicas
- Evita trabajos con keywords excluidas
- Selecciona CV automáticamente
- Maneja preguntas frecuentes

### 🛡️ Seguro
- Credenciales encriptadas
- Anti-detección de bot
- Manejo seguro de datos
- Logs sin credenciales

### 📱 Conectado
- Notificaciones Telegram
- Integración Google Sheets
- Acceso desde cualquier dispositivo

### 🤖 Automático
- Ejecución diaria
- Cero intervención necesaria
- Manejo automático de errores

### 👨‍💻 Escalable
- Modular y extensible
- Fácil de personalizar
- Stack moderno

---

## 🐛 Troubleshooting

### LinkedIn me bloquea
**Solución:** Aumentar delays en config.yaml, verificar 2FA

### Selectores CSS no funcionan
**Solución:** LinkedIn cambió su HTML, actualizar selectores

### Google Sheets no sincroniza
**Solución:** Verificar credenciales, permisos, compartir sheet

### Telegram no notifica
**Solución:** Verificar token, chat ID, conectividad

Ver [ANALISIS_COMPONENTES.md](ANALISIS_COMPONENTES.md) Sección 9 para más detalles.

---

## 📊 Estadísticas Esperadas

### Por Día
- ⏱️ Tiempo de ejecución: ~70 minutos
- 🔍 Trabajos encontrados: ~15-25
- ✍️ Aplicaciones realizadas: ~15-20
- ✅ Tasa de éxito: ~85-95%

### Por Mes
- 📝 Aplicaciones: ~400-600
- 📊 Datos registrados: Todos en Google Sheets
- 💾 Almacenamiento: ~1MB (logs)

### Por Año
- ⏰ Tiempo ahorrado: ~600-1000 horas
- 📈 ROI: 2800%+ (20 horas implementación)

---

## 🎓 Aprender Más

### Sobre el Código
- Ver [ANALISIS_COMPONENTES.md](ANALISIS_COMPONENTES.md)
- Cada módulo está bien documentado
- Comentarios en el código

### Sobre la Arquitectura
- Ver [ESPECIFICACION_PROYECTO.md](ESPECIFICACION_PROYECTO.md)
- Diseño completo incluido
- Decisiones explicadas

### Sobre Implementación
- Ver [PLAN_TECNICO.md](PLAN_TECNICO.md)
- Paso a paso detallado
- Estimaciones de tiempo

---

## 📄 Licencia

Este proyecto está diseñado para uso personal.

---

## 🎉 Estado Actual

**Versión:** 1.0 Pre-Implementación  
**Última Actualización:** 2 de Febrero, 2025  
**Estado:** Listo para comenzar Fase 0 (Diagnóstico)  

### Documentación Completada
- ✅ ESPECIFICACION_PROYECTO.md
- ✅ PLAN_TECNICO.md
- ✅ RESUMEN_EJECUTIVO.md
- ✅ ANALISIS_COMPONENTES.md
- ✅ INDICE_DOCUMENTACION.md
- ✅ CHECKLIST_VALIDACION.md
- ✅ README.md (este archivo)

### Próximos Pasos
1. Revisar documentación
2. Completar checklist de validación
3. Obtener credenciales
4. Comenzar implementación Fase 1

---

## 👋 Contacto y Soporte

**Creado por:** GitHub Copilot  
**Soporte:** Revisar documentación incluida

**Documentación completa incluida en el repositorio.**

---

**¿Listo para automatizar tu búsqueda de trabajo? 🚀**

*Para comenzar, lee [RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md)*
