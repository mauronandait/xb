"""
Módulo de limpieza y procesamiento de datos para el sistema de apuestas de tenis.
Incluye funciones para limpiar datos crudos, calcular estadísticas y preparar datos para ML.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
from src.config import config

logger = logging.getLogger(__name__)

class TennisDataCleaner:
    """Clase para limpiar y procesar datos de tenis."""
    
    def __init__(self):
        """Inicializar el limpiador de datos."""
        self.logger = logging.getLogger(__name__)
        
    def clean_match_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """
        Limpiar datos crudos de partidos de tenis.
        
        Args:
            raw_data: Lista de diccionarios con datos crudos
            
        Returns:
            DataFrame limpio con datos procesados
        """
        try:
            df = pd.DataFrame(raw_data)
            
            # Limpiar nombres de columnas
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            
            # Convertir fechas
            if 'match_time' in df.columns:
                df['match_time'] = pd.to_datetime(df['match_time'], errors='coerce')
            
            # Limpiar nombres de jugadores
            if 'player1' in df.columns:
                df['player1'] = df['player1'].str.strip()
            if 'player2' in df.columns:
                df['player2'] = df['player2'].str.strip()
            
            # Limpiar cuotas
            odds_columns = [col for col in df.columns if 'odds' in col]
            for col in odds_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Filtrar cuotas válidas (entre 1.01 y 1000)
                df[col] = df[col].clip(1.01, 1000)
            
            # Limpiar torneos
            if 'tournament' in df.columns:
                df['tournament'] = df['tournament'].str.strip()
            
            # Eliminar filas con datos faltantes críticos
            critical_columns = ['player1', 'player2', 'match_time']
            df = df.dropna(subset=critical_columns)
            
            # Generar ID único para cada partido
            df['match_id'] = df.apply(
                lambda row: f"{row['player1']}_{row['player2']}_{row['tournament']}_{row['match_time'].strftime('%Y%m%d')}",
                axis=1
            )
            
            self.logger.info(f"Datos limpios: {len(df)} partidos procesados")
            return df
            
        except Exception as e:
            self.logger.error(f"Error limpiando datos: {e}")
            raise
    
    def calculate_implied_probabilities(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcular probabilidades implícitas a partir de las cuotas.
        
        Args:
            df: DataFrame con datos de partidos
            
        Returns:
            DataFrame con probabilidades implícitas calculadas
        """
        try:
            df = df.copy()
            
            # Calcular probabilidades implícitas
            if 'player1_odds' in df.columns and 'player2_odds' in df.columns:
                df['player1_implied_prob'] = 1 / df['player1_odds']
                df['player2_implied_prob'] = 1 / df['player2_odds']
                
                # Calcular margen de la casa de apuestas
                df['margin'] = (df['player1_implied_prob'] + df['player2_implied_prob']) - 1
                
                # Normalizar probabilidades (eliminar margen)
                df['player1_prob'] = df['player1_implied_prob'] / (1 + df['margin'])
                df['player2_prob'] = df['player2_implied_prob'] / (1 + df['margin'])
                
                # Verificar que las probabilidades sumen 1
                df['prob_sum'] = df['player1_prob'] + df['player2_prob']
                
            self.logger.info("Probabilidades implícitas calculadas")
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculando probabilidades: {e}")
            raise
    
    def add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Agregar características estadísticas básicas.
        
        Args:
            df: DataFrame con datos de partidos
            
        Returns:
            DataFrame con características adicionales
        """
        try:
            df = df.copy()
            
            # Agregar características temporales
            if 'match_time' in df.columns:
                df['hour'] = df['match_time'].dt.hour
                df['day_of_week'] = df['match_time'].dt.dayofweek
                df['month'] = df['match_time'].dt.month
                df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            
            # Agregar características de cuotas
            if 'player1_odds' in df.columns and 'player2_odds' in df.columns:
                df['odds_ratio'] = df['player1_odds'] / df['player2_odds']
                df['odds_difference'] = df['player1_odds'] - df['player2_odds']
                df['is_favorite'] = (df['player1_odds'] < df['player2_odds']).astype(int)
            
            # Agregar características de probabilidades
            if 'player1_prob' in df.columns and 'player2_prob' in df.columns:
                df['prob_difference'] = df['player1_prob'] - df['player2_prob']
                df['prob_ratio'] = df['player1_prob'] / df['player2_prob']
            
            self.logger.info("Características estadísticas agregadas")
            return df
            
        except Exception as e:
            self.logger.error(f"Error agregando características: {e}")
            raise
    
    def filter_valid_matches(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtrar partidos válidos para análisis.
        
        Args:
            df: DataFrame con datos de partidos
            
        Returns:
            DataFrame filtrado con solo partidos válidos
        """
        try:
            df = df.copy()
            
            # Filtrar por cuotas válidas
            if 'player1_odds' in df.columns and 'player2_odds' in df.columns:
                df = df[
                    (df['player1_odds'] >= 1.01) & 
                    (df['player2_odds'] >= 1.01) &
                    (df['player1_odds'] <= 1000) & 
                    (df['player2_odds'] <= 1000)
                ]
            
            # Filtrar por probabilidades válidas
            if 'player1_prob' in df.columns and 'player2_prob' in df.columns:
                df = df[
                    (df['player1_prob'] > 0) & 
                    (df['player2_prob'] > 0) &
                    (df['player1_prob'] < 1) & 
                    (df['player2_prob'] < 1)
                ]
            
            # Filtrar por margen razonable
            if 'margin' in df.columns:
                df = df[df['margin'] <= 0.15]  # Máximo 15% de margen
            
            # Filtrar partidos futuros
            if 'match_time' in df.columns:
                df = df[df['match_time'] > datetime.now()]
            
            self.logger.info(f"Partidos válidos filtrados: {len(df)}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error filtrando partidos: {e}")
            raise
    
    def process_tournament_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Procesar datos específicos de torneos.
        
        Args:
            df: DataFrame con datos de partidos
            
        Returns:
            DataFrame con información de torneos procesada
        """
        try:
            df = df.copy()
            
            # Categorizar torneos por nivel
            if 'tournament' in df.columns:
                # Grand Slams
                grand_slams = ['Australian Open', 'French Open', 'Wimbledon', 'US Open']
                df['tournament_level'] = df['tournament'].apply(
                    lambda x: 'Grand Slam' if x in grand_slams else 'Regular'
                )
                
                # Categorizar por superficie (si está disponible)
                # Esto se puede expandir con más información
                df['surface_type'] = 'Unknown'  # Placeholder
            
            self.logger.info("Datos de torneos procesados")
            return df
            
        except Exception as e:
            self.logger.error(f"Error procesando torneos: {e}")
            raise
    
    def run_full_cleaning_pipeline(self, raw_data: List[Dict]) -> pd.DataFrame:
        """
        Ejecutar el pipeline completo de limpieza de datos.
        
        Args:
            raw_data: Lista de diccionarios con datos crudos
            
        Returns:
            DataFrame completamente procesado y listo para ML
        """
        try:
            self.logger.info("Iniciando pipeline de limpieza de datos")
            
            # Paso 1: Limpieza básica
            df = self.clean_match_data(raw_data)
            
            # Paso 2: Calcular probabilidades
            df = self.calculate_implied_probabilities(df)
            
            # Paso 3: Agregar características
            df = self.add_statistical_features(df)
            
            # Paso 4: Procesar torneos
            df = self.process_tournament_data(df)
            
            # Paso 5: Filtrar partidos válidos
            df = self.filter_valid_matches(df)
            
            # Paso 6: Ordenar por fecha
            if 'match_time' in df.columns:
                df = df.sort_values('match_time')
            
            # Paso 7: Resetear índice
            df = df.reset_index(drop=True)
            
            self.logger.info(f"Pipeline de limpieza completado: {len(df)} partidos válidos")
            return df
            
        except Exception as e:
            self.logger.error(f"Error en pipeline de limpieza: {e}")
            raise
    
    def save_cleaned_data(self, df: pd.DataFrame, filepath: str) -> None:
        """
        Guardar datos limpios en archivo.
        
        Args:
            df: DataFrame con datos limpios
            filepath: Ruta del archivo donde guardar
        """
        try:
            df.to_csv(filepath, index=False)
            self.logger.info(f"Datos guardados en: {filepath}")
        except Exception as e:
            self.logger.error(f"Error guardando datos: {e}")
            raise

# Función de conveniencia para uso directo
def clean_tennis_data(raw_data: List[Dict]) -> pd.DataFrame:
    """
    Función de conveniencia para limpiar datos de tenis.
    
    Args:
        raw_data: Lista de diccionarios con datos crudos
        
    Returns:
        DataFrame limpio y procesado
    """
    cleaner = TennisDataCleaner()
    return cleaner.run_full_cleaning_pipeline(raw_data)

