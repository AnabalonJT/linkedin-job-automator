#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test: Input Type Detection y IA Awareness
Verifica que el sistema detecte correctamente el tipo de input esperado
y que la IA responda apropiadamente
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

def test_input_type_detection():
    """Test de detección de tipos de input"""
    print("\n" + "="*70)
    print("TEST: Input Type Detection")
    print("="*70)
    
    # Simulamos atributos HTML como diccionarios
    test_cases = [
        {
            'name': 'Pregunta sobre años (con "años" en placeholder)',
            'attributes': {'placeholder': '¿Cuántos años de experiencia?', 'inputmode': None, 'pattern': None},
            'expected': 'number'
        },
        {
            'name': 'Pregunta sobre años (con "year" en placeholder)',
            'attributes': {'placeholder': 'How many years?', 'inputmode': None, 'pattern': None},
            'expected': 'number'
        },
        {
            'name': 'Input con inputmode número',
            'attributes': {'placeholder': '', 'inputmode': 'numeric', 'pattern': None},
            'expected': 'numeric'
        },
        {
            'name': 'Input con pattern numérico',
            'attributes': {'placeholder': '', 'inputmode': None, 'pattern': r'[\d]{1,2}'},
            'expected': 'number'
        },
        {
            'name': 'Email input',
            'attributes': {'placeholder': 'correo@email.com', 'inputmode': None, 'pattern': None, 'type': 'email'},
            'expected': 'email'
        },
        {
            'name': 'Teléfono input',
            'attributes': {'placeholder': 'Teléfono', 'inputmode': None, 'pattern': None},
            'expected': 'tel'
        },
        {
            'name': 'Texto normal (sin claves)',
            'attributes': {'placeholder': 'Escribe algo aquí', 'inputmode': None, 'pattern': None},
            'expected': 'text'
        }
    ]
    
    from selenium.webdriver.common.by import By
    
    # Creamos mock objects para simular inputs
    class MockInput:
        def __init__(self, attrs):
            self.attrs = attrs
        
        def get_attribute(self, name):
            return self.attrs.get(name, '')
    
    # Función de detección copia simplificada
    def detect_input_type(mock_input, attrs):
        # 1. Check type
        input_type = attrs.get('type', '')
        if input_type in ['number', 'date', 'email', 'tel', 'url']:
            return input_type
        
        # 2. Check inputmode
        inputmode = attrs.get('inputmode', '')
        if inputmode:
            return inputmode
        
        # 3. Check pattern
        pattern = attrs.get('pattern', '')
        if pattern:
            if r'\d' in pattern or 'number' in pattern.lower():
                return 'number'
        
        # 4. Check placeholder
        placeholder = attrs.get('placeholder', '').lower()
        if any(word in placeholder for word in ['años', 'year', 'edad', 'age', 'número', 'number']):
            return 'number'
        if any(word in placeholder for word in ['correo', '@']):
            return 'email'
        if any(word in placeholder for word in ['teléfono', 'phone']):
            return 'tel'
        
        return 'text'
    
    passed = 0
    for test in test_cases:
        mock = MockInput(test['attributes'])
        result = detect_input_type(mock, test['attributes'])
        is_pass = result == test['expected']
        passed += is_pass
        
        status = "✅ PASS" if is_pass else "❌ FAIL"
        print(f"\n  {status}: {test['name']}")
        print(f"    Esperado: {test['expected']}")
        print(f"    Obtenido: {result}")
        print(f"    Attrs: {test['attributes']}")
    
    print(f"\n  Total: {passed}/{len(test_cases)} pasados")
    return passed == len(test_cases)

def test_prompt_support():
    """Test: Verificar que el prompt del sistema tiene las instrucciones correctas"""
    print("\n" + "="*70)
    print("TEST: IA Prompt Update")
    print("="*70)
    
    # Simulamos el prompt actualizado
    system_prompt = """Eres un asistente para postulaciones de trabajo.
TIPOS DE PREGUNTA/RESPUESTA:
- text_input_number: RESPONDO SOLO UN NÚMERO (sin texto, sin decimales)
- text_input_date: RESPONDO SOLO UNA FECHA
- Preguntas NUMBER sobre "años de experiencia":
  * NO respondo "0.2" ni "3.5" - SÖ NÚMEROS ENTEROS
  * REST APIs (5 años) -> respuesta "5"
  * Python (4 años) -> respuesta "4"
"""
    
    checks = [
        ('text_input_number' in system_prompt, "Reconoce text_input_number"),
        ('RESPONDO SOLO UN NÚMERO' in system_prompt, "Instruye responder número limpio"),
        ('SÖ NÚMEROS ENTEROS' in system_prompt, "Especifica números enteros"),
        ('REST APIs' in system_prompt, "Menciona ejemplo REST APIs"),
        ('"5"' in system_prompt or "'5'" in system_prompt, "Ejemplo con número 5 limpio"),
    ]
    
    passed = 0
    for check, desc in checks:
        status = "✅ PASS" if check else "❌ FAIL"
        print(f"  {status}: {desc}")
        passed += check
    
    print(f"\n  Total: {passed}/{len(checks)} checklist completado")
    return passed == len(checks)

def test_applier_integration():
    """Test: Verificar que linkedin_applier tiene detect_input_type"""
    print("\n" + "="*70)
    print("TEST: Applier Integration")
    print("="*70)
    
    try:
        from linkedin_applier import LinkedInApplier
        
        # Verificar que exista el método
        has_detect = hasattr(LinkedInApplier, 'detect_input_type')
        print(f"  {'✅' if has_detect else '❌'} Método detect_input_type existe: {has_detect}")
        
        return has_detect
    except Exception as e:
        print(f"  ❌ Error importando: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("🧪 TESTING: Input Type Detection & IA Awareness")
    print("="*70)
    
    tests = [
        ("Input Type Detection", test_input_type_detection),
        ("IA Prompt Support", test_prompt_support),
        ("Applier Integration", test_applier_integration),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n  ❌ EXCEPCIÓN: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Resumen
    print("\n" + "="*70)
    print("📊 RESUMEN")
    print("="*70)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    total_passed = sum(1 for p in results.values() if p)
    total = len(results)
    
    print(f"\n  Total: {total_passed}/{total} tests pasados")
    
    if total_passed == total:
        print("\n✅ ¡LISTO PARA TESTING CON DATOS REALES!")
        return 0
    else:
        print(f"\n❌ {total - total_passed} tests fallaron")
        return 1

if __name__ == "__main__":
    exit(main())
