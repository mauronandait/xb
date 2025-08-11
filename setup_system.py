#!/usr/bin/env python3
"""
Script de inicialización del sistema de apuestas de tenis.
Configura el entorno, la base de datos y verifica que todo esté funcionando.
"""

import os
import sys
import logging
from pathlib import Path

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent / "src"))

from src.config import config
from src.database import setup_database
from src.data_clean import TennisDataCleaner
from src.betting_signals import BettingSignalDetector
from src.backtest import BacktestEngine

def setup_logging():
    """Configurar el sistema de logging."""
    try:
        config.setup_logging()
        logging.info("Sistema de logging configurado")
        return True
    except Exception as e:
        print(f"Error configurando logging: {e}")
        return False

def check_dependencies():
    """Verificar que todas las dependencias estén instaladas."""
    try:
        import pandas as pd
        import numpy as np
        import psycopg2
        import sqlalchemy
        import streamlit
        import plotly
        import xgboost
        import lightgbm
        
        print("✅ Todas las dependencias están instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("Ejecuta: pip install -r requirements.txt")
        return False

def check_environment():
    """Verificar la configuración del entorno."""
    try:
        print("\n=== VERIFICACIÓN DEL ENTORNO ===")
        
        # Verificar archivo .env
        env_file = Path("config") / ".env"
        if env_file.exists():
            print("✅ Archivo .env encontrado")
        else:
            print("⚠️  Archivo .env no encontrado")
            print("   Copia config/env_local.txt a config/.env y configura las variables")
        
        # Verificar directorios
        directories = ["logs", "notebooks", "tests"]
        for dir_name in directories:
            dir_path = Path(dir_name)
            if dir_path.exists():
                print(f"✅ Directorio {dir_name} existe")
            else:
                print(f"❌ Directorio {dir_name} no existe")
        
        # Verificar configuración
        print(f"   Base de datos: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
        print(f"   Bankroll: ${config.BANKROLL:,.2f}")
        print(f"   Kelly Fraction: {config.KELLY_FRACTION}")
        
        return True
    except Exception as e:
        print(f"Error verificando entorno: {e}")
        return False

def setup_database_system():
    """Configurar el sistema de base de datos."""
    try:
        print("\n=== CONFIGURACIÓN DE BASE DE DATOS ===")
        
        # Verificar conexión
        print("Intentando conectar a la base de datos...")
        success = setup_database()
        
        if success:
            print("✅ Base de datos configurada exitosamente")
            return True
        else:
            print("❌ Error configurando la base de datos")
            print("   Verifica que PostgreSQL esté ejecutándose")
            print("   Verifica las credenciales en config/.env")
            return False
            
    except Exception as e:
        print(f"❌ Error en configuración de base de datos: {e}")
        return False

def test_modules():
    """Probar que todos los módulos funcionen correctamente."""
    try:
        print("\n=== PRUEBA DE MÓDULOS ===")
        
        # Probar limpiador de datos
        cleaner = TennisDataCleaner()
        print("✅ Módulo de limpieza de datos funcionando")
        
        # Probar detector de señales
        detector = BettingSignalDetector()
        print("✅ Módulo de detección de señales funcionando")
        
        # Probar motor de backtesting
        engine = BacktestEngine()
        print("✅ Módulo de backtesting funcionando")
        
        return True
    except Exception as e:
        print(f"❌ Error probando módulos: {e}")
        return False

def create_sample_data():
    """Crear datos de ejemplo para probar el sistema."""
    try:
        print("\n=== CREANDO DATOS DE EJEMPLO ===")
        
        # Datos de ejemplo
        sample_matches = [
            {
                'match_id': 'Djokovic_Nadal_Australian_Open_20241201',
                'tournament': 'Australian Open',
                'player1': 'Novak Djokovic',
                'player2': 'Rafael Nadal',
                'match_time': '2024-12-01T15:00:00',
                'player1_odds': 1.85,
                'player2_odds': 2.10
            },
            {
                'match_id': 'Federer_Medvedev_Wimbledon_20241202',
                'tournament': 'Wimbledon',
                'player1': 'Roger Federer',
                'player2': 'Daniil Medvedev',
                'match_time': '2024-12-02T14:00:00',
                'player1_odds': 2.50,
                'player2_odds': 1.60
            }
        ]
        
        # Probar limpieza de datos
        cleaner = TennisDataCleaner()
        cleaned_data = cleaner.run_full_cleaning_pipeline(sample_matches)
        
        print(f"✅ Datos de ejemplo procesados: {len(cleaned_data)} partidos")
        
        # Probar detección de señales (con probabilidades simuladas)
        cleaned_data['model_prob_player1'] = [0.58, 0.35]
        cleaned_data['model_prob_player2'] = [0.42, 0.65]
        
        detector = BettingSignalDetector(bankroll=10000)
        signals = detector.generate_betting_recommendations(cleaned_data)
        
        if signals['signals'].empty:
            print("ℹ️  No se detectaron señales (normal para datos de ejemplo)")
        else:
            print(f"✅ Señales detectadas: {len(signals['signals'])}")
        
        return True
    except Exception as e:
        print(f"❌ Error creando datos de ejemplo: {e}")
        return False

def main():
    """Función principal de inicialización."""
    print("🎾 INICIALIZANDO SISTEMA DE APUESTAS DE TENIS 🎾")
    print("=" * 50)
    
    # Paso 1: Verificar dependencias
    if not check_dependencies():
        return False
    
    # Paso 2: Configurar logging
    if not setup_logging():
        return False
    
    # Paso 3: Verificar entorno
    if not check_environment():
        return False
    
    # Paso 4: Configurar base de datos (opcional por ahora)
    print("\n⚠️  NOTA: La base de datos requiere Docker instalado")
    print("   Puedes continuar sin ella por ahora")
    try:
        setup_database_system()
    except:
        print("   ℹ️  Base de datos no disponible - continuando sin ella")
    
    # Paso 5: Probar módulos
    if not test_modules():
        return False
    
    # Paso 6: Crear datos de ejemplo
    if not create_sample_data():
        return False
    
    print("\n" + "=" * 50)
    print("🎉 SISTEMA INICIALIZADO EXITOSAMENTE 🎉")
    print("\nPróximos pasos:")
    print("1. Configura las variables en config/.env")
    print("2. Para usar la base de datos, instala Docker Desktop")
    print("3. Ejecuta: streamlit run src/dashboard.py")
    print("4. O ejecuta: python src/data_ingest.py")
    print("\n¡El sistema está listo para usar!")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Inicialización cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        sys.exit(1)
