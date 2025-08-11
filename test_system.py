#!/usr/bin/env python3
"""
Script de testing completo para el Sistema de Apuestas de Tenis.
Prueba todas las funcionalidades principales del sistema.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import uuid

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import config
from database import db_manager, init_database
from data_ingest import run_data_ingestion
from data_clean import DataCleaner
from betting_signals import BettingSignalGenerator
from backtest import BacktestEngine

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemTester:
    """Clase para testing completo del sistema."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
    
    def test_database_connection(self):
        """Probar conexión a base de datos."""
        logger.info("🧪 Probando conexión a base de datos...")
        try:
            # Inicializar base de datos
            init_database()
            
            # Probar conexión
            if db_manager.test_connection():
                logger.info("✅ Conexión a base de datos exitosa")
                self.test_results['database'] = 'PASS'
                return True
            else:
                logger.error("❌ Fallo en conexión a base de datos")
                self.test_results['database'] = 'FAIL'
                return False
        except Exception as e:
            logger.error(f"❌ Error en prueba de base de datos: {e}")
            self.test_results['database'] = 'FAIL'
            return False
    
    def test_data_ingestion(self):
        """Probar ingesta de datos."""
        logger.info("🧪 Probando ingesta de datos...")
        try:
            results = run_data_ingestion()
            
            if results and 'matches_found' in results:
                logger.info(f"✅ Ingesta exitosa: {results['matches_found']} partidos encontrados")
                self.test_results['ingestion'] = 'PASS'
                return True
            else:
                logger.warning("⚠️ Ingesta completada pero sin resultados")
                self.test_results['ingestion'] = 'WARN'
                return True
        except Exception as e:
            logger.error(f"❌ Error en ingesta de datos: {e}")
            self.test_results['ingestion'] = 'FAIL'
            return False
    
    def test_data_cleaning(self):
        """Probar limpieza de datos."""
        logger.info("🧪 Probando limpieza de datos...")
        try:
            cleaner = DataCleaner()
            
            # Obtener datos de la base de datos
            with db_manager.get_db_session() as session:
                matches = session.query(db_manager.MatchRaw).limit(10).all()
            
            if matches:
                cleaned_data = cleaner.clean_matches(matches)
                logger.info(f"✅ Limpieza exitosa: {len(cleaned_data)} partidos procesados")
                self.test_results['cleaning'] = 'PASS'
                return True
            else:
                logger.warning("⚠️ No hay datos para limpiar")
                self.test_results['cleaning'] = 'WARN'
                return True
        except Exception as e:
            logger.error(f"❌ Error en limpieza de datos: {e}")
            self.test_results['cleaning'] = 'FAIL'
            return False
    
    def test_betting_signals(self):
        """Probar generación de señales de apuesta."""
        logger.info("🧪 Probando generación de señales...")
        try:
            generator = BettingSignalGenerator()
            
            # Obtener datos limpios
            with db_manager.get_db_session() as session:
                matches = session.query(db_manager.MatchProcessed).limit(10).all()
            
            if matches:
                signals = generator.generate_signals(matches)
                logger.info(f"✅ Señales generadas: {len(signals)} oportunidades")
                self.test_results['signals'] = 'PASS'
                return True
            else:
                logger.warning("⚠️ No hay datos procesados para generar señales")
                self.test_results['signals'] = 'WARN'
                return True
        except Exception as e:
            logger.error(f"❌ Error en generación de señales: {e}")
            self.test_results['signals'] = 'FAIL'
            return False
    
    def test_backtesting(self):
        """Probar motor de backtesting."""
        logger.info("🧪 Probando motor de backtesting...")
        try:
            engine = BacktestEngine()
            
            # Obtener señales de la base de datos
            with db_manager.get_db_session() as session:
                signals = session.query(db_manager.BettingSignal).limit(10).all()
            
            if signals:
                results = engine.run_backtest(signals)
                logger.info(f"✅ Backtesting exitoso: {results.get('total_bets', 0)} apuestas simuladas")
                self.test_results['backtesting'] = 'PASS'
                return True
            else:
                logger.warning("⚠️ No hay señales para backtesting")
                self.test_results['backtesting'] = 'WARN'
                return True
        except Exception as e:
            logger.error(f"❌ Error en backtesting: {e}")
            self.test_results['backtesting'] = 'FAIL'
            return False
    
    def test_dashboard_accessibility(self):
        """Probar accesibilidad del dashboard."""
        logger.info("🧪 Probando accesibilidad del dashboard...")
        try:
            import requests
            response = requests.get('http://localhost:5000', timeout=5)
            if response.status_code == 200:
                logger.info("✅ Dashboard accesible")
                self.test_results['dashboard'] = 'PASS'
                return True
            else:
                logger.warning(f"⚠️ Dashboard responde con código {response.status_code}")
                self.test_results['dashboard'] = 'WARN'
                return True
        except Exception as e:
            logger.warning(f"⚠️ Dashboard no accesible: {e}")
            self.test_results['dashboard'] = 'WARN'
            return True
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas."""
        logger.info("🚀 Iniciando testing completo del sistema...")
        
        tests = [
            ('database', self.test_database_connection),
            ('ingestion', self.test_data_ingestion),
            ('cleaning', self.test_data_cleaning),
            ('signals', self.test_betting_signals),
            ('backtesting', self.test_backtesting),
            ('dashboard', self.test_dashboard_accessibility)
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                logger.error(f"❌ Error ejecutando {test_name}: {e}")
                self.test_results[test_name] = 'ERROR'
        
        self.print_results()
    
    def print_results(self):
        """Imprimir resultados de las pruebas."""
        logger.info("\n" + "="*60)
        logger.info("📊 RESULTADOS DEL TESTING COMPLETO")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed = sum(1 for result in self.test_results.values() if result == 'PASS')
        warnings = sum(1 for result in self.test_results.values() if result == 'WARN')
        failed = sum(1 for result in self.test_results.values() if result == 'FAIL')
        errors = sum(1 for result in self.test_results.values() if result == 'ERROR')
        
        for test_name, result in self.test_results.items():
            status_emoji = {
                'PASS': '✅',
                'WARN': '⚠️',
                'FAIL': '❌',
                'ERROR': '💥'
            }
            logger.info(f"{status_emoji.get(result, '❓')} {test_name.upper()}: {result}")
        
        logger.info("-"*60)
        logger.info(f"📈 RESUMEN: {passed}/{total_tests} pruebas exitosas")
        logger.info(f"⚠️  Advertencias: {warnings}")
        logger.info(f"❌ Fallos: {failed}")
        logger.info(f"💥 Errores: {errors}")
        
        duration = datetime.now() - self.start_time
        logger.info(f"⏱️  Duración total: {duration}")
        
        if passed == total_tests:
            logger.info("🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
        elif failed == 0 and errors == 0:
            logger.info("✅ Sistema funcionando con algunas advertencias")
        else:
            logger.info("⚠️  Sistema con problemas que requieren atención")

def main():
    """Función principal."""
    try:
        tester = SystemTester()
        tester.run_all_tests()
    except KeyboardInterrupt:
        logger.info("🛑 Testing interrumpido por el usuario")
    except Exception as e:
        logger.error(f"💥 Error fatal en testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
