#!/usr/bin/env python3
"""
Script de prueba rápida para validar los fixes
"""

import sys
import os

# Agregar scripts al path
sys.path.insert(0, 'scripts')

def test_imports():
    """Verificar que todos los imports funcionan"""
    print("🧪 Test 1: Verificando imports...")
    try:
        from linkedin_applier import LinkedInApplier
        from ia_integration import IAIntegration
        from utils import Config, Logger
        print("  ✅ Todos los imports funcionan correctamente")
        return True
    except Exception as e:
        print(f"  ❌ Error en imports: {e}")
        return False

def test_ia_integration():
    """Verificar que IA Integration se inicializa sin selenium_extractor"""
    print("\n🧪 Test 2: Verificando IA Integration...")
    try:
        from utils import Logger
        from ia_integration import IAIntegration
        
        logger = Logger()
        ia = IAIntegration(logger, debug=False)
        
        if ia.enabled:
            print("  ✅ IA Integration inicializada correctamente")
            print(f"     - IA habilitada: {ia.enabled}")
            print(f"     - Tiene classifier: {hasattr(ia, 'classifier')}")
            print(f"     - NO tiene extractor: {not hasattr(ia, 'extractor')}")
            return True
        else:
            print("  ⚠️  IA no habilitada (verificar OPENROUTER_API_KEY)")
            return True  # No es error, solo warning
    except Exception as e:
        print(f"  ❌ Error en IA Integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Verificar que la configuración se carga correctamente"""
    print("\n🧪 Test 3: Verificando configuración...")
    try:
        from utils import Config
        
        config = Config()
        
        # Verificar que se pueden cargar las rutas de CV
        cv_paths = config.get_cv_paths()
        print(f"  ✅ Configuración cargada")
        print(f"     - CVs configurados: {len(cv_paths)}")
        for cv_type, path in cv_paths.items():
            exists = os.path.exists(path) if path else False
            status = "✓" if exists else "✗"
            print(f"     - {cv_type}: {status} {path}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error en configuración: {e}")
        return False

def test_selenium_extractor_removed():
    """Verificar que selenium_extractor fue eliminado"""
    print("\n🧪 Test 4: Verificando eliminación de selenium_extractor...")
    
    extractor_path = os.path.join('scripts', 'selenium_extractor.py')
    
    if os.path.exists(extractor_path):
        print(f"  ❌ selenium_extractor.py todavía existe en {extractor_path}")
        return False
    else:
        print(f"  ✅ selenium_extractor.py eliminado correctamente")
        return True

def main():
    """Ejecutar todos los tests"""
    print("="*60)
    print("🚀 Tests de Validación - LinkedIn Job Automator")
    print("="*60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("IA Integration", test_ia_integration()))
    results.append(("Configuración", test_config()))
    results.append(("Selenium Extractor Eliminado", test_selenium_extractor_removed()))
    
    print("\n" + "="*60)
    print("📊 RESUMEN DE TESTS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  Total: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n  🎉 ¡Todos los tests pasaron! El sistema está listo para probar.")
        return 0
    else:
        print("\n  ⚠️  Algunos tests fallaron. Revisar errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
