"""
Módulo de backtesting para el sistema de apuestas de tenis.
Incluye simulación de estrategias en datos históricos y cálculo de métricas de rendimiento.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import logging
from datetime import datetime, timedelta
from src.config import config
from src.betting_signals import BettingSignalDetector

logger = logging.getLogger(__name__)

class BacktestEngine:
    """Motor de backtesting para estrategias de apuestas de tenis."""
    
    def __init__(self, initial_bankroll: float = None):
        """
        Inicializar el motor de backtesting.
        
        Args:
            initial_bankroll: Capital inicial para la simulación
        """
        self.initial_bankroll = initial_bankroll or config.BANKROLL
        self.logger = logging.getLogger(__name__)
        
    def simulate_bet(self, stake: float, odds: float, result: str) -> Dict[str, float]:
        """
        Simular el resultado de una apuesta individual.
        
        Args:
            stake: Cantidad apostada
            odds: Cuota de la apuesta
            result: Resultado ('win', 'loss', 'void')
            
        Returns:
            Diccionario con resultado de la apuesta
        """
        try:
            if result == 'win':
                profit = (stake * odds) - stake
                return {
                    'stake': stake,
                    'profit': profit,
                    'return': stake * odds,
                    'result': 'win'
                }
            elif result == 'loss':
                return {
                    'stake': stake,
                    'profit': -stake,
                    'return': 0,
                    'result': 'loss'
                }
            else:  # void
                return {
                    'stake': stake,
                    'profit': 0,
                    'return': stake,
                    'result': 'void'
                }
                
        except Exception as e:
            self.logger.error(f"Error simulando apuesta: {e}")
            return {
                'stake': stake,
                'profit': 0,
                'return': stake,
                'result': 'error'
            }
    
    def calculate_bet_result(self, selection: str, winner: str, 
                           selection_type: str, player1: str, player2: str) -> str:
        """
        Determinar el resultado de una apuesta basado en el ganador del partido.
        
        Args:
            selection: Jugador seleccionado en la apuesta
            winner: Ganador del partido
            selection_type: Tipo de selección ('player1' o 'player2')
            player1: Nombre del jugador 1
            player2: Nombre del jugador 2
            
        Returns:
            Resultado de la apuesta ('win', 'loss', 'void')
        """
        try:
            if pd.isna(winner) or winner == '':
                return 'void'
            
            if selection == winner:
                return 'win'
            else:
                return 'loss'
                
        except Exception as e:
            self.logger.error(f"Error calculando resultado: {e}")
            return 'void'
    
    def run_backtest(self, historical_data: pd.DataFrame, 
                    signals_data: pd.DataFrame,
                    strategy: str = 'kelly_fractional') -> Dict:
        """
        Ejecutar backtesting completo de una estrategia.
        
        Args:
            historical_data: DataFrame con resultados históricos
            signals_data: DataFrame con señales de apuesta
            strategy: Estrategia a probar
            
        Returns:
            Diccionario con resultados del backtesting
        """
        try:
            self.logger.info(f"Iniciando backtesting con estrategia: {strategy}")
            
            # Inicializar variables de seguimiento
            current_bankroll = self.initial_bankroll
            bets_placed = []
            bankroll_history = [current_bankroll]
            dates = []
            
            # Combinar datos históricos con señales
            merged_data = pd.merge(
                signals_data, 
                historical_data[['match_id', 'winner']], 
                on='match_id', 
                how='left'
            )
            
            # Ordenar por fecha del partido
            if 'match_time' in merged_data.columns:
                merged_data = merged_data.sort_values('match_time')
            
            # Simular cada apuesta
            for idx, bet in merged_data.iterrows():
                try:
                    # Determinar resultado de la apuesta
                    result = self.calculate_bet_result(
                        bet['selection'],
                        bet.get('winner', ''),
                        bet.get('selection_type', 'player1'),
                        bet.get('player1', ''),
                        bet.get('player2', '')
                    )
                    
                    # Simular apuesta
                    bet_result = self.simulate_bet(
                        bet['recommended_stake'],
                        bet['odds'],
                        result
                    )
                    
                    # Actualizar bankroll
                    current_bankroll += bet_result['profit']
                    
                    # Registrar apuesta
                    bet_record = {
                        'match_id': bet['match_id'],
                        'date': bet.get('match_time', datetime.now()),
                        'selection': bet['selection'],
                        'opponent': bet['opponent'],
                        'odds': bet['odds'],
                        'stake': bet_result['stake'],
                        'result': bet_result['result'],
                        'profit': bet_result['profit'],
                        'bankroll': current_bankroll,
                        'ev': bet.get('ev', 0),
                        'model_prob': bet.get('model_prob', 0)
                    }
                    bets_placed.append(bet_record)
                    
                    # Registrar historial de bankroll
                    bankroll_history.append(current_bankroll)
                    dates.append(bet.get('match_time', datetime.now()))
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando apuesta {bet.get('match_id', idx)}: {e}")
                    continue
            
            # Calcular métricas de rendimiento
            performance_metrics = self.calculate_performance_metrics(
                bets_placed, bankroll_history, dates
            )
            
            # Crear DataFrame de resultados
            bets_df = pd.DataFrame(bets_placed)
            
            result = {
                'bets': bets_df,
                'performance_metrics': performance_metrics,
                'bankroll_history': bankroll_history,
                'dates': dates,
                'strategy': strategy,
                'initial_bankroll': self.initial_bankroll,
                'final_bankroll': current_bankroll
            }
            
            self.logger.info(f"Backtesting completado: {len(bets_placed)} apuestas simuladas")
            return result
            
        except Exception as e:
            self.logger.error(f"Error en backtesting: {e}")
            raise
    
    def calculate_performance_metrics(self, bets: List[Dict], 
                                    bankroll_history: List[float],
                                    dates: List[datetime]) -> Dict[str, float]:
        """
        Calcular métricas de rendimiento del backtesting.
        
        Args:
            bets: Lista de apuestas simuladas
            bankroll_history: Historial del bankroll
            dates: Fechas de las apuestas
            
        Returns:
            Diccionario con métricas de rendimiento
        """
        try:
            if not bets:
                return {
                    'total_bets': 0,
                    'win_rate': 0.0,
                    'roi': 0.0,
                    'total_profit': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0,
                    'profit_factor': 0.0
                }
            
            # Métricas básicas
            total_bets = len(bets)
            winning_bets = len([b for b in bets if b['result'] == 'win'])
            losing_bets = len([b for b in bets if b['result'] == 'loss'])
            void_bets = len([b for b in bets if b['result'] == 'void'])
            
            win_rate = winning_bets / total_bets if total_bets > 0 else 0
            
            # Cálculo de ROI y profit
            total_stake = sum(b['stake'] for b in bets)
            total_profit = sum(b['profit'] for b in bets)
            roi = (total_profit / total_stake) if total_stake > 0 else 0
            
            # Cálculo de drawdown
            max_drawdown = self.calculate_max_drawdown(bankroll_history)
            
            # Cálculo de Sharpe ratio (simplificado)
            returns = np.diff(bankroll_history)
            sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
            
            # Profit factor
            gross_profit = sum(b['profit'] for b in bets if b['profit'] > 0)
            gross_loss = abs(sum(b['profit'] for b in bets if b['profit'] < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Métricas adicionales
            avg_odds = np.mean([b['odds'] for b in bets])
            avg_ev = np.mean([b['ev'] for b in bets if pd.notna(b['ev'])])
            
            metrics = {
                'total_bets': total_bets,
                'winning_bets': winning_bets,
                'losing_bets': losing_bets,
                'void_bets': void_bets,
                'win_rate': win_rate,
                'roi': roi,
                'total_profit': total_profit,
                'total_stake': total_stake,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'profit_factor': profit_factor,
                'avg_odds': avg_odds,
                'avg_ev': avg_ev
            }
            
            self.logger.info(f"Métricas calculadas: ROI {roi:.2%}, Win Rate {win_rate:.2%}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculando métricas: {e}")
            raise
    
    def calculate_max_drawdown(self, bankroll_history: List[float]) -> float:
        """
        Calcular el drawdown máximo del bankroll.
        
        Args:
            bankroll_history: Lista con el historial del bankroll
            
        Returns:
            Drawdown máximo como porcentaje
        """
        try:
            if len(bankroll_history) < 2:
                return 0.0
            
            peak = bankroll_history[0]
            max_dd = 0.0
            
            for value in bankroll_history:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak
                if dd > max_dd:
                    max_dd = dd
            
            return max_dd
            
        except Exception as e:
            self.logger.error(f"Error calculando drawdown: {e}")
            return 0.0
    
    def generate_backtest_report(self, backtest_results: Dict) -> str:
        """
        Generar reporte de texto del backtesting.
        
        Args:
            backtest_results: Resultados del backtesting
            
        Returns:
            Reporte formateado como string
        """
        try:
            metrics = backtest_results['performance_metrics']
            
            report = f"""
=== REPORTE DE BACKTESTING ===
Estrategia: {backtest_results['strategy']}
Período: {backtest_results['dates'][0] if backtest_results['dates'] else 'N/A'} - {backtest_results['dates'][-1] if backtest_results['dates'] else 'N/A'}

RESULTADOS GENERALES:
- Apuestas totales: {metrics['total_bets']}
- Apuestas ganadoras: {metrics['winning_bets']}
- Apuestas perdedoras: {metrics['losing_bets']}
- Apuestas nulas: {metrics['void_bets']}

MÉTRICAS DE RENDIMIENTO:
- Win Rate: {metrics['win_rate']:.2%}
- ROI: {metrics['roi']:.2%}
- Profit Total: ${metrics['total_profit']:.2f}
- Drawdown Máximo: {metrics['max_drawdown']:.2%}
- Sharpe Ratio: {metrics['sharpe_ratio']:.3f}
- Profit Factor: {metrics['profit_factor']:.2f}

BANKROLL:
- Inicial: ${backtest_results['initial_bankroll']:.2f}
- Final: ${backtest_results['final_bankroll']:.2f}
- Cambio: ${metrics['total_profit']:.2f} ({((backtest_results['final_bankroll'] / backtest_results['initial_bankroll']) - 1):.2%})
"""
            return report
            
        except Exception as e:
            self.logger.error(f"Error generando reporte: {e}")
            return f"Error generando reporte: {e}"
    
    def save_backtest_results(self, backtest_results: Dict, filepath: str) -> None:
        """
        Guardar resultados del backtesting en archivo.
        
        Args:
            backtest_results: Resultados del backtesting
            filepath: Ruta del archivo donde guardar
        """
        try:
            # Guardar apuestas
            bets_file = filepath.replace('.csv', '_bets.csv')
            if not backtest_results['bets'].empty:
                backtest_results['bets'].to_csv(bets_file, index=False)
            
            # Guardar métricas
            metrics_file = filepath.replace('.csv', '_metrics.csv')
            pd.DataFrame([backtest_results['performance_metrics']]).to_csv(metrics_file, index=False)
            
            # Guardar historial de bankroll
            history_file = filepath.replace('.csv', '_history.csv')
            history_df = pd.DataFrame({
                'date': backtest_results['dates'],
                'bankroll': backtest_results['bankroll_history']
            })
            history_df.to_csv(history_file, index=False)
            
            self.logger.info(f"Resultados guardados en: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error guardando resultados: {e}")
            raise

# Función de conveniencia para uso directo
def run_tennis_backtest(historical_data: pd.DataFrame,
                        signals_data: pd.DataFrame,
                        initial_bankroll: float = None,
                        strategy: str = 'kelly_fractional') -> Dict:
    """
    Función de conveniencia para ejecutar backtesting de tenis.
    
    Args:
        historical_data: Datos históricos con resultados
        signals_data: Señales de apuesta
        initial_bankroll: Capital inicial
        strategy: Estrategia a probar
        
    Returns:
        Resultados del backtesting
    """
    engine = BacktestEngine(initial_bankroll=initial_bankroll)
    return engine.run_backtest(historical_data, signals_data, strategy)

