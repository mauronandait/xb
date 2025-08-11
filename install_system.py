#!/usr/bin/env python3
"""
Script de Instalación del Sistema de Apuestas de Tenis
=====================================================

Este script automatiza la instalación y configuración del sistema:
1. Instala dependencias de Python
2. Configura la base de datos
3. Crea archivos de configuración
4. Verifica la instalación

Uso:
    python install_system.py [--env local|production]
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemInstaller:
    """Instalador automático del sistema."""
    
    def __init__(self, environment='local'):
        """
        Inicializar instalador.
        
        Args:
            environment: Entorno de instalación ('local' o 'production')
        """
        self.environment = environment
        self.project_root = Path(__file__).parent
        self.src_dir = self.project_root / 'src'
        self.config_dir = self.project_root / 'config'
        self.logs_dir = self.project_root / 'logs'
        self.data_dir = self.project_root / 'data'
        
        # Crear directorios necesarios
        self._create_directories()
    
    def _create_directories(self):
        """Crear directorios necesarios del proyecto."""
        directories = [
            self.logs_dir,
            self.data_dir,
            self.config_dir,
            self.project_root / 'templates',
            self.project_root / 'static'
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True)
            logger.info(f"✅ Directorio creado: {directory}")
    
    def install_python_dependencies(self):
        """Instalar dependencias de Python."""
        try:
            logger.info("📦 Instalando dependencias de Python...")
            
            # Verificar si pip está disponible
            if not shutil.which('pip'):
                logger.error("❌ pip no está disponible. Instale Python y pip primero.")
                return False
            
            # Instalar dependencias básicas
            requirements_file = self.project_root / 'requirements_updated.txt'
            if requirements_file.exists():
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
                ], check=True)
                logger.info("✅ Dependencias de Python instaladas")
                return True
            else:
                logger.warning("⚠️ Archivo requirements_updated.txt no encontrado")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error instalando dependencias: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return False
    
    def setup_database(self):
        """Configurar base de datos."""
        try:
            logger.info("🗄️ Configurando base de datos...")
            
            # Verificar si Docker está disponible
            if shutil.which('docker'):
                logger.info("🐳 Docker detectado, iniciando PostgreSQL...")
                
                # Iniciar PostgreSQL con Docker
                subprocess.run([
                    'docker', 'run', '-d',
                    '--name', 'tennis_betting_db',
                    '-e', 'POSTGRES_DB=tennis_betting',
                    '-e', 'POSTGRES_USER=postgres',
                    '-e', 'POSTGRES_PASSWORD=postgres123',
                    '-p', '5432:5432',
                    'postgres:15'
                ], check=True)
                
                logger.info("✅ Base de datos PostgreSQL iniciada en Docker")
                return True
            else:
                logger.warning("⚠️ Docker no detectado. Configure PostgreSQL manualmente.")
                logger.info("📋 Instrucciones:")
                logger.info("   1. Instale PostgreSQL")
                logger.info("   2. Cree base de datos 'tennis_betting'")
                logger.info("   3. Configure usuario 'postgres' con contraseña 'postgres123'")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error configurando base de datos: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return False
    
    def create_configuration_files(self):
        """Crear archivos de configuración."""
        try:
            logger.info("⚙️ Creando archivos de configuración...")
            
            # Crear archivo .env
            env_file = self.project_root / '.env'
            if not env_file.exists():
                env_content = self._get_env_content()
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(env_content)
                logger.info("✅ Archivo .env creado")
            
            # Crear archivo de configuración local
            local_config = self.config_dir / 'env_local.txt'
            if not local_config.exists():
                local_content = self._get_local_config_content()
                with open(local_config, 'w', encoding='utf-8') as f:
                    f.write(local_content)
                logger.info("✅ Archivo de configuración local creado")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando archivos de configuración: {e}")
            return False
    
    def _get_env_content(self):
        """Obtener contenido del archivo .env."""
        return """# Configuración del Sistema de Apuestas de Tenis
# =================================================

# Base de Datos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tennis_betting
DB_USER=postgres
DB_PASSWORD=postgres123

# Configuración de Apuestas
BANKROLL=10000
KELLY_FRACTION=0.5
MAX_STAKE_PERCENT=5
MIN_EV_THRESHOLD=0.05

# Configuración de Scraping
SCRAPING_ENABLED=true
SCRAPING_DELAY=2
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Configuración de Logging
LOG_LEVEL=INFO
LOG_FILE=logs/tennis_betting.log

# Configuración del Dashboard
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5000
DASHBOARD_DEBUG=false

# Configuración de Modelos
MODEL_UPDATE_FREQUENCY=3600
HISTORICAL_DATA_DAYS=365
"""
    
    def _get_local_config_content(self):
        """Obtener contenido de la configuración local."""
        return """# Configuración Local del Sistema
# =================================

# Base de Datos Local
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tennis_betting
DB_USER=postgres
DB_PASSWORD=postgres123

# Configuración de Desarrollo
LOG_LEVEL=DEBUG
DASHBOARD_DEBUG=true
SCRAPING_DELAY=1

# Configuración de Pruebas
TEST_MODE=true
MOCK_DATA=true
"""
    
    def verify_installation(self):
        """Verificar la instalación."""
        try:
            logger.info("🔍 Verificando instalación...")
            
            checks = []
            
            # Verificar dependencias de Python
            try:
                import flask
                import pandas
                import numpy
                import sqlalchemy
                checks.append(("✅ Dependencias de Python", True))
            except ImportError as e:
                checks.append((f"❌ Dependencias de Python: {e}", False))
            
            # Verificar archivos de configuración
            env_file = self.project_root / '.env'
            if env_file.exists():
                checks.append(("✅ Archivo .env", True))
            else:
                checks.append(("❌ Archivo .env", False))
            
            # Verificar directorios
            if self.logs_dir.exists():
                checks.append(("✅ Directorio de logs", True))
            else:
                checks.append(("❌ Directorio de logs", False))
            
            if self.data_dir.exists():
                checks.append(("✅ Directorio de datos", True))
            else:
                checks.append(("❌ Directorio de datos", False))
            
            # Mostrar resultados
            logger.info("📊 Resultados de la verificación:")
            for check, status in checks:
                logger.info(f"   {check}")
            
            # Verificar si la instalación fue exitosa
            successful_checks = sum(1 for _, status in checks if status)
            total_checks = len(checks)
            
            if successful_checks == total_checks:
                logger.info("🎉 ¡Instalación completada exitosamente!")
                return True
            else:
                logger.warning(f"⚠️ Instalación parcial: {successful_checks}/{total_checks} verificaciones exitosas")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en verificación: {e}")
            return False
    
    def run_quick_test(self):
        """Ejecutar prueba rápida del sistema."""
        try:
            logger.info("🧪 Ejecutando prueba rápida del sistema...")
            
            # Cambiar al directorio del proyecto
            os.chdir(self.project_root)
            
            # Ejecutar prueba básica
            test_result = subprocess.run([
                sys.executable, 'main.py', '--mode', 'ingest'
            ], capture_output=True, text=True, timeout=30)
            
            if test_result.returncode == 0:
                logger.info("✅ Prueba rápida exitosa")
                return True
            else:
                logger.warning(f"⚠️ Prueba rápida falló: {test_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Prueba rápida excedió el tiempo límite")
            return False
        except Exception as e:
            logger.error(f"❌ Error en prueba rápida: {e}")
            return False
    
    def install(self):
        """Ejecutar instalación completa."""
        try:
            logger.info("🚀 Iniciando instalación del Sistema de Apuestas de Tenis...")
            logger.info(f"📁 Directorio del proyecto: {self.project_root}")
            logger.info(f"🌍 Entorno: {self.environment}")
            
            # Paso 1: Instalar dependencias
            if not self.install_python_dependencies():
                logger.error("❌ Falló la instalación de dependencias")
                return False
            
            # Paso 2: Configurar base de datos
            if not self.setup_database():
                logger.warning("⚠️ Configuración de base de datos falló")
            
            # Paso 3: Crear archivos de configuración
            if not self.create_configuration_files():
                logger.error("❌ Falló la creación de archivos de configuración")
                return False
            
            # Paso 4: Verificar instalación
            if not self.verify_installation():
                logger.error("❌ Falló la verificación de instalación")
                return False
            
            # Paso 5: Ejecutar prueba rápida
            if self.run_quick_test():
                logger.info("✅ Prueba del sistema exitosa")
            else:
                logger.warning("⚠️ Prueba del sistema falló")
            
            logger.info("🎉 Instalación completada!")
            logger.info("📋 Próximos pasos:")
            logger.info("   1. Configure su base de datos si es necesario")
            logger.info("   2. Ejecute: python main.py --mode full")
            logger.info("   3. Acceda al dashboard: http://localhost:5000")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error durante la instalación: {e}")
            return False

def main():
    """Función principal del instalador."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Instalador del Sistema de Apuestas de Tenis')
    parser.add_argument('--env', choices=['local', 'production'], default='local',
                       help='Entorno de instalación')
    parser.add_argument('--skip-deps', action='store_true',
                       help='Saltar instalación de dependencias')
    parser.add_argument('--skip-db', action='store_true',
                       help='Saltar configuración de base de datos')
    
    args = parser.parse_args()
    
    try:
        # Crear instalador
        installer = SystemInstaller(environment=args.env)
        
        # Ejecutar instalación
        success = installer.install()
        
        if success:
            print("\n🎉 ¡Instalación completada exitosamente!")
            print("📋 Para ejecutar el sistema:")
            print("   python main.py --mode full")
            print("   python main.py --mode dashboard")
            return 0
        else:
            print("\n❌ La instalación falló. Revise los logs para más detalles.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Instalación interrumpida por el usuario")
        return 1
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
