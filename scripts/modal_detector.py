"""
Detector de modal de postulación de LinkedIn usando JavaScript y selectores fallback.

Este módulo implementa la detección robusta del modal de "Solicitud sencilla" que
aparece después de hacer clic en el botón de postulación. Usa JavaScript para
detectar el modal dinámicamente y múltiples selectores fallback para mayor robustez.
"""

import time
import logging
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)


class ModalDetector:
    """
    Detecta el modal de postulación usando JavaScript y múltiples selectores fallback.
    
    El modal de LinkedIn se carga dinámicamente con JavaScript, por lo que los métodos
    tradicionales de Selenium pueden fallar. Esta clase usa JavaScript para detectar
    el modal tan pronto como aparece en el DOM.
    """
    
    # Selectores ordenados por prioridad (más específico a más genérico)
    MODAL_SELECTORS = [
        # Selectores para modal overlay (página original)
        'div[data-test-modal-id="easy-apply-modal"]',
        'div[data-test-modal-container]',
        'div.jobs-easy-apply-modal',
        # Selectores para página de aplicación (después de redirect)
        'div.jobs-apply-form',
        'form[data-job-id]',
        'div[data-test-apply-form]',
        # Selectores genéricos
        'div[role="dialog"]',
        'div.artdeco-modal'
    ]
    
    def __init__(self, poll_interval: float = 0.5):
        """
        Inicializa el detector de modal.
        
        Args:
            poll_interval: Intervalo en segundos entre intentos de detección (default: 0.5)
        """
        self.poll_interval = poll_interval
    
    def wait_for_modal(self, driver: WebDriver, timeout: int = 15, initial_url: str = None) -> Optional[WebElement]:
        """
        Espera a que el modal aparezca usando JavaScript con polling.
        
        Intenta detectar el modal usando múltiples selectores fallback en orden de
        prioridad. Usa JavaScript para detectar elementos tan pronto como aparecen
        en el DOM, incluso si Selenium los considera "no interactuables".
        
        También detecta si la URL cambió (redirect a página de aplicación) y busca
        el modal en la nueva página.
        
        Args:
            driver: Instancia de Selenium WebDriver
            timeout: Tiempo máximo de espera en segundos (default: 15)
            initial_url: URL inicial antes del clic (para detectar redirects)
            
        Returns:
            WebElement del modal si se encuentra, None si timeout
        """
        logger.info(f"Esperando modal de postulación (timeout: {timeout}s)")
        if initial_url:
            logger.info(f"  URL inicial: {initial_url}")
        
        start_time = time.time()
        url_changed_logged = False
        
        while time.time() - start_time < timeout:
            # Verificar si la URL cambió (redirect)
            current_url = driver.current_url
            if initial_url and current_url != initial_url and not url_changed_logged:
                logger.info(f"  ✓ URL cambió (redirect detectado)")
                logger.info(f"    Nueva URL: {current_url}")
                url_changed_logged = True
            
            # Intentar cada selector en orden
            for selector in self.MODAL_SELECTORS:
                try:
                    # Usar JavaScript para detectar el modal
                    modal = driver.execute_script(
                        f"return document.querySelector('{selector}');"
                    )
                    
                    if modal and self._is_element_visible(driver, selector):
                        logger.info(f"  ✓ Modal detectado con selector: {selector}")
                        # Convertir el elemento JavaScript a WebElement de Selenium
                        return driver.find_element("css selector", selector)
                        
                except Exception as e:
                    logger.debug(f"Error al intentar selector {selector}: {e}")
                    continue
            
            # Esperar antes del siguiente intento
            time.sleep(self.poll_interval)
        
        # Log final con información de debug
        current_url = driver.current_url
        logger.warning(f"  ✗ Modal no detectado después de {timeout}s")
        logger.warning(f"    URL final: {current_url}")
        if initial_url and current_url != initial_url:
            logger.warning(f"    La URL cambió pero no se encontró modal en la nueva página")
        
        return None
    
    def is_modal_visible(self, driver: WebDriver) -> bool:
        """
        Verifica si el modal está visible usando JavaScript.
        
        Args:
            driver: Instancia de Selenium WebDriver
            
        Returns:
            True si el modal está visible, False en caso contrario
        """
        for selector in self.MODAL_SELECTORS:
            if self._is_element_visible(driver, selector):
                return True
        return False
    
    def _is_element_visible(self, driver: WebDriver, selector: str) -> bool:
        """
        Verifica si un elemento está visible usando JavaScript.
        
        Args:
            driver: Instancia de Selenium WebDriver
            selector: Selector CSS del elemento
            
        Returns:
            True si el elemento existe y es visible, False en caso contrario
        """
        try:
            is_visible = driver.execute_script(
                f"""
                const element = document.querySelector('{selector}');
                if (!element) return false;
                
                const style = window.getComputedStyle(element);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0' &&
                       element.offsetWidth > 0 &&
                       element.offsetHeight > 0;
                """
            )
            return bool(is_visible)
        except Exception as e:
            logger.debug(f"Error al verificar visibilidad de {selector}: {e}")
            return False
