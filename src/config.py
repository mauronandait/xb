#!/usr/bin/env python3
"""
Configuración centralizada del sistema de apuestas de tenis.
Maneja variables de entorno, configuración de base de datos y parámetros del sistema.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import json

class Config:
    """Clase de configuración centralizada."""
    
    def __init__(self):
        """Inicializar configuración."""
        self._load_environment()
        self._setup_logging()
        self._validate_config()
        self._load_database_config()
    
    def _load_environment(self):
        """Cargar variables de entorno desde archivo .env."""
        # Buscar archivo .env en diferentes ubicaciones
        env_paths = [
            Path(__file__).parent.parent / 'config' / '.env',
            Path(__file__).parent.parent / 'config' / 'env_corrected.txt',
            Path(__file__).parent.parent / '.env',
            Path.cwd() / '.env'
        ]
        
        env_loaded = False
        for env_path in env_paths:
            if env_path.exists():
                try:
                    load_dotenv(env_path, encoding='utf-8')
                    env_loaded = True
                    print(f"✅ Variables de entorno cargadas desde: {env_path}")
                    break
                except Exception as e:
                    print(f"⚠️  Error cargando {env_path}: {e}")
                    continue
        
        if not env_loaded:
            print("⚠️  No se pudo cargar archivo .env, usando variables del sistema")
    
    def _setup_logging(self):
        """Configurar sistema de logging."""
        log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
        log_file = os.getenv('LOG_FILE', 'logs/tennis_betting.log')
        
        # Crear directorio de logs si no existe
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Sistema de logging configurado")
    
    def _validate_config(self):
        """Validar configuración crítica."""
        required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.logger.warning(f"Variables de entorno faltantes: {missing_vars}")
            self.logger.warning("Usando valores por defecto para desarrollo")
    
    def _load_database_config(self):
        """Cargar configuración específica de base de datos."""
        self.db_config = {
            'host': self.DB_HOST,
            'port': self.DB_PORT,
            'database': self.DB_NAME,
            'user': self.DB_USER,
            'password': self.DB_PASSWORD,
            'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
        }
    
    # Propiedades de base de datos
    @property
    def DB_HOST(self) -> str:
        return os.getenv('DB_HOST', 'localhost')
    
    @property
    def DB_PORT(self) -> int:
        return int(os.getenv('DB_PORT', '5432'))
    
    @property
    def DB_NAME(self) -> str:
        return os.getenv('DB_NAME', 'tennis_betting')
    
    @property
    def DB_USER(self) -> str:
        return os.getenv('DB_USER', 'postgres')
    
    @property
    def DB_PASSWORD(self) -> str:
        return os.getenv('DB_PASSWORD', 'postgres123')
    
    # Configuración de 1xBet
    @property
    def ONEXBET_API_URL(self) -> str:
        return os.getenv('ONEXBET_API_URL', 'https://1xbet.com/api/v1')
    
    @property
    def ONEXBET_API_KEY(self) -> Optional[str]:
        return os.getenv('ONEXBET_API_KEY')
    
    # Configuración de scraping
    @property
    def SCRAPING_ENABLED(self) -> bool:
        return os.getenv('SCRAPING_ENABLED', 'true').lower() == 'true'
    
    @property
    def SCRAPING_DELAY(self) -> int:
        return int(os.getenv('SCRAPING_DELAY', '2'))
    
    @property
    def USER_AGENT(self) -> str:
        return os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Configuración de apuestas
    @property
    def BANKROLL(self) -> float:
        return float(os.getenv('BANKROLL', '10000'))
    
    @property
    def KELLY_FRACTION(self) -> float:
        return float(os.getenv('KELLY_FRACTION', '0.5'))
    
    @property
    def MAX_STAKE_PERCENT(self) -> float:
        return float(os.getenv('MAX_STAKE_PERCENT', '5'))
    
    @property
    def MIN_EV_THRESHOLD(self) -> float:
        return float(os.getenv('MIN_EV_THRESHOLD', '0.05'))
    
    # Configuración de notificaciones
    @property
    def TELEGRAM_BOT_TOKEN(self) -> Optional[str]:
        return os.getenv('TELEGRAM_BOT_TOKEN')
    
    @property
    def TELEGRAM_CHAT_ID(self) -> Optional[str]:
        return os.getenv('TELEGRAM_CHAT_ID')
    
    # Configuración de email
    @property
    def EMAIL_SMTP_SERVER(self) -> str:
        return os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
    
    @property
    def EMAIL_SMTP_PORT(self) -> int:
        return int(os.getenv('EMAIL_SMTP_PORT', '587'))
    
    @property
    def EMAIL_USER(self) -> Optional[str]:
        return os.getenv('EMAIL_USER')
    
    @property
    def EMAIL_PASSWORD(self) -> Optional[str]:
        return os.getenv('EMAIL_PASSWORD')
    
    @property
    def EMAIL_RECIPIENTS(self) -> str:
        return os.getenv('EMAIL_RECIPIENTS', '')
    
    @property
    def ALERTS_EMAIL_ENABLED(self) -> bool:
        return os.getenv('ALERTS_EMAIL_ENABLED', 'false').lower() == 'true'
    
    @property
    def ALERTS_TELEGRAM_ENABLED(self) -> bool:
        return os.getenv('ALERTS_TELEGRAM_ENABLED', 'false').lower() == 'true'
    
    # Configuración de modelos ML
    @property
    def MODEL_UPDATE_FREQUENCY(self) -> int:
        return int(os.getenv('MODEL_UPDATE_FREQUENCY', '3600'))
    
    @property
    def HISTORICAL_DATA_DAYS(self) -> int:
        return int(os.getenv('HISTORICAL_DATA_DAYS', '365'))
    
    # Configuración del dashboard
    @property
    def DASHBOARD_HOST(self) -> str:
        return os.getenv('DASHBOARD_HOST', '0.0.0.0')
    
    @property
    def DASHBOARD_PORT(self) -> int:
        return int(os.getenv('DASHBOARD_PORT', '5000'))
    
    @property
    def DASHBOARD_DEBUG(self) -> bool:
        return os.getenv('DASHBOARD_DEBUG', 'false').lower() == 'true'
    
    # Configuración de seguridad
    @property
    def SECRET_KEY(self) -> str:
        return os.getenv('SECRET_KEY', 'tennis_betting_secret_key_2024_change_in_production')
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        return os.getenv('JWT_SECRET_KEY', 'jwt_secret_key_change_in_production')
    
    @property
    def JWT_ACCESS_TOKEN_EXPIRES(self) -> int:
        return int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))
    
    # Configuración de caché
    @property
    def REDIS_HOST(self) -> str:
        return os.getenv('REDIS_HOST', 'localhost')
    
    @property
    def REDIS_PORT(self) -> int:
        return int(os.getenv('REDIS_PORT', '6379'))
    
    @property
    def REDIS_DB(self) -> int:
        return int(os.getenv('REDIS_DB', '0'))
    
    @property
    def REDIS_PASSWORD(self) -> Optional[str]:
        return os.getenv('REDIS_PASSWORD')
    
    # Configuración de testing
    @property
    def TESTING(self) -> bool:
        return os.getenv('TESTING', 'false').lower() == 'true'
    
    @property
    def TEST_DATABASE_URL(self) -> str:
        return os.getenv('TEST_DATABASE_URL', 'postgresql://postgres:postgres123@localhost:5432/tennis_betting_test')
    
    def get_database_url(self) -> str:
        """Obtener URL de conexión a base de datos."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def get_database_url_without_db(self) -> str:
        """Obtener URL de conexión sin especificar base de datos."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}"
    
    def get_redis_url(self) -> str:
        """Obtener URL de conexión a Redis."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    def is_production(self) -> bool:
        """Verificar si estamos en entorno de producción."""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    
    def get_log_level(self) -> str:
        """Obtener nivel de logging configurado."""
        return os.getenv('LOG_LEVEL', 'INFO')
    
    def get_config_dict(self) -> dict:
        """Obtener configuración como diccionario (sin contraseñas)."""
        return {
            'database': {
                'host': self.DB_HOST,
                'port': self.DB_PORT,
                'database': self.DB_NAME,
                'user': self.DB_USER,
                'pool_size': self.db_config['pool_size'],
                'max_overflow': self.db_config['max_overflow'],
            },
            'scraping': {
                'enabled': self.SCRAPING_ENABLED,
                'delay': self.SCRAPING_DELAY,
                'user_agent': self.USER_AGENT,
            },
            'betting': {
                'bankroll': self.BANKROLL,
                'kelly_fraction': self.KELLY_FRACTION,
                'max_stake_percent': self.MAX_STAKE_PERCENT,
                'min_ev_threshold': self.MIN_EV_THRESHOLD,
            },
            'dashboard': {
                'host': self.DASHBOARD_HOST,
                'port': self.DASHBOARD_PORT,
                'debug': self.DASHBOARD_DEBUG,
            },
            'models': {
                'update_frequency': self.MODEL_UPDATE_FREQUENCY,
                'historical_data_days': self.HISTORICAL_DATA_DAYS,
            }
        }
    
    def validate_database_connection(self) -> bool:
        """Validar conexión a base de datos."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.DB_HOST,
                port=self.DB_PORT,
                database=self.DB_NAME,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                connect_timeout=10
            )
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Error conectando a base de datos: {e}")
            return False
    
    def log_configuration(self):
        """Registrar configuración actual (sin información sensible)."""
        config_dict = self.get_config_dict()
        self.logger.info("Configuración del sistema cargada:")
        self.logger.info(f"  Entorno: {'Producción' if self.is_production() else 'Desarrollo'}")
        self.logger.info(f"  Base de datos: {self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")
        self.logger.info(f"  Scraping: {'Habilitado' if self.SCRAPING_ENABLED else 'Deshabilitado'}")
        self.logger.info(f"  Dashboard: {self.DASHBOARD_HOST}:{self.DASHBOARD_PORT}")
        self.logger.info(f"  Bankroll: ${self.BANKROLL:,.2f}")
        self.logger.info(f"  Log level: {self.get_log_level()}")

# Instancia global de configuración
config = Config()

# Registrar configuración al importar
if __name__ != "__main__":
    config.log_configuration()
