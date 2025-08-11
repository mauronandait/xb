"""
Módulo de detección de señales de apuesta para el sistema de tenis.
Incluye lógica para identificar value bets, calcular stakes Kelly y generar recomendaciones.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import logging
from datetime import datetime
from src.config import config

logger = logging.getLogger(__name__)

class BettingSignalDetector:
    """Clase para detectar señales de apuesta en partidos de tenis."""
    
    def __init__(self, bankroll: float = None, kelly_fraction: float = None):
        """
        Inicializar el detector de señales.
        
        Args:
            bankroll: Capital disponible para apuestas
            kelly_fraction: Fracción del stake Kelly a usar (0-1)
        """
        self.bankroll = bankroll or config.BANKROLL
        self.kelly_fraction = kelly_fraction or config.KELLY_FRACTION
        self.min_ev_threshold = config.MIN_EV_THRESHOLD
        self.max_stake_percent = config.MAX_STAKE_PERCENT
        self.logger = logging.getLogger(__name__)
        
    def calculate_expected_value(self, model_prob: float, odds: float) -> float:
        """
        Calcular el valor esperado (EV) de una apuesta.
        
        Args:
            model_prob: Probabilidad del modelo
            odds: Cuota ofrecida
            
        Returns:
            Valor esperado como decimal
        """
        try:
            ev = (model_prob * odds) - 1
            return round(ev, 4)
        except Exception as e:
            self.logger.error(f"Error calculando EV: {e}")
            return 0.0
    
    def calculate_kelly_stake(self, model_prob: float, odds: float) -> float:
        """
        Calcular el stake Kelly óptimo.
        
        Args:
            model_prob: Probabilidad del modelo
            odds: Cuota ofrecida
            
        Returns:
            Porcentaje del bankroll a apostar (0-1)
        """
        try:
            if odds <= 1:
                return 0.0
            
            kelly_stake = (model_prob * odds - 1) / (odds - 1)
            # Aplicar fracción Kelly y limitar al máximo permitido
            fractional_stake = kelly_stake * self.kelly_fraction
            max_stake = self.max_stake_percent / 100
            
            return max(0.0, min(fractional_stake, max_stake))
            
        except Exception as e:
            self.logger.error(f"Error calculando stake Kelly: {e}")
            return 0.0
    
    def calculate_recommended_stake(self, kelly_stake: float) -> float:
        """
        Calcular el stake recomendado en términos monetarios.
        
        Args:
            kelly_stake: Stake Kelly como porcentaje (0-1)
            
        Returns:
            Cantidad de dinero a apostar
        """
        try:
            return round(kelly_stake * self.bankroll, 2)
        except Exception as e:
            self.logger.error(f"Error calculando stake recomendado: {e}")
            return 0.0
    
    def detect_value_bets(self, df: pd.DataFrame, model_column: str = 'model_prob') -> pd.DataFrame:
        """
        Detectar value bets en un DataFrame de partidos.
        
        Args:
            df: DataFrame con datos de partidos
            model_column: Nombre de la columna con probabilidades del modelo
            
        Returns:
            DataFrame con señales de apuesta detectadas
        """
        try:
            signals = []
            
            for _, row in df.iterrows():
                # Analizar jugador 1
                if pd.notna(row.get('player1_odds')) and pd.notna(row.get(f'{model_column}_player1')):
                    ev1 = self.calculate_expected_value(row[f'{model_column}_player1'], row['player1_odds'])
                    kelly1 = self.calculate_kelly_stake(row[f'{model_column}_player1'], row['player1_odds'])
                    
                    if ev1 > self.min_ev_threshold and kelly1 > 0:
                        signal = {
                            'match_id': row['match_id'],
                            'selection': row['player1'],
                            'opponent': row['player2'],
                            'tournament': row.get('tournament', 'Unknown'),
                            'match_time': row['match_time'],
                            'odds': row['player1_odds'],
                            'model_prob': row[f'{model_column}_player1'],
                            'implied_prob': row.get('player1_implied_prob', 1/row['player1_odds']),
                            'ev': ev1,
                            'kelly_stake': kelly1,
                            'recommended_stake': self.calculate_recommended_stake(kelly1),
                            'selection_type': 'player1'
                        }
                        signals.append(signal)
                
                # Analizar jugador 2
                if pd.notna(row.get('player2_odds')) and pd.notna(row.get(f'{model_column}_player2')):
                    ev2 = self.calculate_expected_value(row[f'{model_column}_player2'], row['player2_odds'])
                    kelly2 = self.calculate_kelly_stake(row[f'{model_column}_player2'], row['player2_odds'])
                    
                    if ev2 > self.min_ev_threshold and kelly2 > 0:
                        signal = {
                            'match_id': row['match_id'],
                            'selection': row['player2'],
                            'opponent': row['player1'],
                            'tournament': row.get('tournament', 'Unknown'),
                            'match_time': row['match_time'],
                            'odds': row['player2_odds'],
                            'model_prob': row[f'{model_column}_player2'],
                            'implied_prob': row.get('player2_implied_prob', 1/row['player2_odds']),
                            'ev': ev2,
                            'kelly_stake': kelly2,
                            'recommended_stake': self.calculate_recommended_stake(kelly2),
                            'selection_type': 'player2'
                        }
                        signals.append(signal)
            
            if signals:
                signals_df = pd.DataFrame(signals)
                # Ordenar por EV descendente
                signals_df = signals_df.sort_values('ev', ascending=False).reset_index(drop=True)
                self.logger.info(f"Se detectaron {len(signals_df)} señales de value bet")
                return signals_df
            else:
                self.logger.info("No se detectaron señales de value bet")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error detectando value bets: {e}")
            raise
    
    def filter_signals_by_confidence(self, signals_df: pd.DataFrame, min_confidence: float = 0.7) -> pd.DataFrame:
        """
        Filtrar señales por nivel de confianza del modelo.
        
        Args:
            signals_df: DataFrame con señales de apuesta
            min_confidence: Confianza mínima requerida (0-1)
            
        Returns:
            DataFrame filtrado con señales de alta confianza
        """
        try:
            if signals_df.empty:
                return signals_df
            
            # Filtrar por confianza del modelo
            high_confidence = signals_df[
                (signals_df['model_prob'] >= min_confidence) | 
                (signals_df['model_prob'] <= (1 - min_confidence))
            ].copy()
            
            # Agregar columna de confianza
            high_confidence['confidence'] = high_confidence['model_prob'].apply(
                lambda x: max(x, 1-x)
            )
            
            self.logger.info(f"Señales filtradas por confianza: {len(high_confidence)} de {len(signals_df)}")
            return high_confidence
            
        except Exception as e:
            self.logger.error(f"Error filtrando por confianza: {e}")
            raise
    
    def calculate_portfolio_metrics(self, signals_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calcular métricas del portafolio de apuestas.
        
        Args:
            signals_df: DataFrame con señales de apuesta
            
        Returns:
            Diccionario con métricas del portafolio
        """
        try:
            if signals_df.empty:
                return {
                    'total_signals': 0,
                    'total_stake': 0.0,
                    'avg_ev': 0.0,
                    'max_stake': 0.0,
                    'portfolio_risk': 0.0
                }
            
            metrics = {
                'total_signals': len(signals_df),
                'total_stake': signals_df['recommended_stake'].sum(),
                'avg_ev': signals_df['ev'].mean(),
                'max_stake': signals_df['recommended_stake'].max(),
                'portfolio_risk': (signals_df['recommended_stake'] / self.bankroll).sum()
            }
            
            # Agregar métricas adicionales
            metrics['avg_odds'] = signals_df['odds'].mean()
            metrics['avg_model_prob'] = signals_df['model_prob'].mean()
            metrics['stake_percentage'] = (metrics['total_stake'] / self.bankroll) * 100
            
            self.logger.info(f"Métricas del portafolio calculadas: {metrics['total_signals']} señales")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculando métricas del portafolio: {e}")
            raise
    
    def generate_betting_recommendations(self, df: pd.DataFrame, 
                                       model_column: str = 'model_prob',
                                       min_confidence: float = 0.7) -> Dict:
        """
        Generar recomendaciones completas de apuestas.
        
        Args:
            df: DataFrame con datos de partidos
            model_column: Nombre de la columna con probabilidades del modelo
            min_confidence: Confianza mínima requerida
            
        Returns:
            Diccionario con señales y métricas del portafolio
        """
        try:
            self.logger.info("Generando recomendaciones de apuestas")
            
            # Detectar value bets
            signals = self.detect_value_bets(df, model_column)
            
            if signals.empty:
                return {
                    'signals': pd.DataFrame(),
                    'portfolio_metrics': self.calculate_portfolio_metrics(signals),
                    'recommendations': []
                }
            
            # Filtrar por confianza
            high_confidence_signals = self.filter_signals_by_confidence(signals, min_confidence)
            
            # Calcular métricas del portafolio
            portfolio_metrics = self.calculate_portfolio_metrics(high_confidence_signals)
            
            # Generar recomendaciones
            recommendations = []
            for _, signal in high_confidence_signals.iterrows():
                rec = {
                    'action': 'APOSTAR',
                    'match': f"{signal['selection']} vs {signal['opponent']}",
                    'tournament': signal['tournament'],
                    'selection': signal['selection'],
                    'odds': signal['odds'],
                    'stake': f"${signal['recommended_stake']:.2f}",
                    'ev': f"{signal['ev']:.1%}",
                    'confidence': f"{signal['confidence']:.1%}"
                }
                recommendations.append(rec)
            
            result = {
                'signals': high_confidence_signals,
                'portfolio_metrics': portfolio_metrics,
                'recommendations': recommendations
            }
            
            self.logger.info(f"Recomendaciones generadas: {len(recommendations)} apuestas recomendadas")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generando recomendaciones: {e}")
            raise
    
    def save_signals(self, signals_df: pd.DataFrame, filepath: str) -> None:
        """
        Guardar señales de apuesta en archivo.
        
        Args:
            signals_df: DataFrame con señales
            filepath: Ruta del archivo donde guardar
        """
        try:
            signals_df.to_csv(filepath, index=False)
            self.logger.info(f"Señales guardadas en: {filepath}")
        except Exception as e:
            self.logger.error(f"Error guardando señales: {e}")
            raise

# Función de conveniencia para uso directo
def detect_tennis_signals(df: pd.DataFrame, 
                         model_column: str = 'model_prob',
                         bankroll: float = None) -> Dict:
    """
    Función de conveniencia para detectar señales de tenis.
    
    Args:
        df: DataFrame con datos de partidos
        model_column: Columna con probabilidades del modelo
        bankroll: Capital disponible
        
    Returns:
        Diccionario con señales y recomendaciones
    """
    detector = BettingSignalDetector(bankroll=bankroll)
    return detector.generate_betting_recommendations(df, model_column)

