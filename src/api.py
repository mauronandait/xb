#!/usr/bin/env python3
"""
API REST para el sistema de apuestas de tenis.
Proporciona endpoints para integración externa y automatización.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from functools import wraps
import jwt

from config import config
from database import db_manager
from betting_signals import generate_tennis_betting_signals
from backtest import run_tennis_backtest
from alerts import alert_manager

# Configurar logging
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY

# Habilitar CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

def require_api_key(f):
    """Decorador para requerir API key."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != config.get('API_KEY', 'default_key'):
            return jsonify({'error': 'API key requerida'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_jwt_token(f):
    """Decorador para requerir token JWT."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token JWT requerido'}), 401
        
        try:
            token = token.split(' ')[1]
            payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=['HS256'])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud del sistema."""
    try:
        # Verificar conexión a base de datos
        db_status = db_manager.test_connection()
        
        response = {
            'status': 'healthy' if db_status else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'database': 'connected' if db_status else 'disconnected',
            'services': {
                'database': db_status,
                'alerts': alert_manager.email_enabled or alert_manager.telegram_enabled,
                'signals': True
            }
        }
        
        status_code = 200 if db_status else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/signals', methods=['GET'])
@require_api_key
def get_signals():
    """Obtener señales de apuestas."""
    try:
        # Parámetros de consulta
        limit = request.args.get('limit', 50, type=int)
        confidence = request.args.get('confidence', 'all')
        min_ev = request.args.get('min_ev', 0.0, type=float)
        
        # Obtener partidos recientes
        matches = db_manager.get_recent_matches(limit=100)
        
        if not matches:
            return jsonify({'signals': [], 'message': 'No hay partidos disponibles'})
        
        # Generar señales
        signals, summary = generate_tennis_betting_signals(matches)
        
        # Filtrar por parámetros
        if confidence != 'all':
            signals = [s for s in signals if s['confidence_level'] == confidence]
        
        if min_ev > 0:
            signals = [s for s in signals if s['expected_value'] >= min_ev]
        
        # Limitar resultados
        signals = signals[:limit]
        
        response = {
            'signals': signals,
            'summary': summary,
            'filters_applied': {
                'confidence': confidence,
                'min_ev': min_ev,
                'limit': limit
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo señales: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals/<signal_id>', methods=['GET'])
@require_api_key
def get_signal(signal_id):
    """Obtener una señal específica por ID."""
    try:
        # Obtener partidos recientes
        matches = db_manager.get_recent_matches(limit=100)
        
        if not matches:
            return jsonify({'error': 'No hay partidos disponibles'}), 404
        
        # Generar señales
        signals, _ = generate_tennis_betting_signals(matches)
        
        # Buscar señal específica
        signal = next((s for s in signals if s.get('match_id') == signal_id), None)
        
        if not signal:
            return jsonify({'error': 'Señal no encontrada'}), 404
        
        return jsonify({'signal': signal})
        
    except Exception as e:
        logger.error(f"Error obteniendo señal: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches', methods=['GET'])
@require_api_key
def get_matches():
    """Obtener partidos disponibles."""
    try:
        # Parámetros de consulta
        limit = request.args.get('limit', 50, type=int)
        tournament = request.args.get('tournament')
        surface = request.args.get('surface')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Obtener partidos
        matches = db_manager.get_recent_matches(limit=limit)
        
        # Aplicar filtros
        if tournament:
            matches = [m for m in matches if m.get('tournament') == tournament]
        
        if surface:
            matches = [m for m in matches if m.get('surface') == surface]
        
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from)
                matches = [m for m in matches if m.get('match_time') >= date_from_obj]
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to)
                matches = [m for m in matches if m.get('match_time') <= date_to_obj]
            except ValueError:
                pass
        
        response = {
            'matches': matches,
            'total': len(matches),
            'filters_applied': {
                'tournament': tournament,
                'surface': surface,
                'date_from': date_from,
                'date_to': date_to,
                'limit': limit
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo partidos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backtest', methods=['POST'])
@require_api_key
def run_backtest():
    """Ejecutar backtesting de estrategias."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        # Parámetros del backtest
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        strategy = data.get('strategy', 'kelly_fractional')
        bankroll = data.get('bankroll', 10000)
        
        if not start_date or not end_date:
            return jsonify({'error': 'Fechas de inicio y fin requeridas'}), 400
        
        # Ejecutar backtest
        results = run_tennis_backtest(
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            bankroll=bankroll
        )
        
        response = {
            'backtest_results': results,
            'parameters': {
                'start_date': start_date,
                'end_date': end_date,
                'strategy': strategy,
                'bankroll': bankroll
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error ejecutando backtest: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
@require_api_key
def get_alerts():
    """Obtener historial de alertas."""
    try:
        # Parámetros de consulta
        alert_type = request.args.get('type')
        limit = request.args.get('limit', 100, type=int)
        
        # Obtener historial de alertas
        alerts = alert_manager.get_alert_history(alert_type=alert_type, limit=limit)
        stats = alert_manager.get_alert_stats()
        
        response = {
            'alerts': alerts,
            'stats': stats,
            'filters_applied': {
                'type': alert_type,
                'limit': limit
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/test', methods=['POST'])
@require_api_key
def test_alert():
    """Probar sistema de alertas."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        alert_type = data.get('type', 'system')
        message = data.get('message', 'Prueba del sistema de alertas')
        severity = data.get('severity', 'info')
        
        # Enviar alerta de prueba
        success = alert_manager.send_system_alert(alert_type, message, severity)
        
        response = {
            'success': success,
            'alert_sent': {
                'type': alert_type,
                'message': message,
                'severity': severity
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error probando alerta: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_system_stats():
    """Obtener estadísticas del sistema."""
    try:
        # Obtener estadísticas de la base de datos
        db_stats = db_manager.get_database_stats()
        
        # Obtener estadísticas de alertas
        alert_stats = alert_manager.get_alert_stats()
        
        # Obtener partidos recientes para estadísticas
        recent_matches = db_manager.get_recent_matches(limit=100)
        signals, summary = generate_tennis_betting_signals(recent_matches)
        
        response = {
            'database': db_stats,
            'alerts': alert_stats,
            'signals': summary,
            'system': {
                'uptime': 'N/A',  # TODO: Implementar cálculo de uptime
                'version': '1.0.0',
                'environment': 'development' if not config.is_production() else 'production'
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh', methods=['POST'])
@require_api_key
def refresh_data():
    """Forzar actualización de datos."""
    try:
        # TODO: Implementar actualización de datos
        # Por ahora, solo retornamos éxito
        
        response = {
            'success': True,
            'message': 'Actualización de datos iniciada',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error actualizando datos: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """Manejar errores 404."""
    return jsonify({'error': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Manejar errores 500."""
    return jsonify({'error': 'Error interno del servidor'}), 500

def run_api_server(host: str = '0.0.0.0', port: int = 8000, debug: bool = False):
    """Ejecutar servidor de API."""
    try:
        logger.info(f"🚀 Iniciando API REST en http://{host}:{port}")
        
        if debug:
            app.run(host=host, port=port, debug=True)
        else:
            from waitress import serve
            serve(app, host=host, port=port)
            
    except Exception as e:
        logger.error(f"Error iniciando API: {e}")
        raise

if __name__ == '__main__':
    # Ejecutar API si se llama directamente
    run_api_server(debug=True)
