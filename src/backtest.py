#!/usr/bin/env python3
"""
Sistema de backtesting para estrategias de apuestas de tenis.
Evalúa el rendimiento histórico de estrategias y calcula métricas de rentabilidad.
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from config import config
from database import db_manager

# Configurar logging
logger = logging.getLogger(__name__)

class TennisBacktester:
    """Sistema de backtesting para estrategias de apuestas de tenis."""
    
    def __init__(self, initial_bankroll: float = None):
        """
        Inicializar backtester.
        
        Args:
            initial_bankroll: Capital inicial para el backtest
        """
        self.logger = logging.getLogger(__name__)
        self.initial_bankroll = initial_bankroll or config.BANKROLL
        self.current_bankroll = self.initial_bankroll
        self.bets_placed = []
        self.results = []
        
        # Configuración de backtesting
        self.commission_rate = 0.05  # 5% de comisión
        self.min_bet_size = 10.0  # Apuesta mínima
        self.max_bet_size = 1000.0  # Apuesta máxima
        
        # Métricas de rendimiento
        self.total_bets = 0
        self.winning_bets = 0
        self.losing_bets = 0
        self.push_bets = 0
        
    def run_backtest(
        self, 
        signals: List[Dict[str, Any]], 
        match_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Ejecutar backtest completo con señales y resultados.
        
        Args:
            signals: Lista de señales de apuestas
            match_results: Lista de resultados de partidos
            
        Returns:
            Resultados del backtest
        """
        try:
            self.logger.info("Iniciando backtest del sistema de apuestas")
            
            # Resetear estado del backtester
            self._reset_backtester()
            
            # Crear diccionario de resultados por partido
            results_dict = self._create_results_lookup(match_results)
            
            # Procesar cada señal
            for signal in signals:
                try:
                    self._process_signal(signal, results_dict)
                except Exception as e:
                    self.logger.warning(f"Error procesando señal: {e}")
                    continue
            
            # Calcular métricas finales
            final_metrics = self._calculate_final_metrics()
            
            # Generar reporte completo
            report = self._generate_backtest_report(final_metrics)
            
            self.logger.info(f"Backtest completado: {self.total_bets} apuestas procesadas")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error en backtest: {e}")
            return {}
    
    def _reset_backtester(self):
        """Resetear estado del backtester."""
        self.current_bankroll = self.initial_bankroll
        self.bets_placed = []
        self.results = []
        self.total_bets = 0
        self.winning_bets = 0
        self.losing_bets = 0
        self.push_bets = 0
    
    def _create_results_lookup(self, match_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Crear diccionario de búsqueda de resultados por partido.
        
        Args:
            match_results: Lista de resultados de partidos
            
        Returns:
            Diccionario de resultados indexado por ID de partido
        """
        results_dict = {}
        
        for result in match_results:
            try:
                match_id = result.get('match_id')
                if match_id:
                    results_dict[match_id] = result
            except Exception as e:
                self.logger.warning(f"Error procesando resultado: {e}")
                continue
        
        return results_dict
    
    def _process_signal(self, signal: Dict[str, Any], results_dict: Dict[str, Dict[str, Any]]):
        """
        Procesar una señal individual de apuesta.
        
        Args:
            signal: Señal de apuesta
            results_dict: Diccionario de resultados
        """
        try:
            match_id = signal.get('match_id')
            
            # Verificar si tenemos resultado para este partido
            if match_id not in results_dict:
                self.logger.debug(f"No hay resultado para partido: {match_id}")
                return
            
            result = results_dict[match_id]
            
            # Verificar que el partido haya terminado
            if result.get('status') != 'finished':
                return
            
            # Calcular stake de la apuesta
            stake = self._calculate_bet_stake(signal)
            
            # Verificar si la apuesta es válida
            if stake < self.min_bet_size:
                return
            
            # Determinar resultado de la apuesta
            bet_result = self._determine_bet_result(signal, result)
            
            # Calcular ganancia/pérdida
            if bet_result == 'win':
                payout = stake * signal['odds'] - stake
                net_payout = payout * (1 - self.commission_rate)
                self.current_bankroll += net_payout
                self.winning_bets += 1
                result_type = 'win'
            elif bet_result == 'loss':
                net_loss = stake
                self.current_bankroll -= net_loss
                self.losing_bets += 1
                result_type = 'loss'
            else:  # push
                self.push_bets += 1
                result_type = 'push'
                net_payout = 0
            
            # Registrar la apuesta
            bet_record = {
                'match_id': match_id,
                'signal_id': signal.get('id', 'unknown'),
                'tournament': signal.get('tournament'),
                'player1': signal.get('player1'),
                'player2': signal.get('player2'),
                'recommended_bet': signal.get('recommended_bet'),
                'player_name': signal.get('player_name'),
                'odds': signal.get('odds'),
                'stake': stake,
                'result': result_type,
                'payout': net_payout if result_type == 'win' else -stake if result_type == 'loss' else 0,
                'bankroll_after': self.current_bankroll,
                'confidence_level': signal.get('confidence_level'),
                'expected_value': signal.get('expected_value'),
                'placed_at': signal.get('generated_at'),
                'settled_at': datetime.utcnow()
            }
            
            self.bets_placed.append(bet_record)
            self.total_bets += 1
            
            # Registrar resultado
            self.results.append({
                'match_id': match_id,
                'bet_result': result_type,
                'stake': stake,
                'payout': bet_record['payout'],
                'odds': signal.get('odds'),
                'confidence': signal.get('confidence_level'),
                'ev': signal.get('expected_value')
            })
            
        except Exception as e:
            self.logger.warning(f"Error procesando señal: {e}")
    
    def _calculate_bet_stake(self, signal: Dict[str, Any]) -> float:
        """
        Calcular stake de la apuesta basado en la señal.
        
        Args:
            signal: Señal de apuesta
            
        Returns:
            Stake calculado
        """
        try:
            # Obtener stake recomendado
            recommended_stake = signal.get('recommended_stake', 0.02)  # 2% por defecto
            
            # Convertir a cantidad monetaria
            if isinstance(recommended_stake, (int, float)):
                stake_amount = self.current_bankroll * recommended_stake
            else:
                # Si es una lista (arbitraje), usar el promedio
                stake_amount = self.current_bankroll * (sum(recommended_stake) / len(recommended_stake))
            
            # Aplicar límites
            stake_amount = max(self.min_bet_size, min(stake_amount, self.max_bet_size))
            
            # Verificar que no exceda el bankroll disponible
            stake_amount = min(stake_amount, self.current_bankroll * 0.95)
            
            return round(stake_amount, 2)
            
        except Exception as e:
            self.logger.warning(f"Error calculando stake: {e}")
            return self.min_bet_size
    
    def _determine_bet_result(self, signal: Dict[str, Any], result: Dict[str, Any]) -> str:
        """
        Determinar el resultado de una apuesta.
        
        Args:
            signal: Señal de apuesta
            result: Resultado del partido
            
        Returns:
            Resultado de la apuesta ('win', 'loss', 'push')
        """
        try:
            recommended_bet = signal.get('recommended_bet')
            player_name = signal.get('player_name')
            
            # Si es arbitraje, siempre es push (no hay ganancia/pérdida neta)
            if recommended_bet == 'arbitrage':
                return 'push'
            
            # Obtener ganador del partido
            winner = result.get('winner')
            if not winner:
                return 'push'
            
            # Verificar si ganó el jugador apostado
            if player_name == winner:
                return 'win'
            else:
                return 'loss'
                
        except Exception as e:
            self.logger.warning(f"Error determinando resultado: {e}")
            return 'push'
    
    def _calculate_final_metrics(self) -> Dict[str, Any]:
        """
        Calcular métricas finales del backtest.
        
        Returns:
            Diccionario con métricas calculadas
        """
        try:
            if self.total_bets == 0:
                return {
                    'total_bets': 0,
                    'win_rate': 0.0,
                    'total_return': 0.0,
                    'roi': 0.0,
                    'final_bankroll': self.initial_bankroll,
                    'profit_loss': 0.0
                }
            
            # Métricas básicas
            win_rate = self.winning_bets / self.total_bets
            total_return = self.current_bankroll - self.initial_bankroll
            roi = (total_return / self.initial_bankroll) * 100
            
            # Calcular métricas de apuestas
            total_stake = sum(bet['stake'] for bet in self.bets_placed)
            total_payout = sum(bet['payout'] for bet in self.bets_placed)
            
            # Calcular métricas de Kelly
            avg_odds = np.mean([bet['odds'] for bet in self.bets_placed if isinstance(bet['odds'], (int, float))])
            avg_ev = np.mean([bet['ev'] for bet in self.bets_placed if bet['ev'] is not None])
            
            # Calcular drawdown máximo
            bankroll_history = [bet['bankroll_after'] for bet in self.bets_placed]
            if bankroll_history:
                peak = max(bankroll_history)
                drawdown = min((peak - bankroll) / peak for bankroll in bankroll_history)
            else:
                drawdown = 0.0
            
            metrics = {
                'total_bets': self.total_bets,
                'winning_bets': self.winning_bets,
                'losing_bets': self.losing_bets,
                'push_bets': self.push_bets,
                'win_rate': round(win_rate, 4),
                'total_stake': round(total_stake, 2),
                'total_payout': round(total_payout, 2),
                'total_return': round(total_return, 2),
                'roi': round(roi, 2),
                'initial_bankroll': self.initial_bankroll,
                'final_bankroll': round(self.current_bankroll, 2),
                'profit_loss': round(total_return, 2),
                'avg_odds': round(avg_odds, 2) if not np.isnan(avg_odds) else 0.0,
                'avg_ev': round(avg_ev, 4) if not np.isnan(avg_ev) else 0.0,
                'max_drawdown': round(drawdown, 4),
                'commission_paid': round(total_stake * self.commission_rate, 2)
            }
            
            return metrics
            
        except Exception as e:
            self.logger.warning(f"Error calculando métricas finales: {e}")
            return {}
    
    def _generate_backtest_report(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generar reporte completo del backtest.
        
        Args:
            metrics: Métricas calculadas
            
        Returns:
            Reporte completo del backtest
        """
        try:
            # Agrupar apuestas por nivel de confianza
            confidence_groups = {}
            for bet in self.bets_placed:
                confidence = bet.get('confidence_level', 'unknown')
                if confidence not in confidence_groups:
                    confidence_groups[confidence] = []
                confidence_groups[confidence].append(bet)
            
            # Calcular métricas por nivel de confianza
            confidence_metrics = {}
            for confidence, bets in confidence_groups.items():
                if bets:
                    wins = len([b for b in bets if b['result'] == 'win'])
                    total = len(bets)
                    win_rate = wins / total if total > 0 else 0.0
                    total_payout = sum(b['payout'] for b in bets)
                    
                    confidence_metrics[confidence] = {
                        'total_bets': total,
                        'win_rate': round(win_rate, 4),
                        'total_payout': round(total_payout, 2),
                        'avg_payout': round(total_payout / total, 2) if total > 0 else 0.0
                    }
            
            # Generar reporte
            report = {
                'summary': metrics,
                'confidence_metrics': confidence_metrics,
                'bet_history': self.bets_placed,
                'results_summary': self.results,
                'backtest_config': {
                    'initial_bankroll': self.initial_bankroll,
                    'commission_rate': self.commission_rate,
                    'min_bet_size': self.min_bet_size,
                    'max_bet_size': self.max_bet_size
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.warning(f"Error generando reporte: {e}")
            return {'summary': metrics}
    
    def run_monte_carlo_simulation(
        self, 
        signals: List[Dict[str, Any]], 
        match_results: List[Dict[str, Any]],
        num_simulations: int = 1000
    ) -> Dict[str, Any]:
        """
        Ejecutar simulación Monte Carlo para evaluar variabilidad de resultados.
        
        Args:
            signals: Lista de señales de apuestas
            match_results: Lista de resultados de partidos
            num_simulations: Número de simulaciones a ejecutar
            
        Returns:
            Resultados de la simulación Monte Carlo
        """
        try:
            self.logger.info(f"Ejecutando simulación Monte Carlo con {num_simulations} iteraciones")
            
            simulation_results = []
            
            for i in range(num_simulations):
                # Resetear backtester
                self._reset_backtester()
                
                # Mezclar señales aleatoriamente para simular diferentes órdenes
                shuffled_signals = signals.copy()
                np.random.shuffle(shuffled_signals)
                
                # Ejecutar backtest
                results_dict = self._create_results_lookup(match_results)
                
                for signal in shuffled_signals:
                    try:
                        self._process_signal(signal, results_dict)
                    except Exception as e:
                        continue
                
                # Calcular métricas de esta simulación
                metrics = self._calculate_final_metrics()
                simulation_results.append(metrics)
                
                if (i + 1) % 100 == 0:
                    self.logger.info(f"Simulación {i + 1}/{num_simulations} completada")
            
            # Calcular estadísticas de la simulación
            final_bankrolls = [r['final_bankroll'] for r in simulation_results]
            rois = [r['roi'] for r in simulation_results]
            
            simulation_stats = {
                'num_simulations': num_simulations,
                'mean_final_bankroll': round(np.mean(final_bankrolls), 2),
                'std_final_bankroll': round(np.std(final_bankrolls), 2),
                'min_final_bankroll': round(np.min(final_bankrolls), 2),
                'max_final_bankroll': round(np.max(final_bankrolls), 2),
                'mean_roi': round(np.mean(rois), 2),
                'std_roi': round(np.std(rois), 2),
                'min_roi': round(np.min(rois), 2),
                'max_roi': round(np.max(rois), 2),
                'probability_profit': round(len([r for r in rois if r > 0]) / num_simulations, 4),
                'probability_breakeven': round(len([r for r in rois if r >= 0]) / num_simulations, 4)
            }
            
            self.logger.info("Simulación Monte Carlo completada")
            return {
                'simulation_stats': simulation_stats,
                'individual_results': simulation_results
            }
            
        except Exception as e:
            self.logger.error(f"Error en simulación Monte Carlo: {e}")
            return {}

# Función de conveniencia para uso directo
def run_tennis_backtest(
    signals: List[Dict[str, Any]], 
    match_results: List[Dict[str, Any]],
    initial_bankroll: float = None
) -> Dict[str, Any]:
    """
    Ejecutar backtest completo para tenis.
    
    Args:
        signals: Lista de señales de apuestas
        match_results: Lista de resultados de partidos
        initial_bankroll: Capital inicial
        
    Returns:
        Reporte completo del backtest
    """
    backtester = TennisBacktester(initial_bankroll=initial_bankroll)
    return backtester.run_backtest(signals, match_results)

def run_monte_carlo_backtest(
    signals: List[Dict[str, Any]], 
    match_results: List[Dict[str, Any]],
    initial_bankroll: float = None,
    num_simulations: int = 1000
) -> Dict[str, Any]:
    """
    Ejecutar simulación Monte Carlo para tenis.
    
    Args:
        signals: Lista de señales de apuestas
        match_results: Lista de resultados de partidos
        initial_bankroll: Capital inicial
        num_simulations: Número de simulaciones
        
    Returns:
        Resultados de la simulación Monte Carlo
    """
    backtester = TennisBacktester(initial_bankroll=initial_bankroll)
    return backtester.run_monte_carlo_simulation(signals, match_results, num_simulations)

if __name__ == "__main__":
    # Ejecutar backtest si se llama directamente
    from data_ingest import run_tennis_data_ingestion
    from data_clean import clean_tennis_data
    from betting_signals import generate_tennis_betting_signals
    
    # Obtener y procesar datos
    matches = run_tennis_data_ingestion()
    cleaned_matches = clean_tennis_data(matches)
    signals, summary = generate_tennis_betting_signals(cleaned_matches)
    
    # Simular resultados (en un caso real, estos vendrían de la base de datos)
    match_results = []
    for match in cleaned_matches[:10]:  # Solo primeros 10 para ejemplo
        match_results.append({
            'match_id': match.get('match_id', f"{match['player1']}_{match['player2']}"),
            'winner': match['player1'] if np.random.random() > 0.5 else match['player2'],
            'status': 'finished',
            'score': '6-4, 6-3'
        })
    
    # Ejecutar backtest
    backtest_results = run_tennis_backtest(signals, match_results)
    
    print(f"✅ Backtest completado: {backtest_results.get('summary', {}).get('total_bets', 0)} apuestas procesadas")
    print(f"📊 ROI: {backtest_results.get('summary', {}).get('roi', 0)}%")

