"""
Sistema de Apuestas Deportivas para Tenis
=========================================

Un sistema completo para automatización de apuestas deportivas que incluye:
- Ingesta de datos en tiempo real desde 1xBet
- Procesamiento y almacenamiento de datos
- Modelos de machine learning para estimación de probabilidades
- Detección de value bets y cálculo de stakes
- Dashboard interactivo y backtesting
- Sistema de alertas y automatización

Autor: Sistema de Apuestas Deportivas
Versión: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Sistema de Apuestas Deportivas"
__description__ = "Sistema completo de automatización de apuestas para tenis"

from config import config
from data_ingest import TennisDataIngestor

__all__ = ['config', 'TennisDataIngestor']
