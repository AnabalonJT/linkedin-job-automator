#!/usr/bin/env python3
"""
LinkedIn Job Scraper
Busca ofertas de trabajo en LinkedIn según criterios configurados
"""

import time
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

from utils import Config, Logger, clean_text, extract_job_id_from_url


class LinkedInScraper:
    """Scraper para búsqueda de ofertas en LinkedIn"""
    
    def __init__(self, config: Config, logger: Logger, headless: bool = False):
        self.config = config
        self.logger = logger
        self.headless = headless
        self.driver = None
        self.cookies_file = Path("data/cookies/linkedin_cookies.json")
        
        # Crear directorio de cookies si no existe
        self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    
    def setup_driver(self):
        """Configura el driver de Selenium con opciones anti-detección"""
        self.logger.info("Configurando Chrome driver...")
        
        # Detectar si estamos en Docker
        in_docker = os.path.exists('/.dockerenv')
        
        try:
            if in_docker:
                # Usar Selenium remoto en Docker
                self.logger.info("Detectado ambiente Docker, usando Selenium remoto...")
                from selenium.webdriver.remote.webdriver import WebDriver
                from selenium.webdriver.remote.webelement import WebElement
                
                options = webdriver.ChromeOptions()
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                
                # Conectar a Selenium remoto (selenium-chrome service en Docker)
                self.driver = webdriver.Remote(
                    command_executor='http://selenium-chrome:4444',
                    options=options
                )
            else:
                # Usar undetected_chromedriver localmente
                self.logger.info("Usando undetected_chromedriver localmente...")
                options = uc.ChromeOptions()
                
                if self.headless:
                    options.add_argument('--headless')
                
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                
                # Usar version_main para coincidir con tu Chrome instalado
                self.driver = uc.Chrome(options=options, version_main=144)
            
            self.logger.success("Chrome driver configurado exitosamente")
        except Exception as e:
            self.logger.error(f"Error configurando driver: {str(e)}")
            raise
    
    def save_cookies(self):
        """Guarda cookies de la sesión"""
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)
        self.logger.info("Cookies guardadas")
    
    def load_cookies(self):
        """Carga cookies guardadas"""
        if self.cookies_file.exists():
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            
            self.logger.info("Cookies cargadas")
            return True
        return False
    
    def login(self, email: str, password: str) -> bool:
        """
        Realiza login en LinkedIn
        
        Args:
            email: Email de LinkedIn
            password: Contraseña de LinkedIn
        
        Returns:
            True si login exitoso, False si falla
        """
        try:
            self.logger.info("Iniciando login en LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Intentar cargar cookies primero
            if self.load_cookies():
                self.logger.info("✓ Cookies cargadas, verificando sesión...")
                self.driver.refresh()
                time.sleep(3)
                
                # Verificar si estamos logueados
                if self.is_logged_in():
                    self.logger.success("Login exitoso usando cookies guardadas")
                    # Guardar cookies actualizadas
                    self.save_cookies()
                    return True
                else:
                    self.logger.info("Cookies expiradas, haciendo login...")
            
            # Si no funcionaron las cookies, hacer login manual
            self.logger.info("Realizando login manual...")
            
            # Verificar si ya estamos en la página de login
            current_url = self.driver.current_url
            if '/login' not in current_url:
                self.driver.get("https://www.linkedin.com/login")
                time.sleep(2)
            
            # Ingresar email
            try:
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                email_input.clear()
                email_input.send_keys(email)
                
                # Ingresar password
                password_input = self.driver.find_element(By.ID, "password")
                password_input.clear()
                password_input.send_keys(password)
                
                # Click en login
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                login_button.click()
                
                # Esperar a que cargue el feed
                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Error en formulario de login: {e}")
                # Puede que ya estemos logueados
                if self.is_logged_in():
                    self.logger.success("Ya estábamos logueados")
                    self.save_cookies()
                    return True
                return False
            
            # Verificar si hay verificación de seguridad
            current_url = self.driver.current_url
            if "checkpoint" in current_url or "challenge" in current_url:
                self.logger.warning("LinkedIn requiere verificación de seguridad")
                self.logger.warning("Por favor completa la verificación manualmente en el navegador")
                
                # Esperar hasta 2 minutos para verificación manual
                for i in range(24):  # 24 * 5 = 120 segundos
                    time.sleep(5)
                    if self.is_logged_in():
                        break
                else:
                    self.logger.error("Timeout esperando verificación manual")
                    return False
            
            # Guardar cookies si login exitoso
            if self.is_logged_in():
                self.save_cookies()
                self.logger.success("Login exitoso")
                return True
            else:
                self.logger.error("Login fallido")
                return False
                
        except Exception as e:
            self.logger.error(f"Error en login: {e}")
            # Verificar si a pesar del error estamos logueados
            if self.is_logged_in():
                self.logger.success("Login exitoso (detectado después de error)")
                self.save_cookies()
                return True
            return False
    
    def is_logged_in(self) -> bool:
        """Verifica si estamos logueados en LinkedIn"""
        try:
            # Intentar múltiples indicadores de sesión activa
            indicators = [
                "a[href*='/feed/']",
                "a[href*='/mynetwork/']",
                "a[href*='/jobs/']",
                "button[data-view-name='navigation-settings']",
                "nav.global-nav",
                "div[data-testid='primary-nav']"
            ]
            
            for indicator in indicators:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, indicator)
                    self.logger.info(f"  ✓ Sesión verificada con: {indicator}")
                    return True
                except NoSuchElementException:
                    continue
            
            # Si ninguno funciona, verificar URL
            current_url = self.driver.current_url
            if '/feed' in current_url or '/mynetwork' in current_url or '/jobs' in current_url:
                self.logger.info("  ✓ Sesión verificada por URL")
                return True
            
            self.logger.warning("  ✗ No se detectó sesión activa")
            return False
            
        except Exception as e:
            self.logger.warning(f"  Error verificando sesión: {e}")
            return False
    
    def search_jobs(self, keywords: str, location: str, num_jobs: int = 25, existing_job_ids: set = None) -> List[Dict[str, Any]]:
        """
        Busca trabajos en LinkedIn con scroll progresivo
        
        Args:
            keywords: Palabras clave de búsqueda
            location: Ubicación
            num_jobs: Número de trabajos a buscar
            existing_job_ids: Set de Job IDs ya existentes para evitar duplicados
        
        Returns:
            Lista de trabajos encontrados
        """
        self.logger.info(f"Buscando trabajos: '{keywords}' en '{location}'")
        
        # Inicializar set de Job IDs existentes si no se proporcionó
        if existing_job_ids is None:
            existing_job_ids = set()
        
        # Construir URL de búsqueda
        search_url = (
            f"https://www.linkedin.com/jobs/search/?"
            f"keywords={keywords.replace(' ', '%20')}&"
            f"location={location.replace(' ', '%20')}&"
            f"f_AL=true&"  # Easy Apply
            f"sortBy=DD"    # Más recientes
        )
        
        self.driver.get(search_url)
        self.logger.info(f"URL de búsqueda: {search_url}")
        time.sleep(5)  # Espera inicial para que cargue
        
        jobs = []
        processed_job_ids = existing_job_ids.copy()  # Copiar Job IDs existentes
        
        try:
            # Esperar a que cargue la página
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Estrategia: Procesar en lotes de 5 con scroll entre lotes
            batch_size = 5
            max_batches = (num_jobs // batch_size) + 1
            
            for batch_num in range(max_batches):
                self.logger.info(f"Procesando lote {batch_num + 1}/{max_batches}")
                
                # Obtener tarjetas visibles actualmente
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")
                
                if not job_cards:
                    self.logger.warning("No se encontraron más tarjetas de trabajo")
                    break
                
                # Calcular rango de este lote
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(job_cards))
                
                self.logger.info(f"  Tarjetas disponibles: {len(job_cards)}, procesando {start_idx} a {end_idx}")
                
                # Procesar este lote
                for idx in range(start_idx, end_idx):
                    if idx >= len(job_cards):
                        break
                    
                    if len(jobs) >= num_jobs:
                        self.logger.info(f"✓ Alcanzado límite de {num_jobs} trabajos")
                        break
                    
                    try:
                        card = job_cards[idx]
                        
                        # Scroll al elemento para que sea visible
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                        time.sleep(0.5)
                        
                        job_data = self.extract_job_data(card)
                        
                        if job_data:
                            job_id = extract_job_id_from_url(job_data['url'])
                            
                            if job_id not in processed_job_ids:
                                jobs.append(job_data)
                                processed_job_ids.add(job_id)
                                self.logger.info(f"  ✓ {job_data['title']} - {job_data['company']}")
                            else:
                                self.logger.info(f"  ⊘ Duplicado omitido: {job_data['title']}")
                        else:
                            self.logger.warning(f"  ✗ No se pudo extraer datos de tarjeta {idx + 1}")
                            
                    except Exception as e:
                        self.logger.warning(f"Error procesando tarjeta {idx + 1}: {str(e)}")
                        continue
                
                # Scroll al final para cargar más trabajos
                if len(jobs) < num_jobs and batch_num < max_batches - 1:
                    self.logger.info(f"  Haciendo scroll para cargar más trabajos...")
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)  # Esperar a que carguen nuevos elementos
                    
                    # Re-obtener tarjetas después del scroll
                    job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")
            
            self.logger.success(f"Total de trabajos extraídos: {len(jobs)}")
            
        except Exception as e:
            self.logger.error(f"Error buscando trabajos: {str(e)}")
        
        return jobs
    
    def extract_job_data(self, job_card) -> Dict[str, Any]:
        """
        Extrae datos de una tarjeta de trabajo
        
        Args:
            job_card: Elemento Selenium de la tarjeta
        
        Returns:
            Diccionario con datos del trabajo
        """
        try:
            # Título - Basado en el HTML real de LinkedIn
            title = None
            title_selectors = [
                "a.job-card-container__link strong",  # Selector exacto del HTML
                "a.job-card-list__title--link strong",
                "a.job-card-container__link",
                "a[aria-label]"  # El aria-label tiene el título completo
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                    title = clean_text(title_elem.text)
                    if not title and selector == "a[aria-label]":
                        # Si está vacío, obtener del aria-label
                        title = title_elem.get_attribute('aria-label')
                    if title:
                        break
                except NoSuchElementException:
                    continue
            
            if not title:
                self.logger.warning(f"    ✗ No se encontró título")
                return None
            
            # Empresa - del HTML: <span class="ZusfgnTvgtXKInZICCvxZapJnMwcNxuyes">
            company = None
            company_selectors = [
                "div.artdeco-entity-lockup__subtitle span",  # Selector del HTML real
                "span.job-card-container__primary-description",
                "h4"
            ]
            
            for selector in company_selectors:
                try:
                    company_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                    company = clean_text(company_elem.text)
                    if company and company != title:
                        break
                except NoSuchElementException:
                    continue
            
            # Ubicación - del HTML: dentro de ul.job-card-container__metadata-wrapper
            location = None
            location_selectors = [
                "ul.job-card-container__metadata-wrapper li span",  # Selector del HTML real
                "div.artdeco-entity-lockup__caption span",
                "li.job-card-container__metadata-item"
            ]
            
            for selector in location_selectors:
                try:
                    location_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                    location = clean_text(location_elem.text)
                    if location:
                        break
                except NoSuchElementException:
                    continue
            
            # URL - del HTML: <a href="/jobs/view/4366376246/...">
            url = None
            url_selectors = [
                "a.job-card-container__link",
                "a[href*='/jobs/view/']",
                "a.job-card-list__title--link"
            ]
            
            for selector in url_selectors:
                try:
                    link_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                    url = link_elem.get_attribute('href')
                    if url:
                        # Asegurar que sea URL completa
                        if url.startswith('/'):
                            url = f"https://www.linkedin.com{url}"
                        break
                except NoSuchElementException:
                    continue
            
            if not url:
                self.logger.warning(f"    ✗ No se encontró URL")
                return None
            
            # Verificar Easy Apply haciendo click en el trabajo
            has_easy_apply = self.check_easy_apply_in_detail(job_card)
            
            return {
                'title': title,
                'company': company or 'N/A',
                'location': location or 'N/A',
                'url': url,
                'has_easy_apply': has_easy_apply,
                'application_type': 'AUTO' if has_easy_apply else 'MANUAL',
                'scraped_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            self.logger.warning(f"    ✗ Error extrayendo datos: {str(e)}")
            return None
    
    def check_easy_apply_in_detail(self, job_card) -> bool:
        """
        Hace click en el trabajo y verifica si tiene Easy Apply en el panel de detalles
        
        Args:
            job_card: Elemento de la tarjeta de trabajo
        
        Returns:
            True si tiene Easy Apply, False si no
        """
        try:
            # Hacer click en la tarjeta para cargar detalles
            clickable = job_card.find_element(By.CSS_SELECTOR, "a.job-card-container__link")
            clickable.click()
            time.sleep(1.5)  # Esperar a que cargue el panel de detalles
            
            # Buscar el botón de "Solicitud sencilla" en el panel de detalles
            try:
                easy_apply_button = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button.jobs-apply-button"
                )
                button_text = easy_apply_button.text.lower()
                has_easy_apply = "solicitud sencilla" in button_text or "easy apply" in button_text
                
                if has_easy_apply:
                    self.logger.info(f"    ✓ Tiene Easy Apply")
                else:
                    self.logger.info(f"    ✗ No tiene Easy Apply")
                
                return has_easy_apply
                
            except NoSuchElementException:
                self.logger.info(f"    ✗ No tiene Easy Apply (botón no encontrado)")
                return False
                
        except Exception as e:
            self.logger.warning(f"    ⚠️ Error verificando Easy Apply: {str(e)}")
            return False
    
    def close(self):
        """Cierra el driver"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Driver cerrado")
            except Exception:
                # Ignorar errores al cerrar (común en Windows)
                pass


def main():
    """Función principal de prueba"""
    print("🚀 LinkedIn Job Scraper - Prueba")
    print("=" * 60)
    
    # Setup
    config = Config()
    logger = Logger()
    
    # Cargar configuración
    yaml_config = config.load_yaml_config()
    credentials = config.get_linkedin_credentials()
    
    if not credentials:
        logger.error("No se pudieron cargar credenciales de LinkedIn")
        return
    
    # Archivo de trabajos
    output_file = Path("data/logs/jobs_found.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # ============================================================================
    # PASO 1: Cargar TODOS los trabajos del Google Sheets y guardar en cache
    # ============================================================================
    all_sheets_jobs = []
    all_sheets_urls = set()
    
    try:
        from google_sheets_manager import GoogleSheetsManager
        sheets_id = config.get_env_var('GOOGLE_SHEETS_ID')
        if sheets_id and Path('config/google_credentials.json').exists():
            sheets_manager = GoogleSheetsManager('config/google_credentials.json', sheets_id)
            
            # Obtener TODOS los trabajos del Google Sheets
            all_sheets_jobs = sheets_manager.get_all_jobs_from_sheets()
            all_sheets_urls = {job.get('url') for job in all_sheets_jobs if job.get('url')}
            
            # Marcar trabajos del Sheets como no nuevos (ya en base de datos)
            for job in all_sheets_jobs:
                job['is_new'] = False
            
            logger.info(f"✓ Cargados {len(all_sheets_jobs)} trabajos del Google Sheets")
            
            # Guardar todos del sheets en jobs_found.json (como source de verdad)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_sheets_jobs, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Cache local actualizado con {len(all_sheets_jobs)} trabajos del Sheets")
    except Exception as e:
        logger.warning(f"No se pudo conectar a Google Sheets: {e}")
        # Cargar del cache local como fallback
        if output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    all_sheets_jobs = json.load(f)
                all_sheets_urls = {job.get('url') for job in all_sheets_jobs if job.get('url')}
                logger.info(f"✓ Cargados {len(all_sheets_jobs)} trabajos del cache local")
            except Exception as e2:
                logger.warning(f"No se pudieron cargar trabajos existentes: {str(e2)}")
    
    # ============================================================================
    # PASO 2: Buscar trabajos NUEVOS en LinkedIn
    # ============================================================================
    
    # Crear scraper
    scraper = LinkedInScraper(config, logger, headless=False)
    
    try:
        # Setup driver
        scraper.setup_driver()
        
        # Login
        if not scraper.login(credentials['username'], credentials['password']):
            logger.error("Login fallido, abortando")
            return
        
        # Extraer Job IDs para deduplicación
        existing_job_ids = {extract_job_id_from_url(url) for url in all_sheets_urls if url}
        
        # Buscar trabajos nuevos
        keywords = yaml_config['busqueda']['palabras_clave'][0]
        location = yaml_config['busqueda']['ubicaciones'][0]
        
        new_jobs = scraper.search_jobs(keywords, location, num_jobs=25, existing_job_ids=existing_job_ids)
        
        # Marcar trabajos nuevos como is_new:true
        for job in new_jobs:
            job['is_new'] = True
        
        # ============================================================================
        # PASO 3: Guardar trabajos nuevos en cache y variable
        # ============================================================================
        
        logger.info(f"\n{'='*60}")
        logger.info(f"RESULTADOS: {len(new_jobs)} trabajos nuevos encontrados")
        logger.info(f"Trabajos ya en base de datos: {len(all_sheets_urls)}")
        logger.info(f"{'='*60}\n")
        
        # Guardar trabajos: todos del sheets + los nuevos encontrados
        all_jobs = all_sheets_jobs + new_jobs
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)
        logger.success(f"✓ Cache local guardado: {len(all_jobs)} trabajos totales")
        logger.info(f"  - {len(all_sheets_jobs)} trabajos existentes (is_new: false)")
        logger.info(f"  - {len(new_jobs)} trabajos nuevos (is_new: true)")
        
        # ============================================================================
        # PASO 4: Actualizar new_jobs_to_apply.json con trabajos nuevos
        # ============================================================================
        new_jobs_file = Path("data/logs/new_jobs_to_apply.json")
        with open(new_jobs_file, 'w', encoding='utf-8') as f:
            json.dump(new_jobs, f, indent=2, ensure_ascii=False)
        logger.success(f"✓ new_jobs_to_apply.json actualizado: {len(new_jobs)} trabajos nuevos")
        
        
        # Mostrar los nuevos trabajos encontrados
        if new_jobs:
            logger.info("📋 Trabajos NUEVOS encontrados:")
            for i, job in enumerate(new_jobs, 1):
                logger.info(f"{i}. {job['title']}")
                logger.info(f"   Empresa: {job['company']}")
                logger.info(f"   Ubicación: {job['location']}")
                logger.info(f"   Easy Apply: {'✓' if job['has_easy_apply'] else '✗'}")
                logger.info(f"   URL: {job['url']}")
                logger.info("")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"💾 jobs_found.json actualizado: {len(all_jobs)} trabajos totales")
        logger.info(f"   ✓ Campo 'is_new' agregado a cada trabajo")
        logger.info(f"{'='*60}\n")
        logger.info(f"📝 Applier leerá jobs_found.json y postulará solo a trabajos con is_new: true")
        
    except Exception as e:
        logger.error(f"Error en ejecución: {str(e)}")
        raise
    
    finally:
        scraper.close()


if __name__ == "__main__":
    main()