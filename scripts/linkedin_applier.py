#!/usr/bin/env python3
"""
LinkedIn Job Applier
Aplica automáticamente a trabajos con Easy Apply
"""

import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

from utils import Config, Logger, select_cv_by_keywords

# Optional: Telegram notifier (graceful if env not configured)
try:
    from telegram_notifier import TelegramNotifier
except Exception:
    TelegramNotifier = None


class LinkedInApplier:
    """Aplicador automático a trabajos de LinkedIn"""
    
    def __init__(self, driver, config: Config, logger: Logger):
        self.driver = driver
        self.config = config
        self.logger = logger
        
        # Cargar respuestas configuradas
        self.answers = config.load_json_config('respuestas_comunes.json')
        
        # Cargar rutas de CVs
        self.cv_paths = config.get_cv_paths()
    
    def apply_to_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica a un trabajo específico
        
        Args:
            job: Diccionario con datos del trabajo
        
        Returns:
            Diccionario con resultado de la aplicación
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Aplicando a: {job['title']} - {job['company']}")
        self.logger.info(f"{'='*60}")
        
        result = {
            'job_url': job['url'],
            'job_title': job['title'],
            'company': job['company'],
            'success': False,
            'status': 'PENDING',  # Estados: PENDING, APPLIED, MANUAL, ERROR, ELIMINADO
            'error': None,
            'questions_encountered': [],
            'cv_used': None
        }
        
        try:
            # Ir a la página del trabajo
            self.driver.get(job['url'])
            self.logger.info(f"  Cargando página del trabajo...")
            time.sleep(5)  # Aumentar tiempo de espera
            
            # Scroll para asegurar que el botón esté visible
            self.driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(1)
            
            # Verificar si el trabajo ya no acepta postulaciones (eliminado/cerrado)
            try:
                # Buscar indicadores de trabajo cerrado
                closed_indicators = [
                    "No longer accepting applications",
                    "Ya no se aceptan solicitudes",
                    "This job is no longer available",
                    "Este trabajo ya no está disponible",
                    "Closed",
                    "Cerrado"
                ]
                
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                is_closed = any(indicator.lower() in page_text.lower() for indicator in closed_indicators)
                
                if is_closed:
                    result['error'] = "Trabajo ya no acepta postulaciones (eliminado/cerrado)"
                    result['status'] = 'ELIMINADO'
                    self.logger.warning("✗ Trabajo cerrado - ya no acepta postulaciones")
                    return result
            except Exception:
                pass  # Continuar si no se puede verificar
            
            # Buscar botón Easy Apply con múltiples selectores (incluyendo <a> tags)
            easy_apply_button = None
            selectors = [
                # Botones tradicionales
                "button.jobs-apply-button",
                "button[aria-label*='Solicitud sencilla']",
                "button[aria-label*='Easy Apply']",
                "button#jobs-apply-button-id",
                "button[data-live-test-job-apply-button]",
                # Links que funcionan como botones (caso común en LinkedIn)
                "a[aria-label*='Solicitud sencilla']",
                "a[aria-label*='Easy Apply']",
                "a.jobs-apply-button"
            ]
            
            for selector in selectors:
                try:
                    easy_apply_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if easy_apply_button:
                        self.logger.info(f"  ✓ Botón Easy Apply encontrado con: {selector}")
                        break
                except TimeoutException:
                    continue
            
            if not easy_apply_button:
                # Verificar si es porque el trabajo está cerrado o no tiene Easy Apply
                try:
                    # Buscar botón "Postular" externo (no Easy Apply)
                    external_apply = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Postular'], a[aria-label*='Apply']")
                    if external_apply:
                        result['error'] = "Requiere postulación externa (no Easy Apply)"
                        result['status'] = 'MANUAL'
                        self.logger.warning("✗ Trabajo requiere postulación externa")
                        return result
                except Exception:
                    pass
                
                result['error'] = "No se encontró botón Easy Apply"
                result['status'] = 'MANUAL'
                self.logger.warning("✗ No se encontró botón Easy Apply con ningún selector")
                
                # Guardar screenshot para debug
                screenshot_path = Path(f"data/logs/debug_no_button_{job['title'][:30]}.png")
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.info(f"  Screenshot guardado: {screenshot_path}")
                
                return result
            
            # Click en Easy Apply
            try:
                # Scroll al botón
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", easy_apply_button)
                time.sleep(1)
                
                # Intentar click
                easy_apply_button.click()
                self.logger.info("  ✓ Click en Easy Apply realizado")
                time.sleep(3)  # Esperar a que abra el modal
                
            except Exception as e:
                # Intentar click con JavaScript si falla el click normal
                self.logger.warning(f"  Click normal falló, intentando con JavaScript...")
                self.driver.execute_script("arguments[0].click();", easy_apply_button)
                time.sleep(3)
            
            # Verificar que el modal se haya abierto
            try:
                modal_selectors = [
                    "div[data-test-modal-id='easy-apply-modal']",
                    "div.jobs-easy-apply-modal",
                    "div[role='dialog'][aria-labelledby*='apply']"
                ]
                
                modal_found = False
                for modal_selector in modal_selectors:
                    try:
                        modal = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
                        )
                        if modal and modal.is_displayed():
                            modal_found = True
                            self.logger.info("  ✓ Modal de aplicación abierto correctamente")
                            break
                    except TimeoutException:
                        continue
                
                if not modal_found:
                    result['error'] = "Modal de aplicación no se abrió"
                    result['status'] = 'ERROR'
                    self.logger.warning("✗ Modal no se abrió después del click")
                    
                    # Screenshot para debug
                    screenshot_path = Path(f"data/logs/debug_no_modal_{job['title'][:30]}.png")
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    self.driver.save_screenshot(str(screenshot_path))
                    
                    return result
                    
            except Exception as e:
                self.logger.warning(f"  No se pudo verificar modal: {str(e)}")
                # Continuar de todas formas, puede que esté abierto
            
            # Procesar formulario multi-paso
            aplicacion_exitosa = self.process_application_form(job, result)
            
            if aplicacion_exitosa:
                result['success'] = True
                self.logger.success(f"✓ Aplicación enviada exitosamente!")
            else:
                self.logger.warning(f"✗ No se pudo completar la aplicación")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error aplicando: {str(e)}")
        
        return result
    
    def process_application_form(self, job: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        Procesa el formulario de aplicación multi-paso
        
        Args:
            job: Datos del trabajo
            result: Diccionario de resultado (se modifica)
        
        Returns:
            True si se completó exitosamente, False si no
        """
        max_steps = 10
        current_step = 0
        
        # Trackear preguntas ya vistas para evitar duplicados
        seen_questions = set()
        questions_without_answer = []
        
        # Detectar si estamos en loop (mismo botón varias veces)
        button_history = []
        
        while current_step < max_steps:
            current_step += 1
            self.logger.info(f"  Paso {current_step}...")
            
            time.sleep(2)
            
            # Rellenar formulario actual ANTES de buscar botón
            new_questions = self.fill_current_form_step(job, result, seen_questions)
            questions_without_answer.extend(new_questions)
            
            # Si hay más de 3 preguntas sin respuesta, abortar
            if len(questions_without_answer) > 3:
                self.logger.warning(f"  ✗ Demasiadas preguntas sin respuesta ({len(questions_without_answer)}). Marcando como MANUAL.")
                result['error'] = f"Requiere {len(questions_without_answer)} respuestas manuales"
                result['status'] = 'MANUAL'
                return False
            
            time.sleep(1)
            
            # Buscar botón de acción
            next_button = None
            button_selectors = [
                "button[aria-label*='Enviar']",
                "button[aria-label*='Submit']",
                "button[aria-label*='Send']",
                "button[aria-label*='Continuar']",
                "button[aria-label*='siguiente']",
                "button[aria-label*='Next']",
                "button[aria-label*='Siguiente']",
                "button[data-easy-apply-next-button]",
                "button[aria-label*='Review']",
                "button[aria-label*='Revisar']",
                "button.artdeco-button--primary"
            ]
            
            for selector in button_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            next_button = btn
                            break
                    if next_button:
                        break
                except NoSuchElementException:
                    continue
            
            if not next_button:
                self.logger.warning("  No se encontró botón de acción")
                screenshot_path = Path(f"data/logs/debug_no_next_button_{current_step}.png")
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.info(f"  Screenshot guardado: {screenshot_path}")
                return False
            
            button_aria_label = next_button.get_attribute('aria-label') or ''
            button_text = next_button.text or button_aria_label
            
            # IMPORTANTE: Detectar botón "Enviar" ANTES de hacer click
            button_context = f"{button_text} {button_aria_label}".lower()
            is_submit_button = any(word in button_context for word in ['enviar', 'submit', 'send application'])
            
            # Detectar loop infinito
            button_history.append(button_aria_label)
            if len(button_history) > 3:
                # Si los últimos 3 botones son iguales, estamos en loop
                if button_history[-1] == button_history[-2] == button_history[-3]:
                    self.logger.warning(f"  ✗ Detectado loop infinito (mismo botón '{button_text}' 3+ veces)")
                    result['error'] = "Loop infinito detectado - formulario bloqueado"
                    result['status'] = 'MANUAL'
                    return False
            
            self.logger.info(f"  Botón encontrado: '{button_text}'")
            
            # Click en el botón
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(0.5)
                next_button.click()
                self.logger.info(f"  ✓ Click en '{button_text}'")
            except Exception as e:
                self.driver.execute_script("arguments[0].click();", next_button)
                self.logger.info(f"  ✓ Click en '{button_text}' (JavaScript)")
            
            time.sleep(2)
            
            # Si era botón "Enviar", aplicación completa
            if is_submit_button:
                # Esperar confirmación
                time.sleep(3)
                self.logger.success("  ✓ Aplicación enviada!")
                result['status'] = 'APPLIED'
                return True
        
        self.logger.warning("  Se alcanzó el límite de pasos")
        result['status'] = 'MANUAL'
        return False
    
    def fill_current_form_step(self, job: Dict[str, Any], result: Dict[str, Any], seen_questions: set) -> list:
        """
        Rellena el paso actual del formulario
        
        Args:
            job: Datos del trabajo
            result: Diccionario de resultado
            seen_questions: Set de preguntas ya vistas (para evitar duplicados)
        
        Returns:
            Lista de preguntas nuevas sin respuesta
        """
        new_questions = []
        
        try:
            # 1. Upload CV si es necesario
            self.handle_cv_upload(job, result)
            
            # 2. Buscar y rellenar campos de texto
            text_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[type='tel']")
            for field in text_fields:
                self.fill_text_field(field, result)
            
            # 3. Buscar y rellenar textareas
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            for textarea in textareas:
                self.fill_textarea(textarea, result)
            
            # 4. Buscar y responder preguntas de radio/checkbox
            self.handle_radio_questions(result, seen_questions, new_questions)
            
            # 5. Buscar y responder dropdowns
            self.handle_dropdown_questions(result, seen_questions, new_questions)
            
            return new_questions
            
        except Exception as e:
            self.logger.warning(f"  Error rellenando formulario: {str(e)}")
            return new_questions
    
    def handle_cv_upload(self, job: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Maneja la subida de CV"""
        try:
            # Buscar input de archivo
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            
            if not file_inputs:
                return True  # No hay upload, está bien
            
            # Seleccionar CV apropiado
            cv_type = select_cv_by_keywords(
                job.get('title', ''),
                job.get('description', ''),
                self.config
            )
            
            cv_path = self.cv_paths.get(cv_type)
            
            if not cv_path or not Path(cv_path).exists():
                self.logger.warning(f"  CV no encontrado: {cv_path}")
                return False
            
            # Subir CV
            file_inputs[0].send_keys(str(Path(cv_path).absolute()))
            result['cv_used'] = cv_type
            self.logger.info(f"  ✓ CV subido: {cv_type}")
            time.sleep(2)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"  Error subiendo CV: {str(e)}")
            return False
    
    def fill_text_field(self, field, result: Dict[str, Any]):
        """Rellena un campo de texto basándose en su label/placeholder"""
        try:
            # Obtener información del campo
            field_id = field.get_attribute('id') or ''
            field_name = field.get_attribute('name') or ''
            placeholder = field.get_attribute('placeholder') or ''
            aria_label = field.get_attribute('aria-label') or ''
            
            # Buscar label asociado
            label_text = ""
            try:
                if field_id:
                    label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
                    label_text = label.text.lower()
            except NoSuchElementException:
                pass
            
            # Combinar todos los indicadores
            field_context = f"{label_text} {placeholder} {aria_label} {field_name}".lower()
            
            # Si ya tiene valor, no sobrescribir
            if field.get_attribute('value'):
                return
            
            # Determinar qué llenar
            personal_info = self.answers.get('informacion_personal', {})
            
            if any(word in field_context for word in ['email', 'correo', 'e-mail']):
                field.send_keys(personal_info.get('email', ''))
                self.logger.info(f"  ✓ Email ingresado")
            
            elif any(word in field_context for word in ['phone', 'teléfono', 'telefono', 'celular']):
                field.send_keys(personal_info.get('telefono', ''))
                self.logger.info(f"  ✓ Teléfono ingresado")
            
            elif any(word in field_context for word in ['linkedin', 'linkedin url']):
                field.send_keys(personal_info.get('linkedin_url', ''))
                self.logger.info(f"  ✓ LinkedIn URL ingresado")
            
            elif any(word in field_context for word in ['city', 'ciudad', 'location', 'ubicación']):
                field.send_keys(personal_info.get('ciudad', ''))
                self.logger.info(f"  ✓ Ciudad ingresada")
            
        except Exception as e:
            pass  # Silenciosamente continuar si falla un campo
    
    def fill_textarea(self, textarea, result: Dict[str, Any]):
        """Rellena un textarea (probablemente carta de presentación)"""
        try:
            # Si ya tiene contenido, no sobrescribir
            if textarea.get_attribute('value'):
                return
            
            aria_label = textarea.get_attribute('aria-label') or ''
            placeholder = textarea.get_attribute('placeholder') or ''
            
            context = f"{aria_label} {placeholder}".lower()
            
            respuestas_abiertas = self.answers.get('respuestas_abiertas_template', {})
            
            if any(word in context for word in ['cover letter', 'carta', 'presentación', 'motivación']):
                cover_letter = respuestas_abiertas.get('por_que_empresa', '')
                textarea.send_keys(cover_letter)
                self.logger.info(f"  ✓ Carta de presentación ingresada")
            
        except Exception as e:
            pass
    
    def handle_radio_questions(self, result: Dict[str, Any], seen_questions: set, new_questions: list):
        """Maneja preguntas de tipo radio button"""
        try:
            radio_groups = self.driver.find_elements(By.CSS_SELECTOR, "fieldset, div[role='radiogroup']")
            
            for group in radio_groups:
                try:
                    legend = group.find_element(By.TAG_NAME, "legend")
                    question_text = legend.text.lower().strip()
                    
                    # Si ya vimos esta pregunta, skip
                    if question_text in seen_questions:
                        continue
                    
                    answer = self.find_answer_for_question(question_text)
                    
                    if answer:
                        radios = group.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        for radio in radios:
                            label = radio.find_element(By.XPATH, "./following-sibling::label")
                            if answer.lower() in label.text.lower():
                                radio.click()
                                self.logger.info(f"  ✓ Respondido: {question_text[:50]}... → {answer}")
                                seen_questions.add(question_text)
                                break
                    else:
                        if question_text and question_text not in seen_questions:
                            new_questions.append(question_text)
                            seen_questions.add(question_text)
                            result['questions_encountered'].append(question_text)
                            self.logger.warning(f"  ? Pregunta sin respuesta: {question_text[:50]}...")
                        
                except Exception:
                    continue
                    
        except Exception as e:
            pass
    
    def handle_dropdown_questions(self, result: Dict[str, Any], seen_questions: set, new_questions: list):
        """Maneja preguntas de tipo dropdown/select"""
        try:
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            
            for select in selects:
                try:
                    select_id = select.get_attribute('id') or ''
                    aria_label = select.get_attribute('aria-label') or ''
                    
                    # Buscar label
                    label_text = ""
                    if select_id:
                        try:
                            label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{select_id}']")
                            label_text = label.text.lower()
                        except:
                            pass
                    
                    question_text = f"{label_text} {aria_label}".lower().strip()
                    
                    # Si ya vimos esta pregunta, skip
                    if question_text in seen_questions:
                        continue
                    
                    # Verificar si ya tiene un valor válido seleccionado
                    current_value = select.get_attribute('value')
                    if current_value and current_value not in ["Selecciona una opción", "Select an option", ""]:
                        self.logger.info(f"  ✓ Dropdown ya tiene valor: {current_value[:50]}")
                        seen_questions.add(question_text)
                        continue
                    
                    # Casos especiales: Email y teléfono de LinkedIn
                    from selenium.webdriver.support.ui import Select
                    select_obj = Select(select)
                    
                    if 'email' in question_text or 'correo' in question_text:
                        for option in select_obj.options[1:]:
                            if '@' in option.text:
                                select_obj.select_by_visible_text(option.text)
                                self.logger.info(f"  ✓ Email seleccionado: {option.text}")
                                seen_questions.add(question_text)
                                break
                        continue
                    
                    if 'phone' in question_text or 'teléfono' in question_text or 'telefono' in question_text:
                        for option in select_obj.options[1:]:
                            if any(char.isdigit() for char in option.text):
                                select_obj.select_by_visible_text(option.text)
                                self.logger.info(f"  ✓ Teléfono seleccionado: {option.text}")
                                seen_questions.add(question_text)
                                break
                        continue
                    
                    # Para otras preguntas, buscar respuesta configurada
                    answer = self.find_answer_for_question(question_text)
                    
                    if answer:
                        for option in select_obj.options:
                            if answer.lower() in option.text.lower():
                                select_obj.select_by_visible_text(option.text)
                                self.logger.info(f"  ✓ Seleccionado: {question_text[:50]}... → {option.text}")
                                seen_questions.add(question_text)
                                break
                    else:
                        # Pregunta sin respuesta - agregar solo si no está duplicada
                        if question_text and question_text not in seen_questions:
                            new_questions.append(question_text)
                            seen_questions.add(question_text)
                            result['questions_encountered'].append(question_text)
                            self.logger.warning(f"  ? Dropdown sin respuesta: {question_text[:50]}...")
                        
                except Exception as e:
                    self.logger.warning(f"  Error en dropdown: {str(e)}")
                    continue
                    
        except Exception as e:
            pass
    
    def find_answer_for_question(self, question_text: str) -> Optional[str]:
        """
        Busca una respuesta configurada para una pregunta
        
        Args:
            question_text: Texto de la pregunta
        
        Returns:
            Respuesta si se encuentra, None si no
        """
        import re
        
        preguntas_config = self.answers.get('preguntas_configuradas', {})
        
        for pregunta_key, pregunta_data in preguntas_config.items():
            # Obtener patrón de la pregunta
            if isinstance(pregunta_data, dict):
                patron = pregunta_data.get('pregunta_patron', '')
                patrones = pregunta_data.get('patrones', [patron]) if patron else pregunta_data.get('patrones', [])
            else:
                continue
            
            # Verificar si algún patrón coincide
            for patron in patrones:
                if re.search(patron, question_text, re.IGNORECASE):
                    # Obtener respuesta
                    if 'respuesta' in pregunta_data:
                        return pregunta_data['respuesta']
                    elif 'respuestas' in pregunta_data:
                        respuestas = pregunta_data['respuestas']
                        if isinstance(respuestas, dict):
                            return respuestas.get('corta') or respuestas.get('default') or list(respuestas.values())[0]
                        return str(respuestas)
                    break
        
        return None


def main():
    """Función principal de prueba"""
    from linkedin_scraper import LinkedInScraper
    
    print("🤖 LinkedIn Job Applier - Prueba")
    print("=" * 60)
    
    config = Config()
    logger = Logger()
    
    # Cargar credenciales
    credentials = config.get_linkedin_credentials()
    if not credentials:
        logger.error("No se pudieron cargar credenciales")
        return
    
    # ============================================================================
    # PASO 1: Cargar solo los NUEVOS trabajos del scraper
    # ============================================================================
    
    # Cargar todos los trabajos de jobs_found.json y filtrar solo los nuevos (is_new: true)
    jobs_file = Path("data/logs/jobs_found.json")
    if not jobs_file.exists():
        logger.info("No hay trabajos para aplicar (jobs_found.json no existe)")
        return
    
    with open(jobs_file, 'r', encoding='utf-8') as f:
        all_jobs = json.load(f)
    
    # Filtrar solo trabajos nuevos (is_new: true) con Easy Apply
    new_jobs = [job for job in all_jobs if job.get('is_new', False)]
    pending_jobs = [job for job in new_jobs if job.get('has_easy_apply')]
    
    logger.info(f"Trabajos NUEVOS pendientes de aplicar: {len(pending_jobs)}")
    
    if len(pending_jobs) == 0:
        logger.info("No hay trabajos nuevos con Easy Apply")
        return
    
    # Crear scraper (para reutilizar driver y login)
    scraper = LinkedInScraper(config, logger, headless=False)
    scraper.setup_driver()
    
    if not scraper.login(credentials['username'], credentials['password']):
        logger.error("Login fallido")
        return
    
    # Crear applier
    applier = LinkedInApplier(scraper.driver, config, logger)

    # Inicializar Telegram (si está disponible)
    notifier = None
    if TelegramNotifier:
        try:
            notifier = TelegramNotifier()
            logger.info('✓ Telegram notifier inicializado')
        except Exception as e:
            logger.warning(f'Telegram no configurado: {e}')
    
    # Inicializar Google Sheets para agregar resultados
    sheets_manager = None
    try:
        from google_sheets_manager import GoogleSheetsManager
        sheets_id = config.get_env_var('GOOGLE_SHEETS_ID')
        if sheets_id and Path('config/google_credentials.json').exists():
            sheets_manager = GoogleSheetsManager('config/google_credentials.json', sheets_id)
            logger.info('✓ Google Sheets manager inicializado')
    except Exception as e:
        logger.warning(f'Google Sheets no disponible: {e}')
    
    # ============================================================================
    # PASO 2: Aplicar solo a los trabajos nuevos
    # ============================================================================
    
    results = []
    for i, job in enumerate(pending_jobs):
        logger.info(f"\n--- Trabajo {i+1}/{len(pending_jobs)} ---")
        result = applier.apply_to_job(job)
        results.append(result)
        
        # Agregar a Google Sheets INMEDIATAMENTE (sin esperar a que termine todo)
        if sheets_manager:
            try:
                sheets_manager.add_job_application(job, result)
                logger.info('  ✓ Agregado a Google Sheets')
            except Exception as e:
                logger.warning(f'  ✗ Error agregando a Google Sheets: {e}')
        
        time.sleep(5)  # Delay entre aplicaciones
    
    # Mostrar resumen
    logger.info(f"\n{'='*60}")
    logger.info("RESUMEN DE APLICACIONES")
    logger.info(f"{'='*60}")
    
    successful = sum(1 for r in results if r.get('success'))
    logger.info(f"Exitosas: {successful}/{len(results)}")
    logger.info(f"Fallidas: {len(results) - successful}/{len(results)}")
    
    # Guardar resultados en archivo de logs
    results_file = Path("data/logs/application_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.success(f"Resultados guardados en: {results_file}")
    
    # Actualizar dashboard si está disponible
    if sheets_manager:
        try:
            sheets_manager.update_dashboard()
            logger.info('✓ Dashboard actualizado')
        except Exception as e:
            logger.warning(f'No se pudo actualizar dashboard: {e}')
    
    scraper.close()


if __name__ == "__main__":
    main()