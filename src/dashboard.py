#!/usr/bin/env python3
"""
Dashboard web para el sistema de apuestas de tenis.
Proporciona interfaz web para visualizar señales, resultados y métricas del sistema.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO, emit
import pandas as pd

from config import config
from database import db_manager
from betting_signals import generate_tennis_betting_signals
from backtest import run_tennis_backtest

# Configurar logging
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'tennis_betting_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

class TennisDashboard:
    """Clase principal del dashboard de tenis."""
    
    def __init__(self):
        """Inicializar dashboard."""
        self.logger = logging.getLogger(__name__)
        self.last_update = datetime.utcnow()
        self.cache_duration = timedelta(minutes=5)
        
        # Datos en caché
        self.cached_signals = []
        self.cached_matches = []
        self.cached_metrics = {}
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Obtener datos principales del dashboard.
        
        Returns:
            Diccionario con datos del dashboard
        """
        try:
            # Verificar si necesitamos actualizar caché
            if datetime.utcnow() - self.last_update > self.cache_duration:
                self._update_cache()
            
            return {
                'signals': self.cached_signals,
                'matches': self.cached_matches,
                'metrics': self.cached_metrics,
                'last_update': self.last_update.isoformat(),
                'system_status': 'active'
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos del dashboard: {e}")
            return {
                'signals': [],
                'matches': [],
                'metrics': {},
                'last_update': datetime.utcnow().isoformat(),
                'system_status': 'error',
                'error': str(e)
            }
    
    def _update_cache(self):
        """Actualizar datos en caché."""
        try:
            self.logger.info("Actualizando caché del dashboard")
            
            # Obtener partidos recientes
            self.cached_matches = self._get_recent_matches()
            
            # Generar señales
            if self.cached_matches:
                signals, summary = generate_tennis_betting_signals(self.cached_matches)
                self.cached_signals = signals
            else:
                self.cached_signals = []
                summary = {}
            
            # Calcular métricas
            self.cached_metrics = self._calculate_dashboard_metrics()
            
            # Actualizar timestamp
            self.last_update = datetime.utcnow()
            
            self.logger.info("Caché del dashboard actualizado")
            
        except Exception as e:
            self.logger.error(f"Error actualizando caché: {e}")
    
    def _get_recent_matches(self) -> List[Dict[str, Any]]:
        """
        Obtener partidos recientes.
        
        Returns:
            Lista de partidos recientes
        """
        try:
            # En un caso real, esto vendría de la base de datos
            # Por ahora, simulamos algunos datos
            matches = [
                {
                    'match_id': 'match_001',
                    'player1': 'Novak Djokovic',
                    'player2': 'Rafael Nadal',
                    'tournament': 'Australian Open',
                    'match_time': datetime.utcnow() + timedelta(hours=2),
                    'surface': 'hard',
                    'round': 'Final',
                    'player1_odds': 1.85,
                    'player2_odds': 2.15,
                    'player1_implied_prob': 0.54,
                    'player2_implied_prob': 0.46,
                    'player1_ev': 0.08,
                    'player2_ev': 0.06
                },
                {
                    'match_id': 'match_002',
                    'player1': 'Daniil Medvedev',
                    'player2': 'Stefanos Tsitsipas',
                    'tournament': 'Miami Open',
                    'match_time': datetime.utcnow() + timedelta(hours=4),
                    'surface': 'hard',
                    'round': 'Semifinal',
                    'player1_odds': 1.65,
                    'player2_odds': 2.45,
                    'player1_implied_prob': 0.61,
                    'player2_implied_prob': 0.39,
                    'player1_ev': 0.12,
                    'player2_ev': 0.04
                }
            ]
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Error obteniendo partidos recientes: {e}")
            return []
    
    def _calculate_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Calcular métricas del dashboard.
        
        Returns:
            Diccionario con métricas calculadas
        """
        try:
            if not self.cached_signals:
                return {
                    'total_signals': 0,
                    'high_confidence': 0,
                    'medium_confidence': 0,
                    'low_confidence': 0,
                    'total_ev': 0.0,
                    'average_ev': 0.0
                }
            
            # Contar por nivel de confianza
            confidence_counts = {
                'high': len([s for s in self.cached_signals if s['confidence_level'] == 'high']),
                'medium': len([s for s in self.cached_signals if s['confidence_level'] == 'medium']),
                'low': len([s for s in self.cached_signals if s['confidence_level'] == 'low'])
            }
            
            # Calcular estadísticas de valor esperado
            ev_values = [s['expected_value'] for s in self.cached_signals if s['signal_type'] == 'value_bet']
            total_ev = sum(ev_values) if ev_values else 0.0
            average_ev = total_ev / len(ev_values) if ev_values else 0.0
            
            metrics = {
                'total_signals': len(self.cached_signals),
                'high_confidence': confidence_counts['high'],
                'medium_confidence': confidence_counts['medium'],
                'low_confidence': confidence_counts['low'],
                'total_ev': round(total_ev, 4),
                'average_ev': round(average_ev, 4),
                'arbitrage_opportunities': len([s for s in self.cached_signals if s['signal_type'] == 'arbitrage']),
                'value_bets': len([s for s in self.cached_signals if s['signal_type'] == 'value_bet'])
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculando métricas: {e}")
            return {}

# Instancia global del dashboard
dashboard = TennisDashboard()

# Rutas del dashboard
@app.route('/')
def index():
    """Página principal del dashboard."""
    try:
        data = dashboard.get_dashboard_data()
        return render_template('index.html', data=data)
    except Exception as e:
        logger.error(f"Error en página principal: {e}")
        return render_template('error.html', error=str(e))

@app.route('/api/dashboard-data')
def api_dashboard_data():
    """API para obtener datos del dashboard."""
    try:
        data = dashboard.get_dashboard_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error en API dashboard: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals')
def api_signals():
    """API para obtener señales de apuestas."""
    try:
        data = dashboard.get_dashboard_data()
        signals = data.get('signals', [])
        
        # Filtrar por parámetros de consulta
        confidence = request.args.get('confidence', 'all')
        min_ev = float(request.args.get('min_ev', 0))
        
        if confidence != 'all':
            signals = [s for s in signals if s['confidence_level'] == confidence]
        
        if min_ev > 0:
            signals = [s for s in signals if s['expected_value'] >= min_ev]
        
        return jsonify({
            'signals': signals,
            'count': len(signals),
            'filters': {
                'confidence': confidence,
                'min_ev': min_ev
            }
        })
    except Exception as e:
        logger.error(f"Error en API señales: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches')
def api_matches():
    """API para obtener partidos."""
    try:
        data = dashboard.get_dashboard_data()
        matches = data.get('matches', [])
        
        # Filtrar por parámetros de consulta
        tournament = request.args.get('tournament', 'all')
        surface = request.args.get('surface', 'all')
        
        if tournament != 'all':
            matches = [m for m in matches if m['tournament'] == tournament]
        
        if surface != 'all':
            matches = [m for m in matches if m['surface'] == surface]
        
        return jsonify({
            'matches': matches,
            'count': len(matches),
            'filters': {
                'tournament': tournament,
                'surface': surface
            }
        })
    except Exception as e:
        logger.error(f"Error en API partidos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    """API para ejecutar backtest."""
    try:
        data = request.get_json()
        
        if not data or 'signals' not in data:
            return jsonify({'error': 'Se requieren señales para el backtest'}), 400
        
        signals = data['signals']
        initial_bankroll = data.get('initial_bankroll', config.BANKROLL)
        
        # Simular resultados para el backtest
        match_results = []
        for signal in signals:
            match_results.append({
                'match_id': signal['match_id'],
                'winner': signal['player_name'] if signal['signal_type'] == 'value_bet' else 'unknown',
                'status': 'finished',
                'score': '6-4, 6-3'
            })
        
        # Ejecutar backtest
        backtest_results = run_tennis_backtest(signals, match_results, initial_bankroll)
        
        return jsonify({
            'success': True,
            'backtest_results': backtest_results
        })
        
    except Exception as e:
        logger.error(f"Error en API backtest: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh')
def api_refresh():
    """API para forzar actualización de datos."""
    try:
        dashboard._update_cache()
        return jsonify({
            'success': True,
            'message': 'Datos actualizados',
            'last_update': dashboard.last_update.isoformat()
        })
    except Exception as e:
        logger.error(f"Error en API refresh: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket para actualizaciones en tiempo real
@socketio.on('connect')
def handle_connect():
    """Manejar conexión de WebSocket."""
    logger.info("Cliente conectado al WebSocket")
    emit('status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Manejar desconexión de WebSocket."""
    logger.info("Cliente desconectado del WebSocket")

@socketio.on('request_update')
def handle_update_request():
    """Manejar solicitud de actualización."""
    try:
        data = dashboard.get_dashboard_data()
        emit('dashboard_update', data)
    except Exception as e:
        logger.error(f"Error enviando actualización: {e}")
        emit('error', {'error': str(e)})

# Crear directorio de templates si no existe
import os
templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(templates_dir, exist_ok=True)

# Crear template HTML básico
template_html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Apuestas de Tenis</title>
    <script src="https://cdn.socket.io/4.0.1/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .signals-section { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .signal-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .high-confidence { border-left: 5px solid #28a745; }
        .medium-confidence { border-left: 5px solid #ffc107; }
        .low-confidence { border-left: 5px solid #dc3545; }
        .refresh-btn { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .refresh-btn:hover { background: #5a6fd8; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎾 Sistema de Apuestas de Tenis</h1>
            <p>Dashboard en tiempo real para análisis de apuestas deportivas</p>
        </div>
        
        <button class="refresh-btn" onclick="refreshData()">🔄 Actualizar Datos</button>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total de Señales</h3>
                <div class="stat-value" id="total-signals">-</div>
            </div>
            <div class="stat-card">
                <h3>Alta Confianza</h3>
                <div class="stat-value" id="high-confidence">-</div>
            </div>
            <div class="stat-card">
                <h3>Valor Esperado Promedio</h3>
                <div class="stat-value" id="avg-ev">-</div>
            </div>
            <div class="stat-card">
                <h3>Última Actualización</h3>
                <div class="stat-value" id="last-update">-</div>
            </div>
        </div>
        
        <div class="signals-section">
            <h2>📊 Señales de Apuestas</h2>
            <div id="signals-container">
                <p>Cargando señales...</p>
            </div>
        </div>
        
        <div class="signals-section">
            <h2>🎯 Partidos Próximos</h2>
            <div id="matches-container">
                <p>Cargando partidos...</p>
            </div>
        </div>
    </div>

    <script>
        // Conectar WebSocket
        const socket = io();
        
        socket.on('connect', function() {
            console.log('Conectado al servidor');
        });
        
        socket.on('dashboard_update', function(data) {
            updateDashboard(data);
        });
        
        // Cargar datos iniciales
        loadDashboardData();
        
        function loadDashboardData() {
            fetch('/api/dashboard-data')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error:', error));
        }
        
        function updateDashboard(data) {
            // Actualizar estadísticas
            document.getElementById('total-signals').textContent = data.metrics.total_signals || 0;
            document.getElementById('high-confidence').textContent = data.metrics.high_confidence || 0;
            document.getElementById('avg-ev').textContent = (data.metrics.average_ev || 0).toFixed(3);
            document.getElementById('last-update').textContent = new Date(data.last_update).toLocaleTimeString();
            
            // Actualizar señales
            updateSignals(data.signals);
            
            // Actualizar partidos
            updateMatches(data.matches);
        }
        
        function updateSignals(signals) {
            const container = document.getElementById('signals-container');
            
            if (!signals || signals.length === 0) {
                container.innerHTML = '<p>No hay señales disponibles</p>';
                return;
            }
            
            let html = '';
            signals.forEach(signal => {
                const confidenceClass = signal.confidence_level + '-confidence';
                html += `
                    <div class="signal-item ${confidenceClass}">
                        <h4>${signal.player_name} vs ${signal.player2 || 'Oponente'}</h4>
                        <p><strong>Tournament:</strong> ${signal.tournament}</p>
                        <p><strong>Odds:</strong> ${signal.odds}</p>
                        <p><strong>Valor Esperado:</strong> ${(signal.expected_value * 100).toFixed(2)}%</p>
                        <p><strong>Confianza:</strong> ${signal.confidence_level}</p>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        function updateMatches(matches) {
            const container = document.getElementById('matches-container');
            
            if (!matches || matches.length === 0) {
                container.innerHTML = '<p>No hay partidos disponibles</p>';
                return;
            }
            
            let html = '';
            matches.forEach(match => {
                const matchTime = new Date(match.match_time).toLocaleString();
                html += `
                    <div class="signal-item">
                        <h4>${match.player1} vs ${match.player2}</h4>
                        <p><strong>Tournament:</strong> ${match.tournament}</p>
                        <p><strong>Surface:</strong> ${match.surface}</p>
                        <p><strong>Round:</strong> ${match.round}</p>
                        <p><strong>Match Time:</strong> ${matchTime}</p>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        function refreshData() {
            fetch('/api/refresh')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        loadDashboardData();
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        
        // Actualizar datos cada 30 segundos
        setInterval(loadDashboardData, 30000);
    </script>
</body>
</html>
"""

# Crear archivo de template
template_path = os.path.join(templates_dir, 'index.html')
with open(template_path, 'w', encoding='utf-8') as f:
    f.write(template_html)

# Crear template de error
error_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - Sistema de Apuestas de Tenis</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; text-align: center; }
        .error-card { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .error-icon { font-size: 4em; color: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-card">
            <div class="error-icon">⚠️</div>
            <h1>Error del Sistema</h1>
            <p>Ha ocurrido un error en el sistema:</p>
            <p><strong>{{ error }}</strong></p>
            <p>Por favor, intente nuevamente más tarde.</p>
            <a href="/" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Volver al Inicio</a>
        </div>
    </div>
</body>
</html>
"""

error_template_path = os.path.join(templates_dir, 'error.html')
with open(error_template_path, 'w', encoding='utf-8') as f:
    f.write(error_template)

def run_dashboard(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """
    Ejecutar el dashboard web.
    
    Args:
        host: Host del servidor
        port: Puerto del servidor
        debug: Modo debug
    """
    try:
        logger.info(f"Iniciando dashboard en http://{host}:{port}")
        
        if debug:
            app.run(host=host, port=port, debug=debug)
        else:
            socketio.run(app, host=host, port=port, debug=debug)
            
    except Exception as e:
        logger.error(f"Error ejecutando dashboard: {e}")

if __name__ == "__main__":
    # Ejecutar dashboard si se llama directamente
    run_dashboard(debug=True)
