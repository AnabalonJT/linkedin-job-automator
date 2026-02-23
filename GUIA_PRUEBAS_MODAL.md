# Guía de Pruebas - Modal y Formularios LinkedIn

## Objetivo
Validar que el sistema puede:
1. Detectar trabajos eliminados/cerrados
2. Hacer click en el botón "Solicitud sencilla" (tanto `<button>` como `<a>`)
3. Verificar que el modal se abre correctamente
4. Procesar formularios dentro del modal

---

## Opción 1: Prueba Rápida con Script de Test

### Paso 1: Configurar URLs de Prueba

Edita el archivo `scripts/test_selectors.py` y agrega URLs de trabajos reales:

```python
test_urls = [
    "https://www.linkedin.com/jobs/view/1234567890/",  # Trabajo activo con Easy Apply
    "https://www.linkedin.com/jobs/view/9876543210/",  # Trabajo cerrado (para probar detección)
]
```

### Paso 2: Ejecutar el Test

```bash
# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Ejecutar test
python scripts/test_selectors.py
```

### Paso 3: Revisar Resultados

El script mostrará:
- ✓ Si el trabajo está activo o cerrado
- ✓ Qué selector encontró el botón Easy Apply
- ✓ Si el modal se abrió correctamente
- ✓ Si encuentra el botón "Siguiente"

Si algo falla, se guardará un screenshot en `data/logs/test_no_modal.png`

---

## Opción 2: Prueba Completa con el Sistema

### Paso 1: Preparar Trabajos de Prueba

Asegúrate de tener trabajos en `data/logs/jobs_found.json` con:
- Al menos 1 trabajo activo con Easy Apply
- Al menos 1 trabajo cerrado (opcional, para probar detección)

### Paso 2: Ejecutar el Aplicador

```bash
# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Ejecutar aplicador
python scripts/linkedin_applier.py
```

### Paso 3: Monitorear Logs

Abre otra terminal y sigue los logs en tiempo real:

```bash
# Linux/Mac
tail -f data/logs/execution_*.log

# Windows PowerShell
Get-Content data/logs/execution_*.log -Wait -Tail 50
```

Busca estos mensajes:
- `✓ Botón Easy Apply encontrado con: [selector]`
- `✓ Modal de aplicación abierto correctamente`
- `✗ Trabajo cerrado - ya no acepta postulaciones`

### Paso 4: Verificar Google Sheets

Abre tu Google Sheet y revisa la hoja "Postulaciones":

| Estado | Qué Verificar |
|--------|---------------|
| `APPLIED` | ✓ Aplicación exitosa, CV usado registrado |
| `ELIMINADO` | ✓ Trabajo cerrado, nota explica el motivo |
| `MANUAL` | ✓ Requiere postulación externa o sin Easy Apply |
| `ERROR` | ✓ Error técnico, revisar screenshot en logs |

---

## Casos de Prueba Específicos

### Caso 1: Trabajo con Easy Apply (Botón `<button>`)

**Objetivo**: Verificar que el sistema puede hacer click en botones tradicionales

**Pasos**:
1. Buscar un trabajo con Easy Apply que use `<button>`
2. Ejecutar el aplicador
3. Verificar que se hace click y se abre el modal

**Resultado Esperado**:
```
✓ Botón Easy Apply encontrado con: button[aria-label*='Easy Apply']
✓ Click en Easy Apply realizado
✓ Modal de aplicación abierto correctamente
```

---

### Caso 2: Trabajo con Easy Apply (Link `<a>`)

**Objetivo**: Verificar que el sistema puede hacer click en links que funcionan como botones

**Pasos**:
1. Buscar un trabajo con Easy Apply que use `<a>` (como en `solicitud_sencilla.html`)
2. Ejecutar el aplicador
3. Verificar que se hace click y se abre el modal

**Resultado Esperado**:
```
✓ Botón Easy Apply encontrado con: a[aria-label*='Solicitud sencilla']
✓ Click en Easy Apply realizado
✓ Modal de aplicación abierto correctamente
```

---

### Caso 3: Trabajo Cerrado/Eliminado

**Objetivo**: Verificar que el sistema detecta trabajos que ya no aceptan postulaciones

**Pasos**:
1. Buscar un trabajo cerrado (puede ser uno antiguo)
2. Ejecutar el aplicador
3. Verificar que se marca como ELIMINADO

**Resultado Esperado**:
```
✗ Trabajo cerrado - ya no acepta postulaciones
Estado: ELIMINADO
```

**En Google Sheets**:
- Estado: `ELIMINADO`
- Notas: "Trabajo ya no acepta postulaciones (eliminado/cerrado)"

---

### Caso 4: Trabajo sin Easy Apply (Postulación Externa)

**Objetivo**: Verificar que el sistema detecta trabajos que requieren postulación externa

**Pasos**:
1. Buscar un trabajo que solo tenga botón "Postular" (no Easy Apply)
2. Ejecutar el aplicador
3. Verificar que se marca como MANUAL

**Resultado Esperado**:
```
✗ Trabajo requiere postulación externa
Estado: MANUAL
```

**En Google Sheets**:
- Estado: `MANUAL`
- Notas: "Requiere postulación externa (no Easy Apply)"

---

### Caso 5: Modal No Se Abre

**Objetivo**: Verificar que el sistema detecta cuando el modal no se abre después del click

**Pasos**:
1. Simular un caso donde el modal no se abre (puede ser por error de red)
2. Ejecutar el aplicador
3. Verificar que se guarda screenshot y se marca como ERROR

**Resultado Esperado**:
```
✓ Click en Easy Apply realizado
✗ Modal no se abrió después del click
Screenshot guardado: data/logs/debug_no_modal_[titulo].png
Estado: ERROR
```

---

## Debugging

### Si el botón Easy Apply no se encuentra:

1. **Revisar screenshot**: `data/logs/debug_no_button_*.png`
2. **Verificar selectores**: Abrir el HTML de la página y buscar el botón manualmente
3. **Agregar nuevo selector**: Si el botón tiene una clase/atributo diferente, agregarlo en `linkedin_applier.py`:

```python
selectors = [
    # ... selectores existentes ...
    "tu_nuevo_selector_aqui"
]
```

### Si el modal no se abre:

1. **Revisar screenshot**: `data/logs/debug_no_modal_*.png`
2. **Verificar timing**: Puede que necesite más tiempo de espera
3. **Aumentar timeout**: En `linkedin_applier.py`, cambiar:

```python
modal = WebDriverWait(self.driver, 5).until(  # Cambiar 5 a 10
    EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
)
```

### Si el formulario no se rellena:

1. **Revisar logs**: Buscar mensajes de "Pregunta sin respuesta"
2. **Agregar respuestas**: Editar `config/respuestas_comunes.json`
3. **Verificar patrones**: Asegurarse de que los patrones coincidan con las preguntas

---

## Checklist de Validación

Antes de considerar las pruebas completas, verifica:

- [ ] El sistema detecta trabajos cerrados y los marca como `ELIMINADO`
- [ ] El sistema puede hacer click en botones `<button>` con Easy Apply
- [ ] El sistema puede hacer click en links `<a>` con Easy Apply
- [ ] El sistema verifica que el modal se abre correctamente
- [ ] El sistema guarda screenshots cuando hay errores
- [ ] Google Sheets se actualiza con el estado correcto
- [ ] Las notas en Google Sheets explican claramente el estado
- [ ] Los logs son claros y útiles para debugging

---

## Próximos Pasos

Una vez validadas las pruebas:

1. **Ejecutar en producción**: Usar el workflow de n8n para automatizar
2. **Monitorear resultados**: Revisar Google Sheets diariamente
3. **Ajustar respuestas**: Agregar nuevas respuestas según preguntas encontradas
4. **Optimizar selectores**: Si encuentras nuevos formatos de botones, agregarlos

---

## Soporte

Si encuentras problemas:

1. Revisa los logs en `data/logs/execution_*.log`
2. Revisa los screenshots en `data/logs/debug_*.png`
3. Verifica el estado en Google Sheets
4. Consulta `CAMBIOS_MODAL_FORMULARIO.md` para detalles técnicos
