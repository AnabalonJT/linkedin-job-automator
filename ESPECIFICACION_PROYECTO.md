🎯 Diseño de la Solución: LinkedIn Job Application Automator
Arquitectura General
┌─────────────────────────────────────────────────────────────┐
│                    COMPONENTE PRINCIPAL                      │
│                         (n8n local)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Módulo 1   │───▶│   Módulo 2   │───▶│   Módulo 3   │ │
│  │  Búsqueda y  │    │ Postulación  │    │ Seguimiento  │ │
│  │   Filtrado   │    │  Automática  │    │ y Reporting  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                    │         │
└─────────┼────────────────────┼────────────────────┼─────────┘
          │                    │                    │
          ▼                    ▼                    ▼
   ┌─────────────┐      ┌─────────────┐    ┌─────────────┐
   │  LinkedIn   │      │ Selenium/   │    │  Google     │
   │   Scraper   │      │ Puppeteer   │    │  Sheets     │
   └─────────────┘      └─────────────┘    └─────────────┘
Stack Tecnológico Propuesto

n8n (local con Docker) - Orquestador principal
Selenium  - Automatización del navegador
Google Sheets - Base de datos (gratuito, más flexible que Notion para esto)
ChromeDriver - Driver para Selenium
Python scripts - Scripts auxiliares que n8n ejecutará

¿Por qué Google Sheets en vez de Notion?

API más simple y con mayor límite gratuito
Mejor integración nativa con n8n
Más fácil para análisis y filtros
El cliente puede verlo desde cualquier dispositivo sin instalar nada


📋 Historias de Usuario
Epic 1: Búsqueda y Filtrado de Ofertas
HU-1.1: Búsqueda automática de ofertas

Como usuario, quiero que el sistema busque automáticamente ofertas de trabajo en LinkedIn que coincidan con mis criterios (ubicación: Región Metropolitana zona oriente, roles: Software Engineer, Consultor, Data Analyst, Automatización) para no tener que buscar manualmente.

Criterios de aceptación:

El sistema busca en LinkedIn con los filtros especificados
Guarda las URLs de las ofertas encontradas
Identifica si la oferta tiene "Easy Apply"
Evita ofertas duplicadas ya procesadas

HU-1.2: Clasificación de ofertas

Como usuario, quiero que el sistema clasifique las ofertas entre "Easy Apply" y "Aplicación Externa" para saber cuáles se pueden automatizar completamente.

Criterios de aceptación:

Marca ofertas con Easy Apply como "AUTO"
Marca otras ofertas como "MANUAL"
Guarda el tipo en la hoja de cálculo


Epic 2: Postulación Automática
HU-2.1: Postulación automática Easy Apply

Como usuario, quiero que el sistema postule automáticamente a ofertas con Easy Apply usando mi información pre-configurada para ahorrar tiempo.

Criterios de aceptación:

Abre la oferta en LinkedIn
Completa formulario Easy Apply automáticamente
Selecciona el CV apropiado según el tipo de trabajo
Pre-llena respuestas comunes guardadas
Confirma el envío de la postulación

HU-2.2: Manejo de preguntas nuevas

Como usuario, quiero que el sistema me notifique cuando encuentra preguntas que no puede responder automáticamente para poder configurarlas después.

Criterios de aceptación:

Detecta preguntas no configuradas
Guarda la pregunta en un log
Marca la postulación como "PENDIENTE_MANUAL"
No envía la aplicación hasta tener la respuesta

HU-2.3: Selección inteligente de CV

Como usuario, quiero que el sistema seleccione el CV correcto (Software o Consultoría/Data) basándose en las palabras clave del trabajo.

Criterios de aceptación:

Analiza el título y descripción del trabajo
Identifica keywords: "software engineer", "developer" → CV Software
Identifica keywords: "consultor", "data analyst", "analytics" → CV Consultoría
Sube el CV correspondiente


Epic 3: Seguimiento y Gestión
HU-3.1: Registro de postulaciones

Como usuario, quiero que todas mis postulaciones se registren en una hoja de cálculo con su información relevante para llevar un control.

Criterios de aceptación:

Guarda: Fecha, Empresa, Puesto, URL, Estado, Tipo de CV usado
Actualiza estado en tiempo real
Permite filtrar por estado

HU-3.2: Actualización de estados

Como usuario, quiero que el sistema revise periódicamente el estado de mis postulaciones en LinkedIn para saber si me respondieron.

Criterios de aceptación:

Verifica estado en LinkedIn ("En revisión", "Rechazado", "Entrevista")
Actualiza automáticamente la hoja de cálculo
Detecta nuevos mensajes del reclutador

HU-3.3: Dashboard de seguimiento

Como usuario, quiero ver un resumen de mis postulaciones (total aplicadas, pendientes, rechazadas, entrevistas) para tener una visión general.

Criterios de aceptación:

Crea una pestaña "Dashboard" en Google Sheets
Muestra métricas clave con fórmulas
Se actualiza automáticamente

HU-3.4: Notificaciones locales

Como usuario, quiero recibir un resumen cuando termine cada ejecución del bot para saber qué pasó sin revisar logs técnicos.

Criterios de aceptación:

Notificación en n8n UI al terminar
Resumen: X ofertas encontradas, Y postulaciones enviadas, Z errores
Opcionalmente: archivo log.txt en carpeta local


Epic 4: Configuración y Mantenimiento
HU-4.1: Configuración inicial simple

Como usuario con TDAH, quiero que la configuración inicial sea clara y paso a paso para no sentirme abrumado.

Criterios de aceptación:

README con pasos numerados claros
Script de setup que valida cada paso
Archivo de configuración en formato simple (JSON o YAML)

HU-4.2: Biblioteca de respuestas

Como usuario, quiero poder agregar y editar fácilmente las respuestas a preguntas comunes de LinkedIn.

Criterios de aceptación:

Archivo respuestas.json editable
Ejemplos de preguntas típicas pre-configuradas
Validación de formato al cargar

HU-4.3: Programación flexible

Como usuario, quiero poder ejecutar el bot manualmente o programarlo para que corra automáticamente en horarios que yo defina.

Criterios de aceptación:

Botón "Ejecutar ahora" en n8n
Cron configurable (diario, cada 2 días, semanal)
Tiempo máximo de ejecución configurable (30-60 min)


🔧 Requerimientos Técnicos
Requerimientos Funcionales
RF-1: Autenticación

El sistema debe mantener la sesión de LinkedIn activa
Debe manejar cookies de sesión guardadas localmente
Debe detectar si la sesión expiró y solicitar re-login manual

RF-2: Búsqueda de ofertas

Buscar en LinkedIn Jobs con filtros: ubicación, keywords, fecha de publicación
Extraer: Título, empresa, ubicación, URL, si tiene Easy Apply
Limitar a X ofertas por ejecución (configurable, ej: 20)

RF-3: Aplicación automática

Abrir oferta con Easy Apply
Rellenar formulario con datos pre-configurados
Manejar formularios multi-paso
Subir CV correcto según clasificación
Detectar preguntas no configuradas y pausar

RF-4: Gestión de datos

Crear/actualizar Google Sheet con estructura definida
Evitar duplicados por URL de oferta
Registrar timestamp de cada acción
Exportar logs de errores

RF-5: Monitoreo

Revisar estado de postulaciones cada X días
Detectar cambios de estado
Identificar mensajes nuevos de reclutadores
Actualizar Google Sheet con nuevos estados

Requerimientos No Funcionales
RNF-1: Rendimiento

Tiempo máximo de ejecución: 60 minutos
Procesamiento de 15-25 ofertas por ejecución
Delay entre acciones (2-5 seg) para evitar detección como bot

RNF-2: Confiabilidad

Retry automático en caso de error temporal (3 intentos)
Guardar progreso después de cada postulación
Continuar desde donde quedó si se interrumpe

RNF-3: Seguridad

Credenciales guardadas localmente encriptadas
No guardar contraseñas en texto plano
Cookies de sesión en archivo .env ignorado por git

RNF-4: Usabilidad

Documentación clara en español
Mensajes de error descriptivos
Setup en menos de 30 minutos

RNF-5: Mantenibilidad

Código modular y comentado
Configuración separada del código
Logs estructurados para debugging


📊 Estructura de Datos (Google Sheets)
Pestaña 1: "Postulaciones"
ColumnaTipoDescripciónIDAutoNúmero únicoFecha_AplicaciónDateCuándo se aplicóEmpresaTextNombre de la empresaPuestoTextTítulo del trabajoURLURLLink a la ofertaUbicaciónTextUbicación del trabajoTipo_AplicaciónEnumAUTO / MANUALCV_UsadoEnumSOFTWARE / CONSULTORIAEstadoEnumAPLICADO / EN_REVISION / ENTREVISTA / RECHAZADO / CANCELADOÚltimo_UpdateDateÚltima vez que se verificóNotasTextObservacionesPruebas_PendientesBooleanSi tiene pruebas técnicas
Pestaña 2: "Dashboard"

Total postulaciones
Por estado (gráficos)
Tasa de respuesta
Últimas 5 postulaciones

Pestaña 3: "Preguntas_Pendientes"

Pregunta encontrada
Fecha
URL oferta
Estado (PENDIENTE / CONFIGURADA)


🚀 Plan de Implementación (Fases)
Fase 0: Setup del entorno ⏱️ 1-2 horas

 Instalar Docker
 Levantar n8n local
 Configurar Google Sheets API
 Crear estructura de carpetas del proyecto

Fase 1: MVP - Búsqueda básica ⏱️ 3-4 horas

 Script Python/Selenium para login LinkedIn
 Búsqueda con filtros básicos
 Extracción de datos de ofertas
 Guardar en Google Sheets

Fase 2: Postulación Easy Apply ⏱️ 5-6 horas

 Detectar botón Easy Apply
 Rellenar formulario básico
 Subir CV
 Enviar aplicación
 Manejo de errores

Fase 3: Inteligencia y configuración ⏱️ 3-4 horas

 Sistema de respuestas pre-configuradas
 Selección automática de CV
 Detección de preguntas nuevas
 Archivo de configuración

Fase 4: Seguimiento ⏱️ 2-3 horas

 Script de revisión de estados
 Actualización automática en Sheets
 Dashboard con métricas

Fase 5: Polish y documentación ⏱️ 2-3 horas

 README completo
 Scripts de setup automatizados
 Manejo robusto de errores
 Logs claros