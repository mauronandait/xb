#!/usr/bin/env python3
"""
Sistema de limpieza y preprocesamiento de datos para el sistema de apuestas de tenis.
Normaliza datos, calcula probabilidades y agrega características estadísticas.
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

from config import config
from database import db_manager

# Configurar logging
logger = logging.getLogger(__name__)

class TennisDataCleaner:
    """Sistema de limpieza y preprocesamiento de datos de tenis."""
    
    def __init__(self):
        """Inicializar limpiador de datos."""
        self.logger = logging.getLogger(__name__)
        self.min_odds_threshold = 1.01
        self.max_odds_threshold = 100.0
        self.min_probability_threshold = 0.001
        self.max_probability_threshold = 0.999
    
    def clean_matches_data(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Limpiar y validar datos de partidos.
        
        Args:
            matches: Lista de partidos crudos
            
        Returns:
            Lista de partidos limpios y validados
        """
        if not matches:
            self.logger.warning("No hay partidos para limpiar")
            return []
        
        self.logger.info(f"Iniciando limpieza de {len(matches)} partidos")
        
        cleaned_matches = []
        
        for match in matches:
            try:
                cleaned_match = self._clean_single_match(match)
                if cleaned_match:
                    cleaned_matches.append(cleaned_match)
            except Exception as e:
                self.logger.warning(f"Error limpiando partido: {e}")
                continue
        
        self.logger.info(f"Limpieza completada: {len(cleaned_matches)} partidos válidos")
        return cleaned_matches
    
    def _clean_single_match(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Limpiar un partido individual.
        
        Args:
            match: Datos del partido
            
        Returns:
            Partido limpio o None si no es válido
        """
        try:
            # Validar campos obligatorios
            required_fields = ['tournament', 'player1', 'player2']
            for field in required_fields:
                if not match.get(field) or not str(match[field]).strip():
                    return None
            
            # Limpiar y normalizar texto
            cleaned_match = {
                'tournament': self._clean_text(match['tournament']),
                'player1': self._clean_text(match['player1']),
                'player2': self._clean_text(match['player2']),
                'match_time': self._clean_datetime(match.get('match_time')),
                'surface': self._clean_surface(match.get('surface')),
                'round': self._clean_text(match.get('round', 'Ronda')),
                'status': self._clean_status(match.get('status', 'scheduled')),
                'raw_data': match.get('raw_data', {})
            }
            
            # Validar y limpiar cuotas
            if 'odds' in match and match['odds']:
                cleaned_odds = self._clean_odds(match['odds'])
                if cleaned_odds:
                    cleaned_match['odds'] = cleaned_odds
                    cleaned_match['player1_odds'] = cleaned_odds[0]
                    cleaned_match['player2_odds'] = cleaned_odds[1]
                else:
                    # Si no hay cuotas válidas, usar valores por defecto
                    cleaned_match['odds'] = [2.0, 2.0]
                    cleaned_match['player1_odds'] = 2.0
                    cleaned_match['player2_odds'] = 2.0
            else:
                # Valores por defecto si no hay cuotas
                cleaned_match['odds'] = [2.0, 2.0]
                cleaned_match['player1_odds'] = 2.0
                cleaned_match['player2_odds'] = 2.0
            
            # Agregar timestamp de limpieza
            cleaned_match['cleaned_at'] = datetime.utcnow()
            
            return cleaned_match
            
        except Exception as e:
            self.logger.warning(f"Error limpiando partido individual: {e}")
            return None
    
    def _clean_text(self, text: Any) -> str:
        """Limpiar y normalizar texto."""
        if not text:
            return ""
        
        # Convertir a string y limpiar
        text = str(text).strip()
        
        # Remover caracteres especiales problemáticos
        text = re.sub(r'[^\w\s\-\.]', '', text)
        
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _clean_datetime(self, dt: Any) -> Optional[datetime]:
        """Limpiar y validar datetime."""
        if not dt:
            return None
        
        try:
            if isinstance(dt, datetime):
                return dt
            elif isinstance(dt, str):
                # Intentar parsear diferentes formatos
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y-%m-%d',
                    '%d/%m/%Y %H:%M',
                    '%d/%m/%Y'
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(dt, fmt)
                    except ValueError:
                        continue
                
                # Si no funciona, usar fecha actual
                return datetime.now()
            else:
                return datetime.now()
                
        except Exception as e:
            self.logger.warning(f"Error limpiando datetime: {e}")
            return datetime.now()
    
    def _clean_surface(self, surface: Any) -> str:
        """Limpiar y normalizar superficie."""
        if not surface:
            return 'hard'
        
        surface = str(surface).lower().strip()
        
        # Mapear variaciones a valores estándar
        surface_mapping = {
            'hard': 'hard',
            'clay': 'clay',
            'grass': 'grass',
            'carpet': 'carpet',
            'indoor': 'hard',
            'outdoor': 'hard',
            'cement': 'hard',
            'concrete': 'hard',
            'synthetic': 'hard'
        }
        
        return surface_mapping.get(surface, 'hard')
    
    def _clean_status(self, status: Any) -> str:
        """Limpiar y normalizar estado del partido."""
        if not status:
            return 'scheduled'
        
        status = str(status).lower().strip()
        
        # Mapear variaciones a valores estándar
        status_mapping = {
            'scheduled': 'scheduled',
            'live': 'live',
            'finished': 'finished',
            'cancelled': 'cancelled',
            'postponed': 'postponed',
            'suspended': 'suspended'
        }
        
        return status_mapping.get(status, 'scheduled')
    
    def _clean_odds(self, odds: List[Any]) -> Optional[List[float]]:
        """
        Limpiar y validar cuotas.
        
        Args:
            odds: Lista de cuotas
            
        Returns:
            Lista de cuotas limpias o None si no son válidas
        """
        if not odds or len(odds) < 2:
            return None
        
        try:
            cleaned_odds = []
            
            for odd in odds[:2]:  # Solo primeras 2 cuotas
                if odd is None:
                    cleaned_odds.append(2.0)
                    continue
                
                try:
                    odd_value = float(odd)
                    
                    # Validar rango de cuotas
                    if odd_value < self.min_odds_threshold or odd_value > self.max_odds_threshold:
                        self.logger.warning(f"Cuota fuera de rango válido: {odd_value}")
                        cleaned_odds.append(2.0)
                    else:
                        cleaned_odds.append(round(odd_value, 2))
                        
                except (ValueError, TypeError):
                    self.logger.warning(f"Cuota no válida: {odd}")
                    cleaned_odds.append(2.0)
            
            # Verificar que tengamos 2 cuotas válidas
            if len(cleaned_odds) == 2:
                return cleaned_odds
            else:
                return None
                
        except Exception as e:
            self.logger.warning(f"Error limpiando cuotas: {e}")
            return None
    
    def calculate_implied_probabilities(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calcular probabilidades implícitas para todos los partidos.
        
        Args:
            matches: Lista de partidos limpios
            
        Returns:
            Lista de partidos con probabilidades calculadas
        """
        self.logger.info("Calculando probabilidades implícitas")
        
        for match in matches:
            try:
                if 'odds' in match and len(match['odds']) >= 2:
                    odds1, odds2 = match['odds'][0], match['odds'][1]
                    
                    # Calcular probabilidades implícitas
                    prob1 = 1 / odds1
                    prob2 = 1 / odds2
                    
                    # Calcular margen del bookmaker
                    total_prob = prob1 + prob2
                    margin = total_prob - 1
                    
                    # Ajustar probabilidades por el margen
                    if margin > 0:
                        prob1_adjusted = prob1 / total_prob
                        prob2_adjusted = prob2 / total_prob
                    else:
                        prob1_adjusted = prob1
                        prob2_adjusted = prob2
                    
                    # Agregar probabilidades al partido
                    match['player1_implied_prob'] = round(prob1_adjusted, 4)
                    match['player2_implied_prob'] = round(prob2_adjusted, 4)
                    match['total_prob'] = round(total_prob, 4)
                    match['margin'] = round(margin, 4)
                    
                    # Validar probabilidades
                    if (prob1_adjusted < self.min_probability_threshold or 
                        prob1_adjusted > self.max_probability_threshold or
                        prob2_adjusted < self.min_probability_threshold or 
                        prob2_adjusted > self.max_probability_threshold):
                        self.logger.warning(f"Probabilidades fuera de rango válido: {prob1_adjusted}, {prob2_adjusted}")
                        match['valid_probabilities'] = False
                    else:
                        match['valid_probabilities'] = True
                        
            except Exception as e:
                self.logger.warning(f"Error calculando probabilidades para partido: {e}")
                match['valid_probabilities'] = False
        
        self.logger.info("Probabilidades implícitas calculadas")
        return matches
    
    def add_statistical_features(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Agregar características estadísticas a los partidos.
        
        Args:
            matches: Lista de partidos con probabilidades
            
        Returns:
            Lista de partidos con características agregadas
        """
        self.logger.info("Agregando características estadísticas")
        
        for match in matches:
            try:
                # Calcular valor esperado (EV)
                if 'player1_implied_prob' in match and 'player1_odds' in match:
                    ev1 = (match['player1_implied_prob'] * (match['player1_odds'] - 1)) - (1 - match['player1_implied_prob'])
                    match['player1_ev'] = round(ev1, 4)
                
                if 'player2_implied_prob' in match and 'player2_odds' in match:
                    ev2 = (match['player2_implied_prob'] * (match['player2_odds'] - 1)) - (1 - match['player2_implied_prob'])
                    match['player2_ev'] = round(ev2, 4)
                
                # Calcular Kelly Criterion
                if 'player1_ev' in match and match['player1_ev'] > 0:
                    kelly1 = match['player1_ev'] / (match['player1_odds'] - 1)
                    match['player1_kelly'] = round(kelly1, 4)
                else:
                    match['player1_kelly'] = 0.0
                
                if 'player2_ev' in match and match['player2_ev'] > 0:
                    kelly2 = match['player2_ev'] / (match['player2_odds'] - 1)
                    match['player2_kelly'] = round(kelly2, 4)
                else:
                    match['player2_kelly'] = 0.0
                
                # Agregar características de torneo
                match['tournament_level'] = self._classify_tournament_level(match.get('tournament', ''))
                match['surface_type'] = match.get('surface', 'hard')
                
                # Agregar timestamp de procesamiento
                match['processed_at'] = datetime.utcnow()
                
            except Exception as e:
                self.logger.warning(f"Error agregando características para partido: {e}")
                continue
        
        self.logger.info("Características estadísticas agregadas")
        return matches
    
    def _classify_tournament_level(self, tournament_name: str) -> str:
        """Clasificar nivel del torneo basado en el nombre."""
        tournament_name = tournament_name.lower()
        
        if any(grand_slam in tournament_name for grand_slam in ['australian open', 'wimbledon', 'roland garros', 'us open']):
            return 'grand_slam'
        elif any(atp_1000 in tournament_name for atp_1000 in ['indian wells', 'miami', 'monte carlo', 'madrid', 'rome', 'canada', 'cincinnati', 'shanghai', 'paris']):
            return 'atp_1000'
        elif any(atp_500 in tournament_name for atp_500 in ['rotterdam', 'dubai', 'acapulco', 'barcelona', 'hamburg', 'washington', 'tokyo', 'basel', 'vienna']):
            return 'atp_500'
        elif any(atp_250 in tournament_name for atp_250 in ['doha', 'adelaide', 'auckland', 'sydney', 'marseille', 'rotterdam']):
            return 'atp_250'
        elif 'challenger' in tournament_name:
            return 'challenger'
        else:
            return 'other'
    
    def filter_valid_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtrar partidos válidos para análisis.
        
        Args:
            matches: Lista de partidos procesados
            
        Returns:
            Lista de partidos válidos
        """
        self.logger.info("Filtrando partidos válidos")
        
        valid_matches = []
        
        for match in matches:
            try:
                # Verificar que tenga todos los campos necesarios
                required_fields = [
                    'tournament', 'player1', 'player2', 'odds', 
                    'player1_implied_prob', 'player2_implied_prob'
                ]
                
                if not all(field in match for field in required_fields):
                    continue
                
                # Verificar que las probabilidades sean válidas
                if not match.get('valid_probabilities', False):
                    continue
                
                # Verificar que las cuotas estén en rango válido
                odds1, odds2 = match['odds'][0], match['odds'][1]
                if odds1 < self.min_odds_threshold or odds1 > self.max_odds_threshold or \
                   odds2 < self.min_odds_threshold or odds2 > self.max_odds_threshold:
                    continue
                
                # Verificar que el margen no sea excesivo
                margin = match.get('margin', 0)
                if margin > 0.15:  # Margen máximo del 15%
                    continue
                
                valid_matches.append(match)
                
            except Exception as e:
                self.logger.warning(f"Error validando partido: {e}")
                continue
        
        self.logger.info(f"Partidos válidos filtrados: {len(valid_matches)}")
        return valid_matches
    
    def run_cleaning_pipeline(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ejecutar pipeline completo de limpieza.
        
        Args:
            matches: Lista de partidos crudos
            
        Returns:
            Lista de partidos limpios y procesados
        """
        self.logger.info("Iniciando pipeline de limpieza de datos")
        
        try:
            # Paso 1: Limpiar datos básicos
            cleaned_matches = self.clean_matches_data(matches)
            self.logger.info(f"Datos limpios: {len(cleaned_matches)} partidos procesados")
            
            # Paso 2: Calcular probabilidades implícitas
            matches_with_probs = self.calculate_implied_probabilities(cleaned_matches)
            self.logger.info("Probabilidades implícitas calculadas")
            
            # Paso 3: Agregar características estadísticas
            matches_with_features = self.add_statistical_features(matches_with_probs)
            self.logger.info("Características estadísticas agregadas")
            
            # Paso 4: Filtrar partidos válidos
            valid_matches = self.filter_valid_matches(matches_with_features)
            self.logger.info(f"Partidos válidos filtrados: {len(valid_matches)}")
            
            self.logger.info(f"Pipeline de limpieza completado: {len(valid_matches)} partidos válidos")
            return valid_matches
            
        except Exception as e:
            self.logger.error(f"Error en pipeline de limpieza: {e}")
            return []

# Función de conveniencia para uso directo
def clean_tennis_data(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Limpiar datos de tenis usando el pipeline completo.
    
    Args:
        matches: Lista de partidos crudos
        
    Returns:
        Lista de partidos limpios y procesados
    """
    cleaner = TennisDataCleaner()
    return cleaner.run_cleaning_pipeline(matches)

if __name__ == "__main__":
    # Ejecutar limpieza si se llama directamente
    from data_ingest import run_tennis_data_ingestion
    
    # Obtener datos de ejemplo
    matches = run_tennis_data_ingestion()
    
    # Limpiar datos
    cleaned_matches = clean_tennis_data(matches)
    
    print(f"✅ Limpieza completada: {len(cleaned_matches)} partidos válidos")

