# Referencia de Selectores HTML - LinkedIn

## Propósito
Este documento contiene ejemplos de los elementos HTML que el sistema busca en LinkedIn, útil para debugging y mantenimiento futuro.

---

## 1. Botón "Solicitud Sencilla" / "Easy Apply"

### Variante 1: Button Element
```html
<button 
    class="jobs-apply-button artdeco-button--primary" 
    aria-label="Solicitud sencilla"
    data-live-test-job-apply-button="">
    Easy Apply
</button>
```

**Selectores que lo encuentran**:
- `button.jobs-apply-button`
- `button[aria-label*='Solicitud sencilla']`
- `button[aria-label*='Easy Apply']`
- `button[data-live-test-job-apply-button]`

---

### Variante 2: Link Element (Caso Real)
```html
<a 
    class="cbaa75c4 _91fce0ff _21173a9d _37c90019 cdcea5fd _1843f717 _62de7624 cd324c6e fc29c723 _61031593 a6067ae0 _12e91934 _6f2720fd _94a82bb0" 
    aria-disabled="false" 
    href="https://www.linkedin.com/jobs/view/4373620084/apply/?openSDUIApplyFlow=true&refId=..."
    aria-label="Solicitud sencilla"
    data-view-name="job-apply-button">
    <span>Solicitud sencilla</span>
</a>
```

**Selectores que lo encuentran**:
- `a[aria-label*='Solicitud sencilla']`
- `a[aria-label*='Easy Apply']`
- `a.jobs-apply-button` (si tiene esa clase)

---

## 2. Modal de Aplicación

### Estructura del Modal
```html
<div 
    data-test-modal-container="" 
    data-test-modal-id="easy-apply-modal" 
    aria-hidden="false" 
    class="artdeco-modal-overlay artdeco-modal-overlay--layer-default artdeco-modal-overlay--is-top-layer ember-view">
    
    <div 
        data-test-modal="" 
        role="dialog" 
        tabindex="-1" 
        class="artdeco-modal artdeco-modal--layer-default jobs-easy-apply-modal" 
        size="large" 
        aria-labelledby="jobs-apply-header">
        
        <div class="artdeco-modal__header ember-view">
            <h2 id="jobs-apply-header">
                Solicitar empleo en [Empresa]
            </h2>
        </div>
        
        <div class="artdeco-modal__content jobs-easy-apply-modal__content p0 ember-view">
            <!-- Contenido del formulario -->
        </div>
        
    </div>
</div>
```

**Selectores que lo encuentran**:
- `div[data-test-modal-id='easy-apply-modal']`
- `div.jobs-easy-apply-modal`
- `div[role='dialog'][aria-labelledby*='apply']`

---

## 3. Botones de Navegación en el Modal

### Botón "Siguiente"
```html
<button 
    aria-label="Ir al siguiente paso" 
    class="artdeco-button artdeco-button--2 artdeco-button--primary ember-view" 
    data-easy-apply-next-button="" 
    data-live-test-easy-apply-next-button="" 
    type="button">
    <span class="artdeco-button__text">Siguiente</span>
</button>
```

**Selectores que lo encuentran**:
- `button[aria-label*='siguiente']`
- `button[aria-label*='Next']`
- `button[data-easy-apply-next-button]`
- `button.artdeco-button--primary`

---

### Botón "Enviar"
```html
<button 
    aria-label="Enviar solicitud" 
    class="artdeco-button artdeco-button--2 artdeco-button--primary ember-view" 
    type="button">
    <span class="artdeco-button__text">Enviar</span>
</button>
```

**Selectores que lo encuentran**:
- `button[aria-label*='Enviar']`
- `button[aria-label*='Submit']`
- `button[aria-label*='Send']`

---

## 4. Campos del Formulario

### Email Dropdown
```html
<select 
    id="text-entity-list-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-4373620084-26171961484-multipleChoice" 
    class="fb-dash-form-element__select-dropdown" 
    aria-describedby="..." 
    aria-required="true" 
    required="" 
    data-test-text-entity-list-form-select="">
    <option value="Select an option">Select an option</option>
    <option value="jtanabalon@gmail.com">jtanabalon@gmail.com</option>
</select>
```

**Cómo se detecta**:
- Tag: `select`
- Label asociado contiene: "email", "correo", "e-mail"
- Se selecciona la opción que contiene "@"

---

### Phone Country Code Dropdown
```html
<select 
    id="text-entity-list-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-4373620084-26171961468-phoneNumber-country" 
    class="fb-dash-form-element__select-dropdown" 
    aria-required="true" 
    required="">
    <option value="Select an option">Select an option</option>
    <option value="Chile (+56)">Chile (+56)</option>
    <!-- ... más países ... -->
</select>
```

**Cómo se detecta**:
- Tag: `select`
- Label asociado contiene: "phone", "teléfono", "country code"
- Se selecciona la opción que contiene dígitos

---

### Mobile Phone Number Input
```html
<input 
    inputmode="text" 
    class="artdeco-text-input--input" 
    id="single-line-text-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-4373620084-26171961468-phoneNumber-nationalNumber" 
    required="" 
    aria-describedby="..." 
    dir="auto" 
    type="text">
```

**Cómo se detecta**:
- Tag: `input[type='text']` o `input[type='tel']`
- Label asociado contiene: "phone", "teléfono", "mobile"
- Se rellena con el teléfono de `respuestas_comunes.json`

---

## 5. Indicadores de Trabajo Cerrado

### Textos que Indican Trabajo Cerrado
```html
<!-- Variante 1 -->
<div class="job-details-jobs-unified-top-card__primary-description">
    <span>No longer accepting applications</span>
</div>

<!-- Variante 2 -->
<div class="job-details-jobs-unified-top-card__primary-description">
    <span>Ya no se aceptan solicitudes</span>
</div>

<!-- Variante 3 -->
<div class="artdeco-inline-feedback artdeco-inline-feedback--error">
    <span>This job is no longer available</span>
</div>
```

**Textos que se buscan** (case-insensitive):
- "No longer accepting applications"
- "Ya no se aceptan solicitudes"
- "This job is no longer available"
- "Este trabajo ya no está disponible"
- "Closed"
- "Cerrado"

---

## 6. Botón de Postulación Externa

### Cuando NO hay Easy Apply
```html
<button 
    class="jobs-apply-button" 
    aria-label="Postular en el sitio web de la empresa">
    Postular
</button>

<!-- O como link -->
<a 
    href="https://external-site.com/apply" 
    class="jobs-apply-button"
    aria-label="Apply on company website">
    Apply
</a>
```

**Selectores que lo encuentran**:
- `button[aria-label*='Postular']`
- `a[aria-label*='Apply']`
- `button[aria-label*='company website']`

---

## 7. Barra de Progreso del Formulario

```html
<div class="display-flex ph5 pv2">
    <div class="flex-grow-1 artdeco-completeness-meter-linear ember-view">
        <div class="artdeco-completeness-meter-linear__progress-container">
            <progress 
                max="100" 
                value="0" 
                class="artdeco-completeness-meter-linear__progress-element" 
                aria-valuetext="Valor actual: 0" 
                aria-valuemin="0" 
                aria-valuenow="0" 
                aria-valuemax="100" 
                style="--offset-value: 0%;">
                Valor actual: 0
            </progress>
        </div>
    </div>
    <span class="pl3 t-14 t-black--light" aria-label="El progreso de tu solicitud de empleo está en el 0." role="note">
        0&nbsp;%
    </span>
</div>
```

**Uso**: Indica el progreso del formulario multi-paso (0%, 25%, 50%, 75%, 100%)

---

## 8. Botón de Cerrar Modal

```html
<button 
    aria-label="Descartar" 
    class="artdeco-button artdeco-button--circle artdeco-button--muted artdeco-button--2 artdeco-button--tertiary ember-view artdeco-modal__dismiss" 
    data-test-modal-close-btn="">
    <svg role="none" aria-hidden="true" class="artdeco-button__icon">
        <use href="#close-medium" width="24" height="24"></use>
    </svg>
</button>
```

**Selector**:
- `button[data-test-modal-close-btn]`
- `button.artdeco-modal__dismiss`
- `button[aria-label*='Descartar']`
- `button[aria-label*='Dismiss']`

---

## Notas de Mantenimiento

### Cuando Agregar Nuevos Selectores

Si encuentras un botón/elemento que no se detecta:

1. **Inspeccionar el elemento** en el navegador (F12)
2. **Identificar atributos únicos**:
   - `aria-label`
   - `data-*` attributes
   - `class` (preferir clases semánticas, no generadas)
   - `id` (si es estable)
3. **Agregar selector** en `linkedin_applier.py`:
   ```python
   selectors = [
       # ... selectores existentes ...
       "tu_nuevo_selector_aqui"
   ]
   ```
4. **Probar** con `scripts/test_selectors.py`

### Selectores a Evitar

❌ **No usar**:
- Clases CSS generadas aleatoriamente: `cbaa75c4`, `_91fce0ff`
- IDs con números aleatorios: `ember418`, `ember419`
- Selectores muy específicos que cambien frecuentemente

✅ **Preferir**:
- `aria-label` (más estable)
- `data-*` attributes semánticos
- Clases con nombres descriptivos: `jobs-apply-button`, `artdeco-modal`
- Roles ARIA: `role="dialog"`, `role="button"`

---

## Changelog

- **2026-02-23**: Versión inicial con selectores actuales de LinkedIn
- Próximas actualizaciones: Agregar nuevos selectores según se descubran

---

## Referencias

- [LinkedIn HTML actual](solicitud_sencilla.html)
- [Modal de formulario](form_postulacion.html)
- [Código del aplicador](scripts/linkedin_applier.py)
