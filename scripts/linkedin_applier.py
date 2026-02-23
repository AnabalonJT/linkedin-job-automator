#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn Job Applier
Aplica automáticamente a trabajos con Easy Apply
"""

import sys
import io

# Configurar UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Workaround para Python 3.12+ donde distutils fue removido
try:
    import setuptools
    import setuptools.distutils
    sys.modules['distutils'] = setuptools.distutils
except ImportError:
    pass

import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys

from utils import Config, Logger, select_cv_by_keywords
from ia_integration import IAIntegration

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
        
        # Inicializar IA
        self.ia = IAIntegration(logger, debug=False)
        if self.ia.enabled:
            self.logger.success("✓ IA integrada")
        else:
            self.logger.warning("⚠ Modo compatibilidad (sin IA)")
            # LOG DEBUG: por qué no está enabled
            if not hasattr(self, 'ia'):
                self.logger.warning("  - IAIntegration no inicializado")
            else:
                import os
                api_key = os.getenv('OPENROUTER_API_KEY')
                if not api_key:
                    self.logger.warning("  - OPENROUTER_API_KEY no configurada")
                else:
                    self.logger.warning(f"  - IA módulos no disponibles o error en inicialización")
    
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
            'job_description': '',  # Será llenado después de obtener la URL
            'success': False,
            'status': 'PENDING',  # PENDING, APPLIED, MANUAL, ERROR
            'error': None,
            'questions_encountered': [],
            'cv_used': None,
            'ia_classification': None,
            'ia_stats': None,
            'low_confidence_count': 0,  # Contador de respuestas con baja confianza
            'max_low_confidence': 3  # Máximo de respuestas baja confianza antes de abortar
        }
        
        try:
            # PASO 0: Ir a la página del trabajo PRIMERO para obtener descripción
            self.logger.info(f"  Cargando página del trabajo...")
            self.driver.get(job['url'])
            time.sleep(3)  # Esperar carga inicial
            
            # VERIFICAR: Detectar si LinkedIn está bloqueando/rate limiting
            try:
                # Buscar palabras clave de bloqueo
                page_text = self.driver.page_source.lower()
                if any(word in page_text for word in ['you\'ve visited linkedin too many', 'rate limiting', 'too many requests', 'try again later']):
                    self.logger.warning("⚠️  LinkedIn está rate limiting. Esperando 30 segundos...")
                    time.sleep(30)
            except:
                pass  # Si no puede chequear, continuar
            
            # Extraer descripción del trabajo de la página
            job_description = ''
            try:
                # ESPERAR a que cargue la sección "Acerca del empleo" (carga al final)
                self.logger.info("  ⏳ Esperando que cargue la descripción del trabajo...")
                time.sleep(3)  # Esperar a que cargue la sección completa
                
                # Estrategia MEJORADA: Buscar solo el contenido de "Acerca del empleo"
                try:
                    # PASO 1: Scroll hacia abajo para asegurar que la sección "Acerca del empleo" cargue
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(1)
                    
                    # PASO 2: Buscar y clickear el botón "mostrar más" si existe
                    try:
                        # Buscar botón con diferentes selectores
                        show_more_selectors = [
                            "button[data-testid='expandable-text-button']",  # Selector del HTML real
                            "button.show-more-less-html__button--more",
                            "button[aria-label*='mostrar más']",
                            "button[aria-label*='Show more']",
                            "button.show-more-less-html__button"
                        ]
                        
                        for selector in show_more_selectors:
                            try:
                                expand_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if expand_button.is_displayed():
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", expand_button)
                                    time.sleep(0.5)
                                    self.driver.execute_script("arguments[0].click();", expand_button)
                                    self.logger.info("  ✓ Botón 'mostrar más' clickeado")
                                    time.sleep(1.5)  # Esperar a que se expanda
                                    break
                            except:
                                continue
                    except:
                        pass  # Si no hay botón, continuar
                    
                    # PASO 3: Buscar el contenedor de descripción con el selector REAL
                    description_selectors = [
                        # Selector del HTML real
                        "span[data-testid='expandable-text-box']",
                        # Fallbacks
                        "div.show-more-less-html__markup",
                        "div.jobs-box__html-content div.show-more-less-html__markup",
                        "div.jobs-description__content div.show-more-less-html__markup"
                    ]
                    
                    for selector in description_selectors:
                        try:
                            desc_container = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if desc_container:
                                # Extraer solo el texto del contenedor
                                raw_text = desc_container.text.strip()
                                
                                self.logger.debug(f"  🔍 Selector '{selector}' encontró texto ({len(raw_text)} chars)")
                                
                                # LIMPIEZA: Remover líneas del header de LinkedIn si se colaron
                                lines = raw_text.split('\n')
                                cleaned_lines = []
                                skip_header = True
                                
                                for line in lines:
                                    line_lower = line.lower().strip()
                                    # Detectar inicio del contenido real (después del header)
                                    if skip_header:
                                        # Si la línea tiene contenido sustancial (no es metadata)
                                        if (len(line) > 80 or 
                                            any(word in line_lower for word in ['we are', 'we\'re', 'about', 'responsibilities', 'requirements', 'qualifications', 'experience', 'skills', 'description', 'acerca', 'somos', 'buscamos', 'who we are', 'what we offer'])):
                                            skip_header = False
                                            cleaned_lines.append(line)
                                        # Skip líneas de metadata
                                        elif any(word in line_lower for word in ['solicitudes', 'applications', 'hace', 'ago', 'promocionado', 'promoted', 'ya no se aceptan', 'no longer accepting']):
                                            continue
                                    else:
                                        cleaned_lines.append(line)
                                
                                job_description = '\n'.join(cleaned_lines).strip()
                                
                                if job_description and len(job_description) > 100:
                                    self.logger.info(f"  ✓ Descripción extraída con selector: {selector}")
                                    break
                                else:
                                    self.logger.debug(f"  ⚠️ Selector '{selector}' dio descripción muy corta ({len(job_description)} chars)")
                        except Exception as e:
                            self.logger.debug(f"  ⚠️ Selector '{selector}' falló: {str(e)}")
                            continue
                    
                except Exception as e:
                    self.logger.debug(f"  Error en extracción mejorada: {str(e)}")
                
                # Fallback: Buscar por h2 "Acerca del empleo" y extraer SOLO el contenido siguiente
                if not job_description or len(job_description) < 100:
                    try:
                        # Buscar el h2 "Acerca del empleo"
                        h2_headers = self.driver.find_elements(By.TAG_NAME, "h2")
                        for h2 in h2_headers:
                            h2_text = h2.text.strip()
                            if "Acerca del empleo" in h2_text or "About the job" in h2_text:
                                # Buscar el div hermano que contiene la descripción
                                try:
                                    parent = h2.find_element(By.XPATH, "..")
                                    desc_div = parent.find_element(By.CSS_SELECTOR, "div.show-more-less-html__markup")
                                    job_description = desc_div.text.strip()
                                    if len(job_description) > 100:
                                        self.logger.info(f"  ✓ Descripción extraída por h2 fallback")
                                        break
                                except:
                                    pass
                    except:
                        pass
                
            except Exception as e:
                self.logger.debug(f"  Error extrayendo descripción: {str(e)}")
            
            # Último fallback: usar descripción del scraper
            if not job_description or len(job_description) < 100:
                fallback = job.get('description', '')
                if fallback and len(fallback) > 100:
                    job_description = fallback
                    self.logger.info(f"  ✓ Usando descripción del scraper como fallback")
                else:
                    # Si no hay descripción, usar el título como contexto mínimo
                    job_description = f"Trabajo: {job.get('title', 'N/A')}"
                    self.logger.warning(f"  ⚠️ No se pudo extraer descripción, usando título como fallback")
            
            result['job_description'] = job_description
            
            # IMPORTANTE: Loguear la descripción COMPLETA para debugging
            self.logger.info(f"  📄 Descripción final ({len(job_description)} chars):")
            # Mostrar primeras 10 líneas para ver si el contenido es correcto
            lines = job_description.split('\n')
            for i, line in enumerate(lines[:10]):
                if line.strip():
                    self.logger.info(f"      L{i+1}: {line[:100]}")
            
            # DEBUG: Verificar si la descripción contiene metadata de LinkedIn
            if any(word in job_description.lower() for word in ['ya no se aceptan', 'solicitudes', 'promocionado', 'hace 1 día']):
                self.logger.warning(f"  ⚠️ ADVERTENCIA: La descripción parece contener metadata de LinkedIn")
            
            # PASO 1: Clasificar con IA (PRIORIDAD 1)
            if self.ia.enabled:
                job_requirements = job.get('requirements', '')
                
                # Si descripción sigue siendo vacía, usar el título como contexto
                if not job_description or job_description.strip() in ['N/A', 'NA', '']:
                    job_description = job.get('title', 'Software Developer')  # Fallback al título
                
                # DEBUG: Loguear lo que se envía a la IA
                self.logger.info(f"  🔍 Enviando a IA para clasificación:")
                self.logger.info(f"      Título: {job['title']}")
                self.logger.info(f"      Descripción (primeros 200 chars): {job_description[:200]}...")
                self.logger.info(f"      Requisitos: {job_requirements[:100] if job_requirements else 'N/A'}...")
                
                classification = self.ia.classify_job(
                    job_title=job['title'],
                    job_description=job_description,
                    job_requirements=job_requirements
                )
                
                result['ia_classification'] = classification
                
                # DEBUG: Loguear respuesta completa de IA
                if classification:
                    self.logger.info(f"  🤖 Respuesta IA completa:")
                    self.logger.info(f"      job_type: {classification.get('job_type', 'N/A')}")
                    self.logger.info(f"      match_percentage: {classification.get('match_percentage', 0)}%")
                    self.logger.info(f"      confidence: {classification.get('confidence', 0):.2f}")
                    self.logger.info(f"      recommended_cv: {classification.get('recommended_cv', 'N/A')}")
                    if classification.get('reasoning'):
                        self.logger.info(f"      reasoning: {classification.get('reasoning', '')[:150]}")
                
                # Usar recomendación de IA
                if classification and isinstance(classification, dict) and 'recommended_cv' in classification:
                    ia_cv = classification['recommended_cv']
                    confidence = classification.get('confidence', 0)
                    result['cv_used'] = ia_cv
                    self.logger.info(f"  ✅ IA recomienda: {ia_cv} (confianza: {confidence:.2f})")
                else:
                    # Fallback a keywords si IA falla
                    self.logger.warning(f"  ⚠️ IA no retornó recomendación válida, usando keywords como fallback")
                    keywords_cv = select_cv_by_keywords(
                        job.get('title', ''),
                        job_description,
                        self.config
                    )
                    result['cv_used'] = keywords_cv
                    self.logger.info(f"  🔑 Fallback keywords: {keywords_cv}")
            else:
                # Si IA no disponible, usar keywords
                self.logger.warning(f"  ⚠️ IA no disponible, usando keywords")
                keywords_cv = select_cv_by_keywords(
                    job.get('title', ''),
                    job_description,
                    self.config
                )
                result['cv_used'] = keywords_cv
                self.logger.info(f"  🔑 Keywords: {keywords_cv}")
            
            # ESPERAR 2 segundos para que cargue el botón "Solicitud sencilla"
            self.logger.info("  ⏳ Esperando 2s para que cargue el botón...")
            time.sleep(2)
            
            # Scroll para asegurar que el botón esté visible
            self.driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(0.5)
            
            # Buscar botón Easy Apply con múltiples selectores
            easy_apply_button = None
            selectors = [
                "button.jobs-apply-button",
                "button[aria-label*='Solicitud sencilla']",
                "button[aria-label*='Easy Apply']",
                "button#jobs-apply-button-id",
                "button[data-live-test-job-apply-button]",
                # Selectores adicionales basados en estructura HTML
                "div.jobs-apply-button--top-card button",
                "button[data-control-name='jobdetails_topcard_inapply']"
            ]
            
            # Intentar con cada selector (timeout: 3 seg)
            for selector in selectors:
                try:
                    easy_apply_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if easy_apply_button:
                        self.logger.info(f"  ✓ Botón 'Solicitud sencilla' encontrado con: {selector}")
                        break
                    easy_apply_button = None
                except:
                    continue
            
            # Si no encontró, intentar scroll y retry
            if not easy_apply_button:
                self.logger.info(f"  ⚠️  Reintentando con scroll...")
                self.driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(1)
                
                for selector in selectors[:3]:
                    try:
                        easy_apply_button = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if easy_apply_button:
                            self.logger.info(f"  ✓ Botón encontrado en reintento")
                            break
                    except:
                        continue
            
            try:
                # Scroll al botón
                if easy_apply_button and easy_apply_button.is_displayed():
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", easy_apply_button)
                    time.sleep(0.3)
                    easy_apply_button.click()
                    self.logger.info("  ✓ Click en Easy Apply realizado")
                    time.sleep(1.5)
                else:
                    raise Exception("Botón no encontrado")
                    
            except Exception as e:
                # Intentar click con JavaScript si falla el click normal
                self.logger.warning(f"  ⚠️ Intentando con JavaScript...")
                try:
                    # Estrategia: Buscar el botón por el span "Solicitud sencilla" y presionarlo
                    self.driver.execute_script("""
                        // Método 1: Buscar por span que contiene "Solicitud sencilla"
                        var spans = document.querySelectorAll('span');
                        for (var i = 0; i < spans.length; i++) {
                            if (spans[i].textContent.trim() === 'Solicitud sencilla') {
                                var link = spans[i].closest('a');
                                if (link) {
                                    link.click();
                                    console.log('Clicked via Solicitud sencilla span');
                                    return;
                                }
                            }
                        }
                        
                        // Método 2: Fallback a otros selectores
                        var btn = document.querySelector('button.jobs-apply-button') || 
                                 document.querySelector('[data-live-test-job-apply-button]') ||
                                 document.querySelector('button[aria-label*="Easy Apply"]') ||
                                 document.querySelector('a[aria-label*="Solicitud sencilla"]');
                        if (btn) {
                            btn.click();
                            console.log('Clicked via fallback selector');
                        }
                    """)
                    self.logger.info("  ✓ Easy Apply abierto con JavaScript")
                    
                    # ESPERAR EXPLÍCITAMENTE a que el modal cargue
                    # Buscar un elemento del formulario para verificar que está listo
                    self.logger.info("  ⏳ Esperando que cargue el modal...")
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input, textarea, select, button[type='button']"))
                        )
                        self.logger.info("  ✓ Modal detectado - formulario listo")
                    except:
                        self.logger.warning("  ⚠️ Modal tardó en cargar pero continuando...")
                    
                    time.sleep(1.5)
                except Exception as js_error:
                    self.logger.error(f"  ❌ No se pudo abrir Easy Apply")
                    result['error'] = "No se encontró botón Easy Apply"
                    result['status'] = 'MANUAL'  # Guardar como MANUAL para revisión
                    return result
            
            # VERIFICACIÓN CRÍTICA: Confirmar que hay un MODAL/formulario realmente abierto
            self.logger.info("  🔍 Verificando que el modal está ABIERTO...")
            
            # Estrategia NUEVA: Buscar elementos del formulario directamente en vez del modal
            try:
                # Esperar a que aparezcan elementos de formulario (más confiable que esperar el modal)
                form_elements_found = False
                
                # Intentar encontrar elementos típicos de un formulario de Easy Apply
                form_selectors = [
                    "input[type='text']",
                    "input[type='email']",
                    "select",
                    "textarea",
                    "button[aria-label*='Siguiente']",
                    "button[aria-label*='Next']",
                    "button[aria-label*='Revisar']",
                    "button[aria-label*='Review']"
                ]
                
                self.logger.info(f"  🔍 Buscando elementos de formulario...")
                time.sleep(2)  # Esperar a que el modal cargue completamente
                
                found_elements = []
                for selector in form_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            # Filtrar elementos visibles
                            visible_elements = [e for e in elements if e.is_displayed()]
                            if visible_elements:
                                found_elements.append(f"{selector} ({len(visible_elements)})")
                                form_elements_found = True
                    except:
                        continue
                
                if found_elements:
                    self.logger.info(f"  ✓ Elementos de formulario encontrados:")
                    for elem in found_elements:
                        self.logger.info(f"      - {elem}")
                else:
                    self.logger.warning(f"  ⚠️ No se encontraron elementos de formulario visibles")
                
                # Si no hay elementos de formulario, probablemente no hay modal
                if not form_elements_found:
                    # Intentar detectar mensajes de error o "ya postulado"
                    try:
                        page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                        if any(word in page_text for word in ['ya postulaste', 'already applied', 'no longer accepting', 'ya no se aceptan']):
                            self.logger.info("  💡 Detectado: Ya postulaste o el trabajo no acepta más aplicaciones")
                    except:
                        pass
                    
                    raise TimeoutException("No se encontraron elementos de formulario")
                
                self.logger.info(f"  ✓ Formulario confirmado - continuando con aplicación")
                
            except TimeoutException as e:
                # No hay modal visible - probablemente no acepta aplicaciones o ya se postuló
                self.logger.warning(f"  ❌ No se abrió el modal de aplicación")
                self.logger.info("  💡 El trabajo no acepta más aplicaciones o ya te has postulado")
                result['error'] = "Modal no se abrió - trabajo no acepta aplicaciones"
                result['status'] = 'MANUAL'
                return result
            
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
        
        # Intentar detectar modal con timeout MUY CORTO (1 seg total)
        try:
            WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog'], .artdeco-modal, form"))
            )
        except:
            pass  # No preocuparse si no se detecta el modal
        
        time.sleep(0.3)
        
        while current_step < max_steps:
            current_step += 1
            self.logger.info(f"  Paso {current_step}...")
            
            time.sleep(0.5)
            
            # Rellenar formulario actual ANTES de buscar botón
            new_questions = self.fill_current_form_step(job, result, seen_questions)
            questions_without_answer.extend(new_questions)
            
            # Si hay más de 3 preguntas sin respuesta, abortar
            if len(questions_without_answer) > 3:
                self.logger.warning(f"  ✗ Demasiadas preguntas sin respuesta ({len(questions_without_answer)}). Marcando como MANUAL.")
                result['error'] = f"Requiere {len(questions_without_answer)} respuestas manuales"
                result['status'] = 'MANUAL'
                return False
            
            time.sleep(0.5)
            
            # Scroll dentro del modal para asegurar que el botón esté visible
            try:
                # Intentar scroll en el body (el modal puede no tener scroll propio)
                self.driver.execute_script("window.scrollBy(0, 200);")
            except:
                pass
            
            # Buscar botón de acción usando selectores SIMPLES del código viejo
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
                "button.artdeco-button--primary",
                # Agregar selector específico del HTML real
                "button[aria-label*='Ir al siguiente paso']"
            ]
            
            for selector in button_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        # Verificar que NO sea el botón "Descartar" o "Volver"
                        btn_aria = (btn.get_attribute('aria-label') or '').lower()
                        btn_text = (btn.text or '').lower()
                        
                        # Ignorar botones de cancelar/volver
                        if any(word in f"{btn_aria} {btn_text}" for word in ['descartar', 'dismiss', 'volver', 'back', 'cancel', 'cerrar', 'close']):
                            continue
                        
                        if btn.is_displayed() and btn.is_enabled():
                            next_button = btn
                            self.logger.info(f"  ✓ Botón encontrado con selector: {selector}")
                            break
                    if next_button:
                        break
                except NoSuchElementException:
                    continue
            
            # Fallback: Buscar TODOS los botones y filtrar manualmente
            if not next_button:
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    self.logger.info(f"  🔍 Fallback: Encontrados {len(buttons)} botones totales")
                    
                    # DEBUG: Mostrar TODOS los botones para entender por qué no coinciden
                    visible_buttons = []
                    for button in buttons:
                        try:
                            if button.is_displayed() and button.is_enabled():
                                button_text = (button.text or '').strip()
                                button_aria = (button.get_attribute('aria-label') or '').strip()
                                visible_buttons.append(f"'{button_text}' / aria='{button_aria}'")
                        except:
                            continue
                    
                    if visible_buttons:
                        self.logger.info(f"  📋 Botones visibles:")
                        for i, btn_info in enumerate(visible_buttons[:10], 1):  # Mostrar primeros 10
                            self.logger.info(f"      {i}. {btn_info}")
                    
                    for button in buttons:
                        try:
                            # Verificar que el botón está visible y habilitado
                            if not button.is_displayed() or not button.is_enabled():
                                continue
                            
                            # Obtener texto y aria-label
                            button_text = (button.text or '').lower().strip()
                            button_aria = (button.get_attribute('aria-label') or '').lower().strip()
                            combined = f"{button_text} {button_aria}"
                            
                            # Palabras clave para botones de acción
                            action_keywords = ['siguiente', 'next', 'revisar', 'review', 'enviar', 'submit', 'continuar', 'continue', 'ir al siguiente']
                            
                            # Palabras clave para botones a ignorar
                            ignore_keywords = ['volver', 'back', 'cancel', 'cancelar', 'cerrar', 'close', 'descartar', 'dismiss']
                            
                            # Verificar si es un botón de acción
                            has_action = any(keyword in combined for keyword in action_keywords)
                            has_ignore = any(keyword in combined for keyword in ignore_keywords)
                            
                            if has_action and not has_ignore:
                                next_button = button
                                self.logger.info(f"  ✓ Botón encontrado (fallback): '{button_text or button_aria}'")
                                break
                        except:
                            continue
                    
                except Exception as e:
                    self.logger.warning(f"  ⚠️ Error buscando botón: {str(e)}")
            
            if not next_button:
                self.logger.warning("  ❌ No se encontró botón de acción en el modal")
                return False
            
            button_aria_label = next_button.get_attribute('aria-label') or ''
            button_text = next_button.text or button_aria_label
            
            self.logger.info(f"  🔘 Botón encontrado: '{button_text}' (aria={button_aria_label})")
            
            # IMPORTANTE: Detectar botón "Enviar" ANTES de hacer click
            button_context = f"{button_text} {button_aria_label}".lower()
            is_submit_button = any(word in button_context for word in ['enviar', 'submit', 'send application'])
            
            if is_submit_button:
                self.logger.info(f"  ✓ Este es el botón final (Enviar/Submit)")
            
            # Detectar loop infinito
            button_history.append(button_aria_label)
            if len(button_history) > 3:
                # Si los últimos 3 botones son iguales, estamos en loop
                if button_history[-1] == button_history[-2] == button_history[-3]:
                    self.logger.warning(f"  ✗ Detectado loop infinito (mismo botón '{button_text}' 3+ veces)")
                    result['error'] = "Loop infinito detectado - formulario bloqueado"
                    result['status'] = 'MANUAL'
                    return False
            
            # Click en el botón
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(0.3)
                next_button.click()
                self.logger.info(f"  ✓ Click en '{button_text}'")
            except Exception as e:
                self.driver.execute_script("arguments[0].click();", next_button)
                self.logger.info(f"  ✓ Click en '{button_text}' (JavaScript)")
            
            time.sleep(0.5)
            
            # Si era botón "Enviar", aplicación completa
            if is_submit_button:
                # Esperar confirmación
                time.sleep(1)
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
            
            # 2. Buscar y responder INPUT TEXT fields (preguntas de texto abiertas)
            # IMPORTANTE: Hacer esto ANTES de rellenar textareas porque algunos inputs son preguntas
            input_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            if input_fields:
                self.logger.info(f"  🔍 Encontrados {len(input_fields)} campos input[type='text']")
                
                # Contar cuántos ya están rellenados
                filled_count = 0
                for field in input_fields:
                    value = field.get_attribute('value') or ''
                    if value.strip():
                        filled_count += 1
                
                if filled_count > 0:
                    self.logger.info(f"  ℹ️  {filled_count}/{len(input_fields)} campos ya tienen valor (saltando)")
            
            for field in input_fields:
                self.handle_text_question(field, result, seen_questions, new_questions)
            
            # 3. Buscar y rellenar campos de texto genéricos (email, teléfono, ciudad)
            # Solo campos que NO son preguntas
            generic_text_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[type='tel']")
            if generic_text_fields:
                self.logger.info(f"  📧 Encontrados {len(generic_text_fields)} campos email/tel")
            for field in generic_text_fields:
                self.fill_text_field(field, result)
            
            # 4. Buscar y rellenar textareas (incluyendo preguntas abiertas)
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            if textareas:
                self.logger.info(f"  📝 Encontrados {len(textareas)} textareas")
            for textarea in textareas:
                # Intentar rellenar como pregunta abierta primero
                question_handled = self.handle_open_question(textarea, result, seen_questions, new_questions)
                if not question_handled:
                    # Si no es pregunta, intentar como campo de presentación
                    self.fill_textarea(textarea, result)
            
            # 5. Buscar y responder preguntas de radio/checkbox
            self.handle_radio_questions(result, seen_questions, new_questions)
            
            # 6. Buscar y responder dropdowns
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
            
            # IMPORTANTE: Verificar si el campo YA tiene valor
            current_value = field.get_attribute('value') or ''
            if current_value and current_value.strip():
                self.logger.debug(f"  ℹ Campo ya tiene valor: {current_value[:30]}, saltando...")
                return  # No sobrescribir campos ya rellenados
            
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
            
            # Determinar qué llenar
            personal_info = self.answers.get('informacion_personal', {})
            
            if any(word in field_context for word in ['email', 'correo', 'e-mail']):
                email = personal_info.get('email', '')
                if email:
                    field.send_keys(email)
                    self.logger.info(f"  ✓ Email ingresado: {email}")
            
            elif any(word in field_context for word in ['phone', 'teléfono', 'telefono', 'celular', 'mobile']):
                phone = personal_info.get('telefono', '')
                if phone:
                    field.send_keys(phone)
                    self.logger.info(f"  ✓ Teléfono ingresado: {phone}")
            
            elif any(word in field_context for word in ['linkedin', 'linkedin url']):
                linkedin_url = personal_info.get('linkedin_url', '')
                if linkedin_url:
                    field.send_keys(linkedin_url)
                    self.logger.info(f"  ✓ LinkedIn URL ingresado")
            
            elif any(word in field_context for word in ['city', 'ciudad', 'location', 'ubicación']):
                city = personal_info.get('ciudad', '')
                if city:
                    field.send_keys(city)
                    self.logger.info(f"  ✓ Ciudad ingresada: {city}")
            
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
    
    def detect_input_type(self, text_input) -> str:
        """
        Detecta qué tipo de entrada espera el input analizando sus atributos HTML
        
        Returns:
            "number", "date", "email", "tel", "url", "text", etc.
        """
        # 1. Check explicit type attribute (aunque sea text, otros atributos pueden especificar)
        input_type = text_input.get_attribute('type') or ''
        if input_type in ['number', 'date', 'email', 'tel', 'url']:
            return input_type
        
        # 2. Check inputmode attribute (HTML5 standard)
        inputmode = text_input.get_attribute('inputmode') or ''
        if inputmode:
            return inputmode
        
        # 3. Check pattern regex (puede indicar números, fechas, etc.)
        pattern = text_input.get_attribute('pattern') or ''
        if pattern:
            if r'\d' in pattern or 'number' in pattern.lower():
                return 'number'
            if 'date' in pattern.lower():
                return 'date'
            if r'\d{1,2}' in pattern or r'\d{2}' in pattern:  # Fecha dd/mm
                return 'date'
        
        # 4. Check placeholder text for clues
        placeholder = text_input.get_attribute('placeholder') or ''
        placeholder_lower = placeholder.lower()
        if any(word in placeholder_lower for word in ['años', 'year', 'edad', 'age', 'número', 'number', 'count', 'cantidad']):
            return 'number'
        if any(word in placeholder_lower for word in ['fecha', 'date', 'día', 'day', '/20', 'dd/mm']):
            return 'date'
        if any(word in placeholder_lower for word in ['email', 'correo', '@']):
            return 'email'
        if any(word in placeholder_lower for word in ['teléfono', 'phone']):
            return 'tel'
        
        # 5. Check aria-label
        aria_label = text_input.get_attribute('aria-label') or ''
        aria_label_lower = aria_label.lower()
        if any(word in aria_label_lower for word in ['años', 'years', 'número', 'number']):
            return 'number'
        if any(word in aria_label_lower for word in ['fecha', 'date']):
            return 'date'
        
        # Default: text
        return 'text'
    
    def handle_text_question(self, text_input, result: Dict[str, Any], seen_questions: set, new_questions: list) -> bool:
        """
        Maneja preguntas en inputs type="text" con label asociado
        
        Args:
            text_input: Elemento input[type="text"] del formulario
            result: Diccionario de resultado
            seen_questions: Set de preguntas ya vistas
            new_questions: Lista de preguntas sin respuesta
        
        Returns:
            True si se procesó como pregunta, False si no
        """
        try:
            # Obtener información de identificación del input
            input_id = text_input.get_attribute('id') or ''
            placeholder = text_input.get_attribute('placeholder') or ''
            aria_label = text_input.get_attribute('aria-label') or ''
            name = text_input.get_attribute('name') or ''
            input_class = text_input.get_attribute('class') or ''
            
            # Buscar label asociado usando "for" attribute
            label_text = ""
            if input_id:
                try:
                    label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
                    label_text = label.text.strip()
                except NoSuchElementException:
                    pass
            
            # Fallback: buscar label en el contenedor padre también
            if not label_text and input_id:
                try:
                    # A veces el label está en un div padre con clase especial
                    parent = text_input.find_element(By.XPATH, "./ancestor::*[contains(@class, 'artdeco-text-input')]")
                    label_elem = parent.find_element(By.TAG_NAME, "label")
                    if label_elem:
                        label_text = label_elem.text.strip()
                except:
                    pass
            
            # Fallback: si no hay label, usar placeholder o aria-label
            question_text = label_text or placeholder or aria_label
            question_text = question_text.strip()
            
            if not question_text or len(question_text) < 5:
                self.logger.debug(f"     ℹ Input descartado: no es pregunta válida (len={len(question_text)})")
                return False  # No es una pregunta válida
            
            # Ignorar campos de entrada genéricos COMUNES (email, teléfono, URL, búsquedas, etc.)
            invalid_patterns = [
                'email', 'correo', 'teléfono', 'phone', 'url', 'website', 'linkedin', 'github',
                'buscar', 'search', 'filtro', 'filter', 'usuario', 'username', 'user',
                'contraseña', 'password', 'confirm', 'confirmación'
            ]
            question_lower = question_text.lower()
            if any(pattern in question_lower for pattern in invalid_patterns):
                return False
            
            # Si ya vimos esta pregunta, skip (evitar duplicados)
            if question_lower in seen_questions:
                return True
            
            self.logger.info(f"  ❓ Pregunta de Texto: {question_text}")
            seen_questions.add(question_lower)
            
            # Ver si el input ya tiene valor
            current_value = text_input.get_attribute('value') or ''
            if current_value and current_value.strip():
                self.logger.info(f"     ✓ Ya tiene valor: {current_value[:50]}")
                return True
            
            # DETECTAR TIPO DE INPUT ESPERADO
            expected_type = self.detect_input_type(text_input)
            if expected_type != 'text':
                self.logger.info(f"     📝 Tipo detectado: {expected_type}")
            
            # Intentar responder con IA
            ia_answer = None
            ia_confidence = 0
            
            if self.ia.enabled:
                self.logger.info(f"     🔄 Consultando IA...")
                ia_result = self.ia.answer_question(
                    question_text=question_text,
                    question_type=f"text_input_{expected_type}",  # Pasar tipo esperado a IA
                    options=None,
                    previous_answers=result.get('answers_log', {})
                )
                
                ia_answer = ia_result.get('answer', '')
                ia_confidence = ia_result.get('confidence', 0)
                
                status = '✅ AUTO' if ia_confidence >= 0.85 else ('⚠️ MANUAL' if ia_confidence >= 0.65 else '❌ FALLBACK')
                self.logger.info(f"     🤖 IA RESPUESTA: '{ia_answer}' [Confianza: {ia_confidence:.0%}] - {status}")
                
                # VERIFICAR: ¿la respuesta IA es inútil?
                if ia_answer and "información no disponible" in ia_answer.lower():
                    result['low_confidence_count'] += 1
                    self.logger.warning(f"     ⚠️  RESPUESTA INÚTIL detectada ({result['low_confidence_count']}/{result['max_low_confidence']})")
                    
                    if result['low_confidence_count'] >= result['max_low_confidence']:
                        self.logger.warning(f"     🛑 LIMITE DE BAJA CONFIANZA ALCANZADO - Abortando aplicación")
                        result['status'] = 'MANUAL'
                        result['abort_reason'] = 'Low confidence answers exceeded limit'
                        return True  # Retornar para evitar rellenar
                
                # THRESHOLD: Si confianza < 0.65, marcar como MANUAL
                if ia_confidence < 0.65:
                    self.logger.warning(f"     ⚠️  Confianza baja ({ia_confidence:.2f}) - Marcando como MANUAL")
                    result['status'] = 'MANUAL'
                    if 'manual_questions' not in result:
                        result['manual_questions'] = []
                    result['manual_questions'].append({
                        'question': question_text,
                        'ia_answer': ia_answer,
                        'confidence': ia_confidence,
                        'reason': 'Below 0.65 threshold'
                    })
                    new_questions.append({
                        'type': 'text',
                        'question': question_text,
                        'confidence': ia_confidence
                    })
                    return True  # No rellenar

            
            # Decidir si rellenar el campo
            if ia_answer and ia_confidence > 0:
                self.logger.info(f"     ↪️ Rellenando input...")
                
                # Validación especial: preguntas sobre años
                if any(p in question_lower for p in ['years', 'años', 'cuanto tiempo', 'how long']):
                    try:
                        # Intentar convertir a número
                        num_value = float(str(ia_answer).replace('years', '').replace('años', '').replace('experience with', '').strip())
                        # Redondear a número entero si pregunta años
                        num_value = int(round(num_value))
                        if num_value < 0:
                            num_value = 0
                        ia_answer = str(num_value)
                        self.logger.info(f"     🔢 Convertido a número entero: {ia_answer}")
                    except (ValueError, TypeError):
                        pass  # Si no puede convertir, usar respuesta original
                
                # Retry logic para elementos obstinados
                for retry in range(3):
                    try:
                        text_input = self.driver.find_element(By.CSS_SELECTOR, f"input[id='{input_id}']") if input_id else text_input
                        text_input.clear()
                        text_input.send_keys(ia_answer)
                        
                        # Verificar que se escribió
                        filled_value = text_input.get_attribute('value')
                        if filled_value:
                            self.logger.info(f"     ✓ Rellenado: {ia_answer[:50]}")
                            # Guardar en answers_log
                            if 'answers_log' not in result:
                                result['answers_log'] = {}
                            result['answers_log'][question_text] = ia_answer
                            return True
                    except StaleElementReferenceException:
                        if retry < 2:
                            time.sleep(0.3)
                            continue
                
                return True
            else:
                self.logger.info(f"     ⚠️ No hay respuesta válida de IA")
                new_questions.append({
                    'type': 'text',
                    'question': question_text,
                    'confidence': ia_confidence
                })
                return True
            
        except Exception as e:
            self.logger.debug(f"     Error procesando input text: {str(e)}")
            return False
    
    def handle_open_question(self, textarea, result: Dict[str, Any], seen_questions: set, new_questions: list) -> bool:
        """
        Maneja preguntas abiertas en textareas
        
        Args:
            textarea: Elemento textarea del formulario
            result: Diccionario de resultado
            seen_questions: Set de preguntas ya vistas
            new_questions: Lista de preguntas sin respuesta
        
        Returns:
            True si se procesó como pregunta, False si no
        """
        try:
            # Obtener información de identificación
            aria_label = textarea.get_attribute('aria-label') or ''
            placeholder = textarea.get_attribute('placeholder') or ''
            name = textarea.get_attribute('name') or ''
            id_attr = textarea.get_attribute('id') or ''
            
            # Buscar label asociado
            label_text = ""
            try:
                if id_attr:
                    label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{id_attr}']")
                    label_text = label.text
                elif aria_label:
                    label_text = aria_label
            except NoSuchElementException:
                pass
            
            # Construir contexto de pregunta
            question_text = (label_text or placeholder or aria_label or "").strip()
            
            if not question_text:
                return False  # No es una pregunta
            
            # Ignorar textareas que son claramente campos estándar (cover letter, etc.)
            ignore_patterns = ['carta', 'cover letter', 'presentación', 'motivación', 'why', 'por qué']
            if any(pattern in question_text.lower() for pattern in ignore_patterns):
                return False
            
            question_lower = question_text.lower()
            
            # Si ya vimos esta pregunta, skip
            if question_lower in seen_questions:
                return True
            
            self.logger.info(f"  ❓ Pregunta Abierta: {question_text}")
            
            # Ver si ya tiene respuesta
            current_value = textarea.get_attribute('value') or ''
            if current_value:
                self.logger.info(f"     ✓ Ya tiene valor: {current_value[:50]}")
                seen_questions.add(question_lower)
                return True
            
            # Intentar responder con IA
            ia_answer = None
            ia_confidence = 0
            ia_reasoning = ""
            auto_submit = False
            
            if self.ia.enabled:
                self.logger.info(f"     🔄 Consultando IA...")
                ia_result = self.ia.answer_question(
                    question_text=question_text,
                    question_type="text",
                    options=None,
                    previous_answers=result.get('answers_log', {})
                )
                
                ia_answer = ia_result.get('answer', '')
                ia_confidence = ia_result.get('confidence', 0)
                ia_reasoning = ia_result.get('reasoning', '')
                auto_submit = ia_result.get('auto_submit', False)
                sources = ia_result.get('sources', [])
                
                # Logging detallado
                status = '✅ AUTO-SUBMIT' if auto_submit else '⚠️ MANUAL REVIEW'
                self.logger.info(f"     🤖 IA RESPUESTA: '{ia_answer}' [Confianza: {ia_confidence:.0%}] - {status}")
                if ia_reasoning:
                    self.logger.info(f"     💭 Razonamiento: {ia_reasoning}")
                if sources:
                    self.logger.info(f"     📚 Fuentes: {', '.join(sources)}")
            else:
                self.logger.info(f"     ⚠️  IA deshabilitado, buscando en configuración")
            
            # Estrategia de respuesta
            answer = None
            answer_source = None
            
            # VERIFICAR: ¿la respuesta IA es inútil?
            if ia_answer and "información no disponible" in ia_answer.lower():
                result['low_confidence_count'] += 1
                self.logger.warning(f"     ⚠️  RESPUESTA INÚTIL detectada ({result['low_confidence_count']}/{result['max_low_confidence']})")
                
                if result['low_confidence_count'] >= result['max_low_confidence']:
                    self.logger.warning(f"     🛑 LIMITE DE BAJA CONFIANZA ALCANZADO - Abortando aplicación")
                    result['status'] = 'MANUAL'
                    result['abort_reason'] = 'Low confidence answers exceeded limit'
                    new_questions.append(question_text)
                    seen_questions.add(question_lower)
                    return True
            
            # 1. IA con confianza alta
            if auto_submit and ia_answer:
                answer = ia_answer
                answer_source = "IA (Auto)"
            
            # 2. Buscar en configuración
            if not answer:
                answer = self.find_answer_for_question(question_text)
                answer_source = "Config" if answer else None
            
            # 3. Usar respuesta genérica si existe
            if not answer:
                # Buscar por palabras clave comunes
                if any(word in question_lower for word in ['salary', 'salario', 'renta', 'expectativa', 'pretensión']):
                    preguntas_config = self.answers.get('preguntas_configuradas', {})
                    salary_config = preguntas_config.get('expectativa_salario', {})
                    answer = salary_config.get('respuesta', salary_config.get('respuesta_corta'))
                    answer_source = "Config_Salary"
            
            if answer:
                try:
                    textarea.send_keys(answer)
                    time.sleep(0.5)  # Wait for DOM to process
                    self.logger.info(f"     ✅ Respondido [{answer_source}]: {answer[:50]}...")
                    
                    if 'answers_log' not in result:
                        result['answers_log'] = {}
                    result['answers_log'][question_text] = {
                        'answer': answer,
                        'source': answer_source,
                        'ia_confidence': ia_confidence,
                        'ia_auto': auto_submit
                    }
                    seen_questions.add(question_lower)
                    return True
                    
                except StaleElementReferenceException:
                    self.logger.warning(f"     ⚠️  Stale element - re-buscando textarea...")
                    time.sleep(1)
                    try:
                        # Re-buscar el textarea
                        new_textarea = self.driver.find_element(By.CSS_SELECTOR, f"textarea[id='{id_attr}']") if id_attr else None
                        if new_textarea:
                            new_textarea.send_keys(answer)
                            self.logger.info(f"     ✅ Respondido (reintento): {answer[:50]}...")
                            seen_questions.add(question_lower)
                            return True
                    except:
                        pass
                    
                except Exception as e:
                    self.logger.warning(f"     ❌ Error escribiendo respuesta: {str(e)}")
                    return False
            else:
                self.logger.warning(f"     ❌ Sin respuesta disponible")
                new_questions.append(question_text)
                seen_questions.add(question_lower)
                return True  # Retornar True para no procesar como cover letter
            
        except Exception as e:
            self.logger.info(f"  Error en handle_open_question: {e}")
            return False
    
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
                    
                    # Obtener opciones disponibles
                    radios = group.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    options = []
                    for radio in radios:
                        try:
                            label = radio.find_element(By.XPATH, "./following-sibling::label")
                            options.append(label.text)
                        except:
                            pass
                    
                    if not options:
                        continue
                    
                    # Intentar responder con IA primero si está disponible
                    ia_answer = None
                    ia_confidence = 0
                    ia_reasoning = ""
                    auto_submit = False
                    
                    self.logger.info(f"  ❓ Radio Question: {question_text}")
                    self.logger.info(f"     Opciones: {', '.join(options)}")
                    
                    if self.ia.enabled:
                        # Preguntar a IA
                        self.logger.info(f"     🔄 Consultando IA...")
                        ia_result = self.ia.answer_question(
                            question_text=question_text,
                            question_type="choice",
                            options=options,
                            previous_answers=result.get('answers_log', {})
                        )
                        
                        ia_answer = ia_result.get('answer', '')
                        ia_confidence = ia_result.get('confidence', 0)
                        ia_reasoning = ia_result.get('reasoning', '')
                        auto_submit = ia_result.get('auto_submit', False)
                        sources = ia_result.get('sources', [])
                        cv_context = ia_result.get('cv_context_used', '')
                        
                        # Logging detallado de respuesta IA
                        status = '✅ AUTO-SUBMIT' if auto_submit else '⚠️ MANUAL REVIEW'
                        self.logger.info(f"     🤖 IA RESPUESTA: '{ia_answer}' [Confianza: {ia_confidence:.0%}] - {status}")
                        if ia_reasoning:
                            self.logger.info(f"     💭 Razonamiento: {ia_reasoning}")
                        if sources:
                            self.logger.info(f"     📚 Fuentes: {', '.join(sources)}")
                        
                        # VALIDAR: ¿la respuesta IA está en las opciones disponibles?
                        ia_answer_valid = False
                        if ia_answer:
                            for option_text in options:
                                if ia_answer.lower() in option_text.lower():
                                    ia_answer_valid = True
                                    break
                        
                        if not ia_answer_valid and ia_answer:
                            self.logger.warning(f"     ❌ Respuesta IA '{ia_answer}' NO está en opciones")
                            
                            # VERIFICAR: ¿Es respuesta "Información no disponible"?
                            if "información no disponible" in ia_answer.lower() or "no disponible" in ia_answer.lower():
                                result['low_confidence_count'] += 1
                                self.logger.warning(f"     ⚠️  RESPUESTA INÚTIL detectada ({result['low_confidence_count']}/{result['max_low_confidence']})")
                                
                                # Si alcanzamos el límite, abortar la aplicación
                                if result['low_confidence_count'] >= result['max_low_confidence']:
                                    self.logger.warning(f"     🛑 LIMITE DE BAJA CONFIANZA ALCANZADO - Abortando aplicación")
                                    result['status'] = 'MANUAL'
                                    result['abort_reason'] = 'Low confidence answers exceeded limit'
                                    return  # Salir del método para evitar más procesamiento
                            
                            # Fallback: si confianza < 85%, intentar respuesta genérica "No"
                            # (Mejor responder una opción que dejar vacío y causar loop)
                            if ia_confidence < 0.85:
                                for option_text in options:
                                    if option_text.lower() in ['no', 'nein', 'non', 'non disponible']:
                                        ia_answer = option_text
                                        ia_answer_valid = True
                                        self.logger.info(f"     💡 Fallback a respuesta genérica: {ia_answer}")
                                        auto_submit = False  # Marcar como manual por confianza baja
                                        break
                            if not ia_answer_valid:
                                ia_answer = ""  # Rechazar solo si no hay fallback
                        
                        # THRESHOLD: Si confianza < 0.65, marcar como MANUAL
                        if ia_answer_valid and ia_confidence < 0.65:
                            self.logger.warning(f"     ⚠️  Confianza baja ({ia_confidence:.2f}) - Marcando como MANUAL")
                            result['status'] = 'MANUAL'
                            if 'manual_questions' not in result:
                                result['manual_questions'] = []
                            result['manual_questions'].append({
                                'question': question_text,
                                'ia_answer': ia_answer,
                                'confidence': ia_confidence,
                                'reason': 'Below 0.65 threshold'
                            })
                            new_questions.append(question_text)
                            seen_questions.add(question_text)
                            continue  # Saltar esta pregunta
                    else:
                        self.logger.info(f"     ⚠️  IA deshabilitado, buscando en configuración")
                    
                    # Estrategia de respuesta por prioridad
                    answer = None
                    answer_source = None
                    
                    # 1. IA con respuesta válida (después de validar contra opciones)
                    if ia_answer:
                        answer = ia_answer
                        # Determinar fuente según confianza
                        if auto_submit and ia_confidence >= 0.85:
                            answer_source = "IA (Auto)"
                        elif ia_confidence >= 0.60:  # Confianza moderada
                            answer_source = "IA (Manual)"
                        else:  # Fallback genérico pero mejor que vacío
                            answer_source = "IA (Fallback)"
                    
                    # 2. Buscar en configuración si IA no respondió
                    if not answer:
                        answer = self.find_answer_for_question(question_text)
                        answer_source = "Config" if answer else None
                    
                    if answer:
                        radios = group.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        found = False
                        for radio in radios:
                            try:
                                label = radio.find_element(By.XPATH, "./following-sibling::label")
                                if answer.lower() in label.text.lower():
                                    radio.click()
                                    time.sleep(0.5)  # Esperar a que se procese el click
                                    self.logger.info(f"     ✅ Respondido [{answer_source}]: {answer}")
                                    
                                    # Agregar a log de respuestas
                                    if 'answers_log' not in result:
                                        result['answers_log'] = {}
                                    result['answers_log'][question_text] = {
                                        'answer': answer,
                                        'source': answer_source,
                                        'ia_confidence': ia_confidence,
                                        'ia_auto': auto_submit
                                    }
                                    
                                    seen_questions.add(question_text)
                                    found = True
                                    break
                            except:
                                pass
                        
                        if not found:
                            self.logger.warning(f"     ✗ Respuesta '{answer}' no encontrada en opciones")
                    else:
                        if question_text and question_text not in seen_questions:
                            new_questions.append(question_text)
                            seen_questions.add(question_text)
                            result['questions_encountered'].append(question_text)
                            self.logger.warning(f"     ❌ Sin respuesta disponible")
                        
                except Exception as e:
                    self.logger.info(f"  Error procesando radio group: {e}")
                    continue
                    
        except Exception as e:
            self.logger.info(f"  Error en handle_radio_questions: {e}")
    
    def handle_dropdown_questions(self, result: Dict[str, Any], seen_questions: set, new_questions: list):
        """Maneja preguntas de tipo dropdown/select"""
        try:
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            
            for select in selects:
                try:
                    select_id = select.get_attribute('id') or ''
                    aria_label = select.get_attribute('aria-label') or ''
                    
                    # IMPORTANTE: Ignorar el dropdown de idioma de LinkedIn (NO es parte del formulario)
                    if 'language' in select_id.lower() or 'idioma' in select_id.lower():
                        self.logger.debug(f"  ⏭️  Ignorando dropdown de idioma de LinkedIn")
                        continue
                    
                    # Verificar si el select tiene valor "es_ES" o similar (indicador de dropdown de idioma)
                    current_value = select.get_attribute('value') or ''
                    if current_value in ['es_ES', 'en_US', 'pt_BR', 'fr_FR', 'de_DE']:
                        self.logger.debug(f"  ⏭️  Ignorando dropdown de idioma (valor: {current_value})")
                        continue
                    
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
                    
                    # Marcar como visto INMEDIATAMENTE para evitar duplicados
                    # (aunque falle la respuesta, no queremos procesarla de nuevo)
                    seen_questions.add(question_text)
                    
                    # Verificar si ya tiene un valor válido seleccionado
                    if current_value and current_value not in ["Selecciona una opción", "Select an option", "", "Select an option"]:
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
                    
                    # Obtener opciones disponibles
                    options = [opt.text for opt in select_obj.options[1:]]
                    
                    self.logger.info(f"  ❓ Dropdown Question: {question_text}")
                    self.logger.info(f"     Opciones: {', '.join(options[:5])}" + ("..." if len(options) > 5 else ""))
                    
                    # Intentar responder con IA primero si está disponible
                    ia_answer = None
                    ia_confidence = 0
                    ia_reasoning = ""
                    auto_submit = False
                    
                    if self.ia.enabled:
                        # Preguntar a IA
                        self.logger.info(f"     🔄 Consultando IA...")
                        ia_result = self.ia.answer_question(
                            question_text=question_text,
                            question_type="dropdown",
                            options=options,
                            previous_answers=result.get('answers_log', {})
                        )
                        
                        ia_answer = ia_result.get('answer', '')
                        ia_confidence = ia_result.get('confidence', 0)
                        ia_reasoning = ia_result.get('reasoning', '')
                        auto_submit = ia_result.get('auto_submit', False)
                        sources = ia_result.get('sources', [])
                        
                        # Logging detallado de respuesta IA
                        status = '✅ AUTO-SUBMIT' if auto_submit else '⚠️ MANUAL REVIEW'
                        self.logger.info(f"     🤖 IA RESPUESTA: '{ia_answer}' [Confianza: {ia_confidence:.0%}] - {status}")
                        if ia_reasoning:
                            self.logger.info(f"     💭 Razonamiento: {ia_reasoning}")
                        if sources:
                            self.logger.info(f"     📚 Fuentes: {', '.join(sources)}")
                        
                        # VALIDAR: ¿la respuesta IA está en las opciones disponibles?
                        ia_answer_valid = False
                        if ia_answer:
                            for option in select_obj.options:
                                if ia_answer.lower() in option.text.lower():
                                    ia_answer_valid = True
                                    break
                        
                        if not ia_answer_valid and ia_answer:
                            self.logger.warning(f"     ❌ Respuesta IA '{ia_answer}' NO está en opciones")
                            
                            # VERIFICAR: ¿Es respuesta "Información no disponible"?
                            if "información no disponible" in ia_answer.lower() or "no disponible" in ia_answer.lower():
                                result['low_confidence_count'] += 1
                                self.logger.warning(f"     ⚠️  RESPUESTA INÚTIL detectada ({result['low_confidence_count']}/{result['max_low_confidence']})")
                                
                                # Si alcanzamos el límite, abortar la aplicación
                                if result['low_confidence_count'] >= result['max_low_confidence']:
                                    self.logger.warning(f"     🛑 LIMITE DE BAJA CONFIANZA ALCANZADO - Abortando aplicación")
                                    result['status'] = 'MANUAL'
                                    result['abort_reason'] = 'Low confidence answers exceeded limit'
                                    return  # Salir del método para evitar más procesamiento
                            
                            # Fallback: si confianza < 85%, intentar respuesta genérica "No"
                            # (Mejor responder una opción que dejar vacío y causar loop infinito)
                            if ia_confidence < 0.85:
                                for option in select_obj.options[1:]:  # Skip primer "Select"
                                    if option.text.lower() in ['no', 'nein', 'non', 'non disponible']:
                                        ia_answer = option.text
                                        ia_answer_valid = True
                                        self.logger.info(f"     💡 Fallback a respuesta genérica: {ia_answer}")
                                        auto_submit = False  # Marcar como manual por confianza baja
                                        break
                            if not ia_answer_valid:
                                ia_answer = ""  # Rechazar solo si no hay fallback
                        
                        # THRESHOLD: Si confianza < 0.65, marcar como MANUAL
                        if ia_answer_valid and ia_confidence < 0.65:
                            self.logger.warning(f"     ⚠️  Confianza baja ({ia_confidence:.2f}) - Marcando como MANUAL")
                            result['status'] = 'MANUAL'
                            if 'manual_questions' not in result:
                                result['manual_questions'] = []
                            result['manual_questions'].append({
                                'question': question_text,
                                'ia_answer': ia_answer,
                'confidence': ia_confidence,
                                'reason': 'Below 0.65 threshold'
                            })
                            new_questions.append(question_text)
                            seen_questions.add(question_text)
                            continue  # Saltar esta pregunta
                    else:
                        self.logger.info(f"     ⚠️  IA deshabilitado, buscando en configuración")
                    
                    # Estrategia de respuesta por prioridad
                    answer = None
                    answer_source = None
                    
                    # 1. IA con respuesta válida (después de validar contra opciones)
                    if ia_answer:
                        answer = ia_answer
                        # Determinar fuente según confianza
                        if auto_submit and ia_confidence >= 0.85:
                            answer_source = "IA (Auto)"
                        elif ia_confidence >= 0.60:  # Confianza moderada
                            answer_source = "IA (Manual)"
                        else:  # Fallback genérico pero mejor que vacío
                            answer_source = "IA (Fallback)"
                    
                    # 2. Buscar en configuración si IA no respondió
                    if not answer:
                        answer = self.find_answer_for_question(question_text)
                        answer_source = "Config" if answer else None
                    
                    if answer:
                        found = False
                        # Re-buscar el select en caso de que el DOM cambió durante la IA
                        try:
                            new_select = self.driver.find_element(By.CSS_SELECTOR, f"select[id='{select_id}']")
                            select_obj = Select(new_select)
                        except:
                            self.logger.warning(f"     ⚠️  No se puede re-buscar select, intentando con cache...")
                        
                        for attempt in range(3):  # Reintentar hasta 3 veces si hay stale element
                            try:
                                for option in select_obj.options:
                                    if answer.lower() in option.text.lower():
                                        select_obj.select_by_visible_text(option.text)
                                        time.sleep(1)  # Esperar a que se procese la selección
                                        self.logger.info(f"     ✅ Seleccionado [{answer_source}]: {option.text}")
                                        
                                        # Agregar a log de respuestas
                                        if 'answers_log' not in result:
                                            result['answers_log'] = {}
                                        result['answers_log'][question_text] = {
                                            'answer': answer,
                                            'source': answer_source,
                                            'ia_confidence': ia_confidence,
                                            'ia_auto': auto_submit
                                        }
                                        
                                        seen_questions.add(question_text)
                                        found = True
                                        break
                                
                                if found:
                                    break
                            except StaleElementReferenceException:
                                if attempt < 2:
                                    self.logger.info(f"     🔄 Stale element en intento {attempt+1}, re-buscando...")
                                    time.sleep(1)
                                    # Re-buscar elementos
                                    new_select = self.driver.find_element(By.CSS_SELECTOR, f"select[id='{select_id}']")
                                    select_obj = Select(new_select)
                                else:
                                    self.logger.warning(f"     ❌ Stale element después de 3 intentos")
                                    raise
                        
                        if not found:
                            self.logger.warning(f"     ✗ Respuesta '{answer}' no encontrada en opciones")
                    else:
                        # Pregunta sin respuesta - agregar solo si no está duplicada
                        if question_text and question_text not in seen_questions:
                            new_questions.append(question_text)
                            seen_questions.add(question_text)
                            result['questions_encountered'].append(question_text)
                            self.logger.warning(f"     ❌ Sin respuesta disponible")
                        
                except Exception as e:
                    self.logger.info(f"  Error procesando dropdown: {e}")
                    continue
                    
        except Exception as e:
            self.logger.info(f"  Error en handle_dropdown_questions: {e}")
    
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
            if not isinstance(pregunta_data, dict):
                continue
            
            # Obtener patrones
            patrones = pregunta_data.get('patrones', [])
            
            # Verificar si algún patrón coincide
            for patron in patrones:
                if re.search(patron, question_text, re.IGNORECASE):
                    # Obtener respuesta según estructura
                    respuesta = None
                    
                    # Prioridad 1: respuesta_corta
                    if 'respuesta_corta' in pregunta_data:
                        respuesta = pregunta_data['respuesta_corta']
                    # Prioridad 2: respuesta directa
                    elif 'respuesta' in pregunta_data:
                        respuesta = pregunta_data['respuesta']
                    # Prioridad 3: respuesta_alternativa
                    elif 'respuesta_alternativa' in pregunta_data:
                        respuesta = pregunta_data['respuesta_alternativa']
                    # Prioridad 4: respuesta_default
                    elif 'respuesta_default' in pregunta_data:
                        respuesta = pregunta_data['respuesta_default']
                    # Prioridad 5: respuestas por contexto (usar default)
                    elif 'respuestas_por_contexto' in pregunta_data:
                        respuesta = pregunta_data['respuestas_por_contexto'].get('default', '')
                    # Prioridad 6: respuestas por nivel (usar default)
                    elif 'respuestas_por_nivel' in pregunta_data:
                        respuesta = pregunta_data['respuestas_por_nivel'].get('default', '')
                    # Prioridad 7: respuestas dict con corta/default
                    elif 'respuestas' in pregunta_data:
                        respuestas = pregunta_data['respuestas']
                        if isinstance(respuestas, dict):
                            respuesta = respuestas.get('corta') or respuestas.get('default') or list(respuestas.values())[0]
                        else:
                            respuesta = str(respuestas)
                    
                    if respuesta:
                        return respuesta
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
    successful = 0
    failed = 0
    
    for i, job in enumerate(pending_jobs, 1):
        # Feedback completo de progreso
        logger.info(f"\n{'='*60}")
        logger.info(f"Postulación {i}/{len(pending_jobs)}")
        logger.info(f"{'='*60}")
        logger.info(f"📌 {job.get('title', 'N/A')} - {job.get('company', 'N/A')}")
        
        result = applier.apply_to_job(job)
        results.append(result)
        
        # Actualizar contadores
        if result.get('success'):
            successful += 1
            logger.success(f"✅ APLICACIÓN #{successful} EXITOSA")
        else:
            failed += 1
            logger.warning(f"❌ Aplicación #{failed} falló: {result.get('error', 'Error desconocido')}")
        
        # Agregar a Google Sheets INMEDIATAMENTE (sin esperar a que termine todo)
        if sheets_manager:
            try:
                sheets_manager.add_job_application(job, result)
                logger.info('  ✓ Agregado a Google Sheets')
            except Exception as e:
                logger.warning(f'  ✗ Error agregando a Google Sheets: {e}')
        
        # Delay inteligente entre aplicaciones (con variación para evitar detection)
        import random
        if i < len(pending_jobs):  # Si no es la última
            delay = random.uniform(8, 15)  # Entre 8 y 15 segundos
            logger.info(f'  ⏳ Esperando {delay:.1f}s antes de siguiente aplicación...')
            time.sleep(delay)
    
    # Mostrar resumen
    logger.info(f"\n{'='*60}")
    logger.info("📊 RESUMEN FINAL DE APLICACIONES")
    logger.info(f"{'='*60}")
    logger.success(f"✅ Exitosas: {successful}/{len(results)}")
    logger.warning(f"❌ Fallidas: {failed}/{len(results)}")
    
    # Mostrar stats de IA si está disponible
    if applier.ia.enabled:
        ia_stats = applier.ia.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info("ESTADÍSTICAS IA")
        logger.info(f"{'='*60}")
        logger.info(f"Trabajos clasificados: {ia_stats['total_jobs_classified']}")
        logger.info(f"Preguntas respondidas: {ia_stats['total_questions_answered']}")
        logger.info(f"Automatizadas: {ia_stats['auto_answered']} ({ia_stats['automation_rate']:.1f}%)")
        logger.info(f"Manuales: {ia_stats['manual_marked']}")
        logger.info(f"Confianza promedio: {ia_stats['average_confidence']:.2f}/1.0")
        if ia_stats['cv_type_usage']:
            logger.info(f"CVs usados: {ia_stats['cv_type_usage']}")
    
    # Agregar stats globales de IA si está disponible
    results_metadata = {
        'total_applications': len(results),
        'successful': sum(1 for r in results if r.get('success')),
        'applied': sum(1 for r in results if r.get('status') == 'APPLIED'),
        'manual': sum(1 for r in results if r.get('status') == 'MANUAL'),
        'error': sum(1 for r in results if r.get('status') == 'ERROR')
    }
    
    if applier.ia.enabled:
        ia_stats = applier.ia.get_stats()
        results_metadata['ia_stats'] = ia_stats
        results_metadata['ia_enabled'] = True
    else:
        results_metadata['ia_enabled'] = False
    
    # Guardar resultados con metadata
    output_data = {
        'metadata': results_metadata,
        'results': results
    }
    
    results_file = Path("data/logs/application_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.success(f"Resultados guardados en: {results_file}")
    logger.info(f"  - Aplicaciones exitosas: {results_metadata['applied']}/{results_metadata['total_applications']}")
    if applier.ia.enabled:
        logger.info(f"  - IA Stats: {results_metadata['ia_stats'].get('automation_rate', 0):.1f}% automatizado")
    
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