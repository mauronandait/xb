"""
Módulo de configuración para el sistema de apuestas de tenis.
Lee variables de entorno y proporciona configuración centralizada.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
env_path = Path(__file__).parent.parent / "config" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Intentar cargar desde directorio actual

class Config:
    """Clase de configuración centralizada."""
    
    # Base de datos
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'tennis_betting')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    
    # 1xBet
    ONEXBET_API_URL = os.getenv('ONEXBET_API_URL', 'https://1xbet.com/api')
    ONEXBET_API_KEY = os.getenv('ONEXBET_API_KEY', '')
    
    # Scraping
    SCRAPING_ENABLED = os.getenv('SCRAPING_ENABLED', 'true').lower() == 'true'
    SCRAPING_DELAY = int(os.getenv('SCRAPING_DELAY', 2))
    USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Apuestas
    BANKROLL = float(os.getenv('BANKROLL', 10000))
    KELLY_FRACTION = float(os.getenv('KELLY_FRACTION', 0.5))
    MAX_STAKE_PERCENT = float(os.getenv('MAX_STAKE_PERCENT', 5))
    MIN_EV_THRESHOLD = float(os.getenv('MIN_EV_THRESHOLD', 0.05))
    
    # Alertas
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER', '')
    EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', 587))
    EMAIL_USER = os.getenv('EMAIL_USER', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/tennis_betting.log')
    
    # Modelos
    MODEL_UPDATE_FREQUENCY = int(os.getenv('MODEL_UPDATE_FREQUENCY', 3600))
    HISTORICAL_DATA_DAYS = int(os.getenv('HISTORICAL_DATA_DAYS', 365))
    
    @classmethod
    def get_database_url(cls) -> str:
        """Obtener URL de conexión a la base de datos."""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def setup_logging(cls):
        """Configurar logging del sistema."""
        # Crear directorio de logs si no existe
        log_dir = Path(cls.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(cls.LOG_FILE),
                logging.StreamHandler()
            ]
        )

# Instancia global de configuración
config = Config()
