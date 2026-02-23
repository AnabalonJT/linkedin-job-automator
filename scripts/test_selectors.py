#!/usr/bin/env python3
"""
Script de prueba para validar selectores de LinkedIn
Útil para debugging sin ejecutar todo el flujo de aplicación
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time


def test_easy_apply_button(driver, job_url):
    """Prueba los selectores del botón Easy Apply"""
    print(f"\n{'='*60}")
    print(f"Probando: {job_url}")
    print(f"{'='*60}")
    
    driver.get(job_url)
    time.sleep(5)
    
    # Scroll para asegurar que el botón esté visible
    driver.execute_script("window.scrollTo(0, 300);")
    time.sleep(1)
    
    # 1. Verificar si el trabajo está cerrado
    print("\n1. Verificando si el trabajo está cerrado...")
    closed_indicators = [
        "No longer accepting applications",
        "Ya no se aceptan solicitudes",
        "This job is no longer available",
        "Este trabajo ya no está disponible",
        "Closed",
        "Cerrado"
    ]
    
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text
        is_closed = any(indicator.lower() in page_text.lower() for indicator in closed_indicators)
        
        if is_closed:
            print("   ✗ TRABAJO CERRADO - Ya no acepta postulaciones")
            return False
        else:
            print("   ✓ Trabajo activo")
    except Exception as e:
        print(f"   ? No se pudo verificar: {e}")
    
    # 2. Buscar botón Easy Apply
    print("\n2. Buscando botón Easy Apply...")
    selectors = [
        ("button.jobs-apply-button", "Button con clase jobs-apply-button"),
        ("button[aria-label*='Solicitud sencilla']", "Button con aria-label 'Solicitud sencilla'"),
        ("button[aria-label*='Easy Apply']", "Button con aria-label 'Easy Apply'"),
        ("button#jobs-apply-button-id", "Button con ID jobs-apply-button-id"),
        ("button[data-live-test-job-apply-button]", "Button con data-live-test"),
        ("a[aria-label*='Solicitud sencilla']", "Link <a> con aria-label 'Solicitud sencilla'"),
        ("a[aria-label*='Easy Apply']", "Link <a> con aria-label 'Easy Apply'"),
        ("a.jobs-apply-button", "Link <a> con clase jobs-apply-button")
    ]
    
    easy_apply_found = False
    for selector, description in selectors:
        try:
            button = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            if button and button.is_displayed():
                print(f"   ✓ ENCONTRADO: {description}")
                print(f"      Selector: {selector}")
                print(f"      Tag: {button.tag_name}")
                print(f"      Texto: {button.text[:50]}")
                print(f"      Aria-label: {button.get_attribute('aria-label')}")
                easy_apply_found = True
                break
        except TimeoutException:
            print(f"   ✗ No encontrado: {description}")
    
    if not easy_apply_found:
        print("\n   ⚠ NO SE ENCONTRÓ BOTÓN EASY APPLY")
        
        # Buscar botón de postulación externa
        print("\n3. Buscando botón de postulación externa...")
        try:
            external_buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Postular'], a[aria-label*='Apply']")
            if external_buttons:
                print(f"   ✓ Encontrado botón de postulación externa")
                for btn in external_buttons[:3]:
                    if btn.is_displayed():
                        print(f"      - {btn.get_attribute('aria-label')}")
            else:
                print("   ✗ No se encontró botón de postulación externa")
        except Exception as e:
            print(f"   ? Error buscando botón externo: {e}")
        
        return False
    
    # 3. Intentar hacer click
    print("\n3. Intentando hacer click en Easy Apply...")
    try:
        button = driver.find_element(By.CSS_SELECTOR, selector)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
        time.sleep(1)
        button.click()
        print("   ✓ Click realizado")
        time.sleep(3)
    except Exception as e:
        print(f"   ✗ Error en click: {e}")
        try:
            driver.execute_script("arguments[0].click();", button)
            print("   ✓ Click con JavaScript realizado")
            time.sleep(3)
        except Exception as e2:
            print(f"   ✗ Error en click con JavaScript: {e2}")
            return False
    
    # 4. Verificar que el modal se abrió
    print("\n4. Verificando que el modal se abrió...")
    modal_selectors = [
        ("div[data-test-modal-id='easy-apply-modal']", "Modal con data-test-modal-id"),
        ("div.jobs-easy-apply-modal", "Modal con clase jobs-easy-apply-modal"),
        ("div[role='dialog'][aria-labelledby*='apply']", "Modal con role=dialog")
    ]
    
    modal_found = False
    for modal_selector, description in modal_selectors:
        try:
            modal = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
            )
            if modal and modal.is_displayed():
                print(f"   ✓ MODAL ENCONTRADO: {description}")
                print(f"      Selector: {modal_selector}")
                modal_found = True
                break
        except TimeoutException:
            print(f"   ✗ No encontrado: {description}")
    
    if not modal_found:
        print("\n   ⚠ MODAL NO SE ABRIÓ CORRECTAMENTE")
        driver.save_screenshot("data/logs/test_no_modal.png")
        print("   Screenshot guardado: data/logs/test_no_modal.png")
        return False
    
    # 5. Buscar botón "Siguiente" en el modal
    print("\n5. Buscando botón 'Siguiente' en el modal...")
    next_button_selectors = [
        ("button[aria-label*='siguiente']", "Button 'siguiente'"),
        ("button[aria-label*='Next']", "Button 'Next'"),
        ("button[data-easy-apply-next-button]", "Button con data-easy-apply-next-button"),
        ("button.artdeco-button--primary", "Button primary")
    ]
    
    for btn_selector, description in next_button_selectors:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, btn_selector)
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    print(f"   ✓ ENCONTRADO: {description}")
                    print(f"      Texto: {btn.text}")
                    print(f"      Aria-label: {btn.get_attribute('aria-label')}")
                    break
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "="*60)
    print("✅ PRUEBA COMPLETADA")
    print("="*60)
    
    return True


def main():
    """Función principal"""
    print("🧪 Test de Selectores de LinkedIn")
    print("="*60)
    
    # URLs de prueba (reemplazar con URLs reales)
    test_urls = [
        # Agregar aquí URLs de trabajos de LinkedIn para probar
        # Ejemplo: "https://www.linkedin.com/jobs/view/1234567890/"
    ]
    
    if not test_urls:
        print("\n⚠ No hay URLs de prueba configuradas")
        print("Edita este archivo y agrega URLs en la lista 'test_urls'")
        return
    
    # Configurar driver
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Descomentar para modo headless
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    
    try:
        # Cargar cookies si existen (para estar logueado)
        driver.get("https://www.linkedin.com")
        time.sleep(2)
        
        try:
            import json
            from pathlib import Path
            cookies_file = Path("data/cookies/linkedin_cookies.json")
            if cookies_file.exists():
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
                    for cookie in cookies:
                        driver.add_cookie(cookie)
                print("✓ Cookies cargadas")
                driver.refresh()
                time.sleep(3)
        except Exception as e:
            print(f"⚠ No se pudieron cargar cookies: {e}")
        
        # Probar cada URL
        for url in test_urls:
            test_easy_apply_button(driver, url)
            time.sleep(2)
        
    finally:
        input("\nPresiona Enter para cerrar el navegador...")
        driver.quit()


if __name__ == "__main__":
    main()
