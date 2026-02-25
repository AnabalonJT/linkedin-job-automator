"""
Detector de campos de formulario de LinkedIn.

Este módulo identifica y clasifica campos del formulario de postulación dentro del
modal de "Solicitud sencilla". Detecta diferentes tipos de campos (text, email, phone,
dropdown, etc.) y extrae su propósito usando metadata disponible.
"""

import logging
from typing import List
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from models import FormField

logger = logging.getLogger(__name__)


class FormFieldDetector:
    """
    Detecta y clasifica campos del formulario de postulación.
    
    Busca campos SOLO dentro del contexto del modal para evitar detectar elementos
    de la página principal de LinkedIn (como el dropdown de idioma).
    """
    
    # Selectores específicos de LinkedIn para cada tipo de campo
    FIELD_TYPES = {
        'text': 'input[data-test-single-line-text-form-component]',
        'numeric': 'input[inputmode="text"][id*="numeric"], input[type="text"][id*="numeric"]',  # Campos numéricos
        'email': 'input[type="email"]',
        'phone_country': 'select[id*="phoneNumber-country"]',
        'phone_number': 'input[id*="phoneNumber-nationalNumber"]',
        'dropdown': 'select[data-test-text-entity-list-form-select]',
        'textarea': 'textarea',
        'radio': 'input[type="radio"]',
        'checkbox': 'input[type="checkbox"]',
        'file': 'input[type="file"], input[id*="document-upload"], input[accept*="pdf"]',  # Campos de archivo
        # Bug 2 fix: Selector mejorado para CV radio buttons con fallbacks
        'cv_radio': 'input[type="radio"][id*="jobsDocumentCardToggle"], input[type="radio"][id*="document"], label.jobs-document-upload-redesign-card__container input[type="radio"]'
    }
    
    def detect_fields(self, modal_element: WebElement) -> List[FormField]:
        """
        Detecta todos los campos dentro del modal.
        
        Busca campos SOLO dentro del contexto del modal proporcionado para evitar
        detectar elementos fuera del formulario de postulación.
        
        Args:
            modal_element: WebElement del modal de postulación
            
        Returns:
            Lista de FormField con tipo, label, propósito y elemento
        """
        logger.info("Detectando campos del formulario dentro del modal")
        detected_fields = []
        
        # Import WebDriverWait for explicit waits (Bug 2 fix)
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException
        
        for field_type, selector in self.FIELD_TYPES.items():
            try:
                # Bug 2 fix: Add explicit wait for cv_radio fields to render
                if field_type == 'cv_radio':
                    try:
                        WebDriverWait(modal_element, 5).until(
                            lambda driver: len(modal_element.find_elements("css selector", selector)) > 0
                        )
                        logger.info(f"✓ CV radio buttons encontrados después de espera explícita")
                    except TimeoutException:
                        logger.warning(f"Timeout esperando CV radio buttons con selector: {selector}")
                        logger.warning(f"HTML del modal (primeros 500 chars): {modal_element.get_attribute('outerHTML')[:500]}")
                
                # Buscar elementos SOLO dentro del modal
                elements = modal_element.find_elements("css selector", selector)
                
                # Bug 2 fix: Log detallado para cv_radio
                if field_type == 'cv_radio':
                    if not elements:
                        logger.warning(f"No se encontraron CV radio buttons con selector: {selector}")
                        logger.warning(f"Intentando búsqueda más amplia...")
                        # Intentar búsqueda más amplia si el selector específico falla
                        elements = modal_element.find_elements("xpath", "//input[@type='radio' and contains(@id, 'document')]")
                        if elements:
                            logger.info(f"✓ Encontrados {len(elements)} CV radio buttons con búsqueda ampliada")
                    else:
                        logger.info(f"✓ Encontrados {len(elements)} CV radio buttons")
                
                for element in elements:
                    try:
                        # Verificar que el elemento sea visible e interactuable
                        if not element.is_displayed():
                            continue
                        
                        # Extraer información del campo
                        label = self._get_field_label(element)
                        purpose = self.get_field_purpose(element)
                        required = self._is_field_required(element)
                        options = self._get_field_options(element) if field_type in ['dropdown', 'phone_country'] else None
                        
                        field = FormField(
                            element=element,
                            field_type=field_type,
                            label=label,
                            purpose=purpose,
                            required=required,
                            options=options
                        )
                        
                        detected_fields.append(field)
                        logger.info(f"Campo detectado: tipo={field_type}, propósito={purpose}, requerido={required}")
                        
                    except (StaleElementReferenceException, NoSuchElementException) as e:
                        logger.debug(f"Error al procesar elemento {field_type}: {e}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Error al buscar campos de tipo {field_type}: {e}")
                continue
        
        logger.info(f"Total de campos detectados: {len(detected_fields)}")
        return detected_fields
    
    def get_field_purpose(self, field_element: WebElement) -> str:
        """
        Identifica el propósito del campo usando metadata disponible.
        
        Intenta extraer el propósito del campo desde múltiples fuentes en orden:
        1. Label asociado (usando 'for' attribute o parent label)
        2. Placeholder text
        3. aria-label attribute
        4. id del elemento
        5. name attribute
        
        Args:
            field_element: WebElement del campo
            
        Returns:
            String describiendo el propósito (ej: "years of experience", "phone number")
        """
        # 1. Intentar obtener label asociado
        try:
            field_id = field_element.get_attribute('id')
            if field_id:
                # Buscar label con for=field_id
                parent = field_element.find_element("xpath", "../..")
                label = parent.find_element("css selector", f"label[for='{field_id}']")
                label_text = label.text.strip()
                if label_text:
                    return label_text
        except:
            pass
        
        # 2. Intentar obtener label parent
        try:
            parent = field_element.find_element("xpath", "..")
            if parent.tag_name.lower() == 'label':
                label_text = parent.text.strip()
                if label_text:
                    return label_text
        except:
            pass
        
        # 3. Intentar placeholder
        try:
            placeholder = field_element.get_attribute('placeholder')
            if placeholder and placeholder.strip():
                return placeholder.strip()
        except:
            pass
        
        # 4. Intentar aria-label
        try:
            aria_label = field_element.get_attribute('aria-label')
            if aria_label and aria_label.strip():
                return aria_label.strip()
        except:
            pass
        
        # 5. Intentar id (limpiar y formatear)
        try:
            field_id = field_element.get_attribute('id')
            if field_id:
                # Convertir camelCase o snake_case a texto legible
                purpose = field_id.replace('_', ' ').replace('-', ' ')
                # Insertar espacios antes de mayúsculas
                import re
                purpose = re.sub(r'([a-z])([A-Z])', r'\1 \2', purpose)
                return purpose.strip()
        except:
            pass
        
        # 6. Intentar name attribute
        try:
            name = field_element.get_attribute('name')
            if name:
                purpose = name.replace('_', ' ').replace('-', ' ')
                import re
                purpose = re.sub(r'([a-z])([A-Z])', r'\1 \2', purpose)
                return purpose.strip()
        except:
            pass
        
        # Si no se pudo determinar, retornar tipo genérico
        return "unknown field"
    
    def _get_field_label(self, field_element: WebElement) -> str:
        """
        Obtiene el label del campo (versión simplificada de get_field_purpose).
        
        Args:
            field_element: WebElement del campo
            
        Returns:
            Label del campo o string vacío
        """
        purpose = self.get_field_purpose(field_element)
        return purpose if purpose != "unknown field" else ""
    
    def _is_field_required(self, field_element: WebElement) -> bool:
        """
        Determina si un campo es obligatorio.
        
        Args:
            field_element: WebElement del campo
            
        Returns:
            True si el campo es obligatorio, False en caso contrario
        """
        try:
            # Verificar atributo required
            required_attr = field_element.get_attribute('required')
            if required_attr:
                return True
            
            # Verificar aria-required
            aria_required = field_element.get_attribute('aria-required')
            if aria_required and aria_required.lower() == 'true':
                return True
            
            # Buscar asterisco (*) en label asociado
            try:
                parent = field_element.find_element("xpath", "../..")
                label_text = parent.text
                if '*' in label_text:
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.debug(f"Error al verificar si campo es requerido: {e}")
            return False
    
    def _get_field_options(self, field_element: WebElement) -> List[str]:
        """
        Obtiene las opciones disponibles para campos dropdown/select.
        
        Args:
            field_element: WebElement del campo select
            
        Returns:
            Lista de opciones disponibles (excluyendo placeholders)
        """
        try:
            options = field_element.find_elements("tag name", "option")
            valid_options = []
            
            for opt in options:
                text = opt.text.strip()
                value = opt.get_attribute('value')
                
                # Filtrar opciones placeholder/vacías
                if not text or not value:
                    continue
                
                # Filtrar textos placeholder comunes
                placeholder_texts = [
                    'selecciona una opción',
                    'select an option',
                    'choose an option',
                    'elige una opción',
                    'seleccione',
                    'select',
                    'choose',
                    '--',
                    '---'
                ]
                
                if text.lower() in placeholder_texts:
                    continue
                
                valid_options.append(text)
            
            return valid_options
        except Exception as e:
            logger.info(f"Error al obtener opciones del dropdown: {e}")
            return []
