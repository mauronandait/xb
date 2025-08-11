#!/usr/bin/env python3
"""
Sistema de generación de señales de apuestas para tenis.
Analiza partidos y genera señales de "value betting" basadas en análisis estadístico.
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from config import config
from database import db_manager
from alerts import send_value_bet_alert

# Configurar logging
logger = logging.getLogger(__name__)

class TennisBettingSignals:
    """Sistema de generación de señales de apuestas para tenis."""
    
    def __init__(self):
        """Inicializar generador de señales."""
        self.logger = logging.getLogger(__name__)
        
        # Configuración de señales
        self.min_ev_threshold = config.MIN_EV_THRESHOLD
        self.min_kelly_threshold = 0.01
        self.max_stake_percent = config.MAX_STAKE_PERCENT / 100
        self.kelly_fraction = config.KELLY_FRACTION
        
        # Umbrales de confianza
        self.high_confidence_threshold = 0.15
        self.medium_confidence_threshold = 0.08
        self.low_confidence_threshold = 0.05
        
        # Factores de ponderación
        self.tournament_weights = {
            'grand_slam': 1.2,
            'atp_1000': 1.1,
            'atp_500': 1.0,
            'atp_250': 0.9,
            'challenger': 0.8,
            'other': 0.7
        }
        
        self.surface_weights = {
            'hard': 1.0,
            'clay': 1.0,
            'grass': 1.0,
            'carpet': 0.9
        }
    
    def generate_betting_signals(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generar señales de apuestas para una lista de partidos.
        
        Args:
            matches: Lista de partidos procesados
            
        Returns:
            Lista de señales de apuestas generadas
        """
        if not matches:
            self.logger.warning("No hay partidos para generar señales")
            return []
        
        self.logger.info(f"Generando señales de apuestas para {len(matches)} partidos")
        
        signals = []
        
        for match in matches:
            try:
                signal = self._analyze_match_for_signals(match)
                if signal:
                    signals.append(signal)
            except Exception as e:
                self.logger.warning(f"Error analizando partido para señales: {e}")
                continue
        
        # Ordenar señales por confianza y valor esperado
        signals = self._rank_signals(signals)
        
        self.logger.info(f"Señales generadas: {len(signals)} oportunidades identificadas")
        return signals
    
    def _analyze_match_for_signals(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analizar un partido individual para generar señales.
        
        Args:
            match: Datos del partido
            
        Returns:
            Señal de apuesta o None si no hay oportunidad
        """
        try:
            # Verificar que el partido tenga todos los datos necesarios
            required_fields = [
                'player1', 'player2', 'odds', 'player1_implied_prob', 
                'player2_implied_prob', 'player1_ev', 'player2_ev'
            ]
            
            if not all(field in match for field in required_fields):
                return None
            
            # Analizar oportunidades para ambos jugadores
            signals = []
            
            # Analizar jugador 1
            signal1 = self._analyze_player_opportunity(
                match, 'player1', match['player1_odds'], 
                match['player1_implied_prob'], match['player1_ev']
            )
            if signal1:
                signals.append(signal1)
            
            # Analizar jugador 2
            signal2 = self._analyze_player_opportunity(
                match, 'player2', match['player2_odds'], 
                match['player2_implied_prob'], match['player2_ev']
            )
            if signal2:
                signals.append(signal2)
            
            # Si no hay señales individuales, verificar oportunidades de arbitraje
            if not signals:
                arbitrage_signal = self._check_arbitrage_opportunity(match)
                if arbitrage_signal:
                    signals.append(arbitrage_signal)
            
            # Retornar la mejor señal si existe
            if signals:
                return max(signals, key=lambda x: x['confidence_score'])
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error analizando partido: {e}")
            return None
    
    def _analyze_player_opportunity(
        self, match: Dict[str, Any], player_key: str, 
        odds: float, implied_prob: float, ev: float
    ) -> Optional[Dict[str, Any]]:
        """
        Analizar oportunidad de apuesta para un jugador específico.
        
        Args:
            match: Datos del partido
            player_key: Clave del jugador ('player1' o 'player2')
            odds: Cuotas del jugador
            implied_prob: Probabilidad implícita
            ev: Valor esperado
            
        Returns:
            Señal de apuesta o None si no hay oportunidad
        """
        try:
            # Verificar umbral mínimo de valor esperado
            if ev < self.min_ev_threshold:
                return None
            
            # Calcular Kelly Criterion
            kelly = ev / (odds - 1) if ev > 0 else 0
            
            # Verificar umbral mínimo de Kelly
            if kelly < self.min_kelly_threshold:
                return None
            
            # Calcular stake recomendado
            recommended_stake = min(kelly * self.kelly_fraction, self.max_stake_percent)
            
            # Calcular puntuación de confianza
            confidence_score = self._calculate_confidence_score(
                match, ev, kelly, implied_prob
            )
            
            # Determinar nivel de confianza
            confidence_level = self._determine_confidence_level(confidence_score)
            
            # Generar señal
            signal = {
                'match_id': match.get('match_id', f"{match['player1']}_{match['player2']}"),
                'tournament': match['tournament'],
                'player1': match['player1'],
                'player2': match['player2'],
                'match_time': match.get('match_time'),
                'surface': match.get('surface', 'hard'),
                'round': match.get('round', 'Ronda'),
                'recommended_bet': player_key,
                'player_name': match[player_key],
                'odds': odds,
                'implied_probability': implied_prob,
                'expected_value': ev,
                'kelly_criterion': kelly,
                'recommended_stake': recommended_stake,
                'confidence_score': confidence_score,
                'confidence_level': confidence_level,
                'signal_type': 'value_bet',
                'generated_at': datetime.utcnow(),
                'match_data': match
            }
            
            return signal
            
        except Exception as e:
            self.logger.warning(f"Error analizando oportunidad del jugador: {e}")
            return None
    
    def _check_arbitrage_opportunity(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Verificar si existe oportunidad de arbitraje.
        
        Args:
            match: Datos del partido
            
        Returns:
            Señal de arbitraje o None si no hay oportunidad
        """
        try:
            odds1 = match['player1_odds']
            odds2 = match['player2_odds']
            
            # Calcular probabilidades implícitas
            prob1 = 1 / odds1
            prob2 = 1 / odds2
            
            # Verificar si hay arbitraje (probabilidades suman menos de 1)
            total_prob = prob1 + prob2
            
            if total_prob < 0.98:  # Margen mínimo del 2%
                # Calcular stakes óptimos para arbitraje
                stake1 = 1 / (odds1 * total_prob)
                stake2 = 1 / (odds2 * total_prob)
                
                # Calcular ganancia garantizada
                guaranteed_profit = 1 - total_prob
                
                signal = {
                    'match_id': match.get('match_id', f"{match['player1']}_{match['player2']}"),
                    'tournament': match['tournament'],
                    'player1': match['player1'],
                    'player2': match['player2'],
                    'match_time': match.get('match_time'),
                    'surface': match.get('surface', 'hard'),
                    'round': match.get('round', 'Ronda'),
                    'recommended_bet': 'arbitrage',
                    'player_name': 'Arbitraje',
                    'odds': [odds1, odds2],
                    'implied_probability': [prob1, prob2],
                    'expected_value': guaranteed_profit,
                    'kelly_criterion': 0.0,
                    'recommended_stake': [stake1, stake2],
                    'confidence_score': 0.95,  # Arbitraje tiene alta confianza
                    'confidence_level': 'high',
                    'signal_type': 'arbitrage',
                    'guaranteed_profit': guaranteed_profit,
                    'generated_at': datetime.utcnow(),
                    'match_data': match
                }
                
                return signal
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error verificando arbitraje: {e}")
            return None
    
    def _calculate_confidence_score(
        self, match: Dict[str, Any], ev: float, kelly: float, implied_prob: float
    ) -> float:
        """
        Calcular puntuación de confianza para una señal.
        
        Args:
            match: Datos del partido
            ev: Valor esperado
            kelly: Kelly Criterion
            implied_prob: Probabilidad implícita
            
        Returns:
            Puntuación de confianza (0-1)
        """
        try:
            score = 0.0
            
            # Factor de valor esperado (40% del peso)
            ev_score = min(ev / 0.20, 1.0)  # Normalizar a máximo 20%
            score += ev_score * 0.4
            
            # Factor de Kelly Criterion (30% del peso)
            kelly_score = min(kelly / 0.10, 1.0)  # Normalizar a máximo 10%
            score += kelly_score * 0.3
            
            # Factor de probabilidad implícita (20% del peso)
            # Preferir probabilidades moderadas (no extremas)
            if 0.2 <= implied_prob <= 0.8:
                prob_score = 1.0
            else:
                prob_score = 1.0 - abs(0.5 - implied_prob) * 2
            
            score += prob_score * 0.2
            
            # Factor de calidad del torneo (10% del peso)
            tournament_weight = self.tournament_weights.get(
                match.get('tournament_level', 'other'), 0.7
            )
            score += tournament_weight * 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.warning(f"Error calculando puntuación de confianza: {e}")
            return 0.5
    
    def _determine_confidence_level(self, confidence_score: float) -> str:
        """
        Determinar nivel de confianza basado en la puntuación.
        
        Args:
            confidence_score: Puntuación de confianza (0-1)
            
        Returns:
            Nivel de confianza ('high', 'medium', 'low')
        """
        if confidence_score >= self.high_confidence_threshold:
            return 'high'
        elif confidence_score >= self.medium_confidence_threshold:
            return 'medium'
        else:
            return 'low'
    
    def _rank_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ordenar señales por relevancia y confianza.
        
        Args:
            signals: Lista de señales
            
        Returns:
            Lista de señales ordenadas
        """
        try:
            # Ordenar por confianza y valor esperado
            ranked_signals = sorted(
                signals,
                key=lambda x: (x['confidence_score'], x['expected_value']),
                reverse=True
            )
            
            # Agregar ranking
            for i, signal in enumerate(ranked_signals):
                signal['rank'] = i + 1
                signal['priority'] = 'high' if i < 5 else 'medium' if i < 15 else 'low'
            
            return ranked_signals
            
        except Exception as e:
            self.logger.warning(f"Error ordenando señales: {e}")
            return signals
    
    def filter_signals_by_criteria(
        self, signals: List[Dict[str, Any]], 
        min_confidence: str = 'low',
        min_ev: float = 0.0,
        max_stake: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Filtrar señales por criterios específicos.
        
        Args:
            signals: Lista de señales
            min_confidence: Confianza mínima ('low', 'medium', 'high')
            min_ev: Valor esperado mínimo
            max_stake: Stake máximo permitido
            
        Returns:
            Lista de señales filtradas
        """
        try:
            confidence_levels = {'low': 0, 'medium': 1, 'high': 2}
            min_confidence_level = confidence_levels.get(min_confidence, 0)
            
            filtered_signals = []
            
            for signal in signals:
                # Verificar nivel de confianza
                signal_confidence = confidence_levels.get(signal['confidence_level'], 0)
                if signal_confidence < min_confidence_level:
                    continue
                
                # Verificar valor esperado
                if signal['expected_value'] < min_ev:
                    continue
                
                # Verificar stake máximo
                if isinstance(signal['recommended_stake'], list):
                    max_signal_stake = max(signal['recommended_stake'])
                else:
                    max_signal_stake = signal['recommended_stake']
                
                if max_signal_stake > max_stake:
                    continue
                
                filtered_signals.append(signal)
            
            self.logger.info(f"Señales filtradas: {len(filtered_signals)} de {len(signals)}")
            return filtered_signals
            
        except Exception as e:
            self.logger.warning(f"Error filtrando señales: {e}")
            return signals
    
    def generate_signals_summary(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generar resumen de las señales.
        
        Args:
            signals: Lista de señales
            
        Returns:
            Resumen de señales
        """
        try:
            if not signals:
                return {
                    'total_signals': 0,
                    'high_confidence': 0,
                    'medium_confidence': 0,
                    'low_confidence': 0,
                    'total_ev': 0.0,
                    'average_ev': 0.0,
                    'arbitrage_opportunities': 0,
                    'value_bets': 0
                }
            
            # Contar por nivel de confianza
            confidence_counts = {
                'high': len([s for s in signals if s['confidence_level'] == 'high']),
                'medium': len([s for s in signals if s['confidence_level'] == 'medium']),
                'low': len([s for s in signals if s['confidence_level'] == 'low'])
            }
            
            # Calcular estadísticas de valor esperado
            ev_values = [s['expected_value'] for s in signals if s['signal_type'] == 'value_bet']
            total_ev = sum(ev_values) if ev_values else 0.0
            average_ev = total_ev / len(ev_values) if ev_values else 0.0
            
            # Contar tipos de señales
            arbitrage_count = len([s for s in signals if s['signal_type'] == 'arbitrage'])
            value_bet_count = len([s for s in signals if s['signal_type'] == 'value_bet'])
            
            summary = {
                'total_signals': len(signals),
                'high_confidence': confidence_counts['high'],
                'medium_confidence': confidence_counts['medium'],
                'low_confidence': confidence_counts['low'],
                'total_ev': round(total_ev, 4),
                'average_ev': round(average_ev, 4),
                'arbitrage_opportunities': arbitrage_count,
                'value_bets': value_bet_count,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.warning(f"Error generando resumen: {e}")
            return {}
    
    def run_signal_generation(self, matches: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Ejecutar generación completa de señales.
        
        Args:
            matches: Lista de partidos procesados
            
        Returns:
            Tupla con (señales, resumen)
        """
        try:
            self.logger.info("Iniciando generación de señales de apuestas")
            
            # Generar señales
            signals = self.generate_betting_signals(matches)
            
            # Enviar alertas para señales de alta confianza
            self._send_alerts_for_signals(signals)
            
            # Generar resumen
            summary = self.generate_signals_summary(signals)
            
            self.logger.info(f"Generación de señales completada: {len(signals)} señales generadas")
            
            return signals, summary
            
        except Exception as e:
            self.logger.error(f"Error en generación de señales: {e}")
            return [], {}
    
    def _send_alerts_for_signals(self, signals: List[Dict[str, Any]]):
        """
        Enviar alertas para señales generadas.
        
        Args:
            signals: Lista de señales de apuestas
        """
        try:
            # Filtrar señales de alta confianza para alertas
            high_confidence_signals = [
                s for s in signals 
                if s['confidence_level'] == 'high' and s['signal_type'] == 'value_bet'
            ]
            
            for signal in high_confidence_signals:
                try:
                    # Preparar datos para la alerta
                    alert_data = {
                        'player_name': signal['player_name'],
                        'player2': signal['player2'],
                        'tournament': signal['tournament'],
                        'surface': signal['surface'],
                        'round': signal['round'],
                        'odds': signal['odds'],
                        'model_probability': signal.get('model_probability', 0),
                        'implied_probability': signal['implied_probability'],
                        'expected_value': signal['expected_value'],
                        'kelly_stake': signal['kelly_criterion'],
                        'recommended_stake': signal['recommended_stake'],
                        'confidence_level': signal['confidence_level']
                    }
                    
                    # Enviar alerta
                    success = send_value_bet_alert(alert_data)
                    
                    if success:
                        self.logger.info(f"Alerta enviada para value bet: {signal['player_name']}")
                    else:
                        self.logger.warning(f"Error enviando alerta para: {signal['player_name']}")
                        
                except Exception as e:
                    self.logger.error(f"Error enviando alerta individual: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error en sistema de alertas: {e}")

# Función de conveniencia para uso directo
def generate_tennis_betting_signals(matches: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Generar señales de apuestas para tenis usando el sistema completo.
    
    Args:
        matches: Lista de partidos procesados
        
    Returns:
        Tupla con (señales, resumen)
    """
    signal_generator = TennisBettingSignals()
    return signal_generator.run_signal_generation(matches)

if __name__ == "__main__":
    # Ejecutar generación de señales si se llama directamente
    from data_ingest import run_tennis_data_ingestion
    from data_clean import clean_tennis_data
    
    # Obtener y limpiar datos
    matches = run_tennis_data_ingestion()
    cleaned_matches = clean_tennis_data(matches)
    
    # Generar señales
    signals, summary = generate_tennis_betting_signals(cleaned_matches)
    
    print(f"✅ Señales generadas: {len(signals)} oportunidades identificadas")
    print(f"📊 Resumen: {summary}")

