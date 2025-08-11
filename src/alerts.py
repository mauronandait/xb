#!/usr/bin/env python3
"""
Sistema de alertas para el sistema de apuestas de tenis.
Proporciona notificaciones por email y Telegram para eventos importantes.
"""

import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from config import config

logger = logging.getLogger(__name__)

class AlertManager:
    """Gestor de alertas del sistema."""
    
    def __init__(self):
        """Inicializar gestor de alertas."""
        self.logger = logging.getLogger(__name__)
        self.email_enabled = config.ALERTS_EMAIL_ENABLED
        self.telegram_enabled = config.ALERTS_TELEGRAM_ENABLED
        
        # Configuración de email
        self.smtp_server = config.EMAIL_SMTP_SERVER
        self.smtp_port = config.EMAIL_SMTP_PORT
        self.email_user = config.EMAIL_USER
        self.email_password = config.EMAIL_PASSWORD
        self.email_recipients = config.EMAIL_RECIPIENTS.split(',') if config.EMAIL_RECIPIENTS else []
        
        # Configuración de Telegram
        self.telegram_bot_token = config.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = config.TELEGRAM_CHAT_ID
        
        # Historial de alertas
        self.alert_history = []
        self.max_history = 1000
    
    def send_value_bet_alert(self, signal: Dict[str, Any]) -> bool:
        """
        Enviar alerta cuando se detecte un value bet.
        
        Args:
            signal: Señal de apuesta detectada
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            subject = f"🎾 Value Bet Detectado: {signal.get('player_name', 'N/A')}"
            
            message = self._format_value_bet_message(signal)
            
            success = True
            
            # Enviar por email
            if self.email_enabled:
                email_sent = self._send_email(subject, message)
                success = success and email_sent
            
            # Enviar por Telegram
            if self.telegram_enabled:
                telegram_sent = self._send_telegram(message)
                success = success and telegram_sent
            
            # Registrar alerta
            self._log_alert('value_bet', signal, success)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error enviando alerta de value bet: {e}")
            return False
    
    def send_odds_change_alert(self, match_id: str, old_odds: float, new_odds: float, 
                              player: str, change_percent: float) -> bool:
        """
        Enviar alerta cuando cambien significativamente las cuotas.
        
        Args:
            match_id: ID del partido
            old_odds: Cuotas anteriores
            new_odds: Nuevas cuotas
            player: Nombre del jugador
            change_percent: Porcentaje de cambio
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            subject = f"📊 Cambio de Cuotas: {player}"
            
            message = f"""
🎾 **Cambio Significativo de Cuotas**

**Partido:** {match_id}
**Jugador:** {player}
**Cuotas Anteriores:** {old_odds:.2f}
**Nuevas Cuotas:** {new_odds:.2f}
**Cambio:** {change_percent:+.2f}%

**Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ **Revisar si esto afecta nuestras señales de apuesta**
            """.strip()
            
            success = True
            
            # Enviar por email
            if self.email_enabled:
                email_sent = self._send_email(subject, message)
                success = success and email_sent
            
            # Enviar por Telegram
            if self.telegram_enabled:
                telegram_sent = self._send_telegram(message)
                success = success and telegram_sent
            
            # Registrar alerta
            self._log_alert('odds_change', {
                'match_id': match_id,
                'player': player,
                'old_odds': old_odds,
                'new_odds': new_odds,
                'change_percent': change_percent
            }, success)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error enviando alerta de cambio de cuotas: {e}")
            return False
    
    def send_system_alert(self, alert_type: str, message: str, severity: str = 'info') -> bool:
        """
        Enviar alerta del sistema.
        
        Args:
            alert_type: Tipo de alerta
            message: Mensaje de la alerta
            severity: Severidad (info, warning, error, critical)
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            # Emojis según severidad
            severity_emojis = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'critical': '🚨'
            }
            
            emoji = severity_emojis.get(severity, 'ℹ️')
            subject = f"{emoji} Alerta del Sistema: {alert_type}"
            
            formatted_message = f"""
🚨 **Alerta del Sistema**

**Tipo:** {alert_type}
**Severidad:** {severity.upper()}
**Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Mensaje:**
{message}

---
Sistema de Apuestas de Tenis
            """.strip()
            
            success = True
            
            # Enviar por email
            if self.email_enabled:
                email_sent = self._send_email(subject, formatted_message)
                success = success and email_sent
            
            # Enviar por Telegram
            if self.telegram_enabled:
                telegram_sent = self._send_telegram(formatted_message)
                success = success and telegram_sent
            
            # Registrar alerta
            self._log_alert('system', {
                'type': alert_type,
                'message': message,
                'severity': severity
            }, success)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error enviando alerta del sistema: {e}")
            return False
    
    def _format_value_bet_message(self, signal: Dict[str, Any]) -> str:
        """Formatear mensaje de value bet."""
        return f"""
🎾 **¡Value Bet Detectado!**

**Jugador:** {signal.get('player_name', 'N/A')}
**Oponente:** {signal.get('player2', 'N/A')}
**Torneo:** {signal.get('tournament', 'N/A')}
**Superficie:** {signal.get('surface', 'N/A')}
**Ronda:** {signal.get('round', 'N/A')}

**Cuotas:** {signal.get('odds', 0):.2f}
**Probabilidad del Modelo:** {signal.get('model_probability', 0):.1%}
**Probabilidad Implícita:** {signal.get('implied_probability', 0):.1%}
**Valor Esperado:** {signal.get('expected_value', 0):.1%}

**Recomendación de Stake:**
- Stake Kelly: {signal.get('kelly_stake', 0):.1%}
- Stake Recomendado: ${signal.get('recommended_stake', 0):.2f}

**Confianza del Modelo:** {signal.get('confidence_level', 'N/A')}

**Hora de Detección:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💰 **¡Actúa rápido antes de que cambien las cuotas!**
        """.strip()
    
    def _send_email(self, subject: str, message: str) -> bool:
        """Enviar email."""
        try:
            if not self.email_user or not self.email_password:
                self.logger.warning("Configuración de email incompleta")
                return False
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = ', '.join(self.email_recipients)
            msg['Subject'] = subject
            
            # Agregar cuerpo del mensaje
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # Enviar email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            self.logger.info(f"Email enviado: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enviando email: {e}")
            return False
    
    def _send_telegram(self, message: str) -> bool:
        """Enviar mensaje por Telegram."""
        try:
            if not self.telegram_bot_token or not self.telegram_chat_id:
                self.logger.warning("Configuración de Telegram incompleta")
                return False
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            self.logger.info("Mensaje de Telegram enviado")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enviando mensaje de Telegram: {e}")
            return False
    
    def _log_alert(self, alert_type: str, data: Dict[str, Any], success: bool):
        """Registrar alerta en el historial."""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'data': data,
            'success': success
        }
        
        self.alert_history.append(alert)
        
        # Mantener solo las últimas alertas
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
    
    def get_alert_history(self, alert_type: Optional[str] = None, 
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtener historial de alertas.
        
        Args:
            alert_type: Filtrar por tipo de alerta
            limit: Número máximo de alertas a retornar
            
        Returns:
            Lista de alertas
        """
        if alert_type:
            filtered = [a for a in self.alert_history if a['type'] == alert_type]
        else:
            filtered = self.alert_history
        
        return filtered[-limit:]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de alertas."""
        total_alerts = len(self.alert_history)
        successful_alerts = sum(1 for a in self.alert_history if a['success'])
        failed_alerts = total_alerts - successful_alerts
        
        # Contar por tipo
        type_counts = {}
        for alert in self.alert_history:
            alert_type = alert['type']
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
        
        return {
            'total_alerts': total_alerts,
            'successful_alerts': successful_alerts,
            'failed_alerts': failed_alerts,
            'success_rate': (successful_alerts / total_alerts * 100) if total_alerts > 0 else 0,
            'type_counts': type_counts,
            'last_alert': self.alert_history[-1] if self.alert_history else None
        }

# Instancia global del gestor de alertas
alert_manager = AlertManager()

def send_value_bet_alert(signal: Dict[str, Any]) -> bool:
    """Función de conveniencia para enviar alertas de value bet."""
    return alert_manager.send_value_bet_alert(signal)

def send_odds_change_alert(match_id: str, old_odds: float, new_odds: float, 
                           player: str, change_percent: float) -> bool:
    """Función de conveniencia para enviar alertas de cambio de cuotas."""
    return alert_manager.send_odds_change_alert(match_id, old_odds, new_odds, player, change_percent)

def send_system_alert(alert_type: str, message: str, severity: str = 'info') -> bool:
    """Función de conveniencia para enviar alertas del sistema."""
    return alert_manager.send_system_alert(alert_type, message, severity)
