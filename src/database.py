#!/usr/bin/env python3
"""
Sistema de base de datos para el sistema de apuestas de tenis.
Incluye modelos SQLAlchemy, conexión pooling y funciones de utilidad.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.sql import text
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json
import os

from config import config

# Configurar logging
logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

class DatabaseManager:
    """Gestor de base de datos con pooling y manejo de errores."""
    
    def __init__(self):
        """Inicializar gestor de base de datos."""
        self.engine = None
        self.SessionLocal = None
        self.session_factory = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Inicializar motor de base de datos con configuración optimizada."""
        try:
            database_url = config.get_database_url()
            
            # Configuración del engine con pooling
            engine_config = {
                'poolclass': QueuePool,
                'pool_size': config.db_config['pool_size'],
                'max_overflow': config.db_config['max_overflow'],
                'pool_timeout': config.db_config['pool_timeout'],
                'pool_recycle': config.db_config['pool_recycle'],
                'pool_pre_ping': True,
                'echo': config.DASHBOARD_DEBUG,
                'connect_args': {
                    'connect_timeout': 10,
                    'application_name': 'tennis_betting_system',
                    'client_encoding': 'utf8'
                }
            }
            
            self.engine = create_engine(database_url, **engine_config)
            
            # Crear sesión factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            # Crear sesión thread-local
            self.SessionLocal = scoped_session(self.session_factory)
            
            logger.info("Motor de base de datos inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando motor de base de datos: {e}")
            raise
    
    def get_session(self) -> Session:
        """Obtener sesión de base de datos."""
        if not self.SessionLocal:
            raise RuntimeError("Base de datos no inicializada")
        return self.SessionLocal()
    
    @contextmanager
    def get_db_session(self):
        """Context manager para sesiones de base de datos."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error en sesión de base de datos: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Probar conexión a base de datos."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                return True
        except Exception as e:
            logger.error(f"Error probando conexión: {e}")
            return False
    
    def create_tables(self):
        """Crear todas las tablas definidas en los modelos."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Tablas creadas correctamente")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
            raise
    
    def drop_tables(self):
        """Eliminar todas las tablas (¡CUIDADO!)."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("Todas las tablas eliminadas")
        except Exception as e:
            logger.error(f"Error eliminando tablas: {e}")
            raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """Obtener información de la base de datos."""
        try:
            with self.engine.connect() as conn:
                # Información de versiones
                version_result = conn.execute(text("SELECT version()"))
                version = version_result.fetchone()[0]
                
                # Información de tablas
                tables_result = conn.execute(text("""
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                tables = [{"name": row[0], "type": row[1]} for row in tables_result]
                
                # Estadísticas de conexiones
                connections_result = conn.execute(text("""
                    SELECT count(*) as active_connections 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """))
                active_connections = connections_result.fetchone()[0]
                
                return {
                    "version": version,
                    "tables": tables,
                    "active_connections": active_connections,
                    "pool_size": config.db_config['pool_size'],
                    "max_overflow": config.db_config['max_overflow']
                }
        except Exception as e:
            logger.error(f"Error obteniendo información de BD: {e}")
            return {"error": str(e)}
    
    def execute_raw_sql(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Ejecutar SQL raw y retornar resultados como diccionarios."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error ejecutando SQL raw: {e}")
            raise
    
    def backup_database(self, backup_path: str) -> bool:
        """Crear backup de la base de datos."""
        try:
            import subprocess
            backup_cmd = [
                'pg_dump',
                '-h', config.DB_HOST,
                '-p', str(config.DB_PORT),
                '-U', config.DB_USER,
                '-d', config.DB_NAME,
                '-f', backup_path,
                '--format=custom',
                '--verbose'
            ]
            
            # Establecer variable de entorno para contraseña
            env = os.environ.copy()
            env['PGPASSWORD'] = config.DB_PASSWORD
            
            result = subprocess.run(
                backup_cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Backup creado exitosamente en: {backup_path}")
                return True
            else:
                logger.error(f"Error en backup: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """Restaurar base de datos desde backup."""
        try:
            import subprocess
            restore_cmd = [
                'pg_restore',
                '-h', config.DB_HOST,
                '-p', str(config.DB_PORT),
                '-U', config.DB_USER,
                '-d', config.DB_NAME,
                '--clean',
                '--if-exists',
                '--verbose',
                backup_path
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = config.DB_PASSWORD
            
            result = subprocess.run(
                restore_cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Base de datos restaurada exitosamente")
                return True
            else:
                logger.error(f"Error en restauración: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error restaurando BD: {e}")
            return False

# Modelos SQLAlchemy
class Tournament(Base):
    """Modelo para torneos de tenis."""
    __tablename__ = 'tournaments'
    
    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    surface = Column(String(50), nullable=False)
    country = Column(String(100))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    prize_money = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    matches = relationship("MatchRaw", back_populates="tournament")
    
    def __repr__(self):
        return f"<Tournament(name='{self.name}', category='{self.category}', surface='{self.surface}')>"

class Player(Base):
    """Modelo para jugadores de tenis."""
    __tablename__ = 'players'
    
    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100))
    ranking = Column(Integer)
    ranking_points = Column(Integer)
    birth_date = Column(DateTime)
    height_cm = Column(Integer)
    weight_kg = Column(Float)
    playing_style = Column(String(100))
    preferred_surface = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    matches_as_player1 = relationship("MatchRaw", foreign_keys="MatchRaw.player1_id", back_populates="player1")
    matches_as_player2 = relationship("MatchRaw", foreign_keys="MatchRaw.player2_id", back_populates="player2")
    matches_won = relationship("MatchRaw", foreign_keys="MatchRaw.winner_id")
    
    def __repr__(self):
        return f"<Player(name='{self.name}', country='{self.country}', ranking={self.ranking})>"

class MatchRaw(Base):
    """Modelo para partidos crudos."""
    __tablename__ = 'matches_raw'
    
    id = Column(String, primary_key=True)
    external_id = Column(String(255), unique=True)
    tournament_id = Column(String, ForeignKey('tournaments.id'))
    player1_id = Column(String, ForeignKey('players.id'))
    player2_id = Column(String, ForeignKey('players.id'))
    match_date = Column(DateTime)
    status = Column(String(50), default='scheduled')
    score = Column(String(100))
    winner_id = Column(String, ForeignKey('players.id'))
    sets_played = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    surface = Column(String(50))
    round = Column(String(100))
    best_of = Column(Integer, default=3)
    raw_data = Column(JSON)
    source = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    tournament = relationship("Tournament", back_populates="matches")
    player1 = relationship("Player", foreign_keys=[player1_id], back_populates="matches_as_player1")
    player2 = relationship("Player", foreign_keys=[player2_id], back_populates="matches_as_player2")
    winner = relationship("Player", foreign_keys=[winner_id], back_populates="matches_won")
    odds = relationship("OddsRaw", back_populates="match")
    processed_match = relationship("MatchProcessed", back_populates="match_raw", uselist=False)
    betting_signals = relationship("BettingSignal", back_populates="match")
    
    def __repr__(self):
        return f"<MatchRaw(id='{self.id}', player1='{self.player1_id}', player2='{self.player2_id}', date='{self.match_date}')>"

class OddsRaw(Base):
    """Modelo para cuotas crudas."""
    __tablename__ = 'odds_raw'
    
    id = Column(String, primary_key=True)
    match_id = Column(String, ForeignKey('matches_raw.id', ondelete='CASCADE'))
    bookmaker = Column(String(100), nullable=False)
    player1_odds = Column(Float)
    player2_odds = Column(Float)
    draw_odds = Column(Float)
    margin = Column(Float)
    raw_data = Column(JSON)
    odds_timestamp = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    match = relationship("MatchRaw", back_populates="odds")
    
    def __repr__(self):
        return f"<OddsRaw(match_id='{self.match_id}', bookmaker='{self.bookmaker}', player1_odds={self.player1_odds})>"

class MatchProcessed(Base):
    """Modelo para partidos procesados."""
    __tablename__ = 'matches_processed'
    
    id = Column(String, primary_key=True)
    match_raw_id = Column(String, ForeignKey('matches_raw.id', ondelete='CASCADE'))
    player1_implied_prob = Column(Float)
    player2_implied_prob = Column(Float)
    player1_model_prob = Column(Float)
    player2_model_prob = Column(Float)
    confidence_score = Column(Float)
    model_version = Column(String(50))
    features_used = Column(JSON)
    processing_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    match_raw = relationship("MatchRaw", back_populates="processed_match")
    
    def __repr__(self):
        return f"<MatchProcessed(match_raw_id='{self.match_raw_id}', confidence={self.confidence_score})>"

class BettingSignal(Base):
    """Modelo para señales de apuesta."""
    __tablename__ = 'betting_signals'
    
    id = Column(String, primary_key=True)
    match_id = Column(String, ForeignKey('matches_raw.id', ondelete='CASCADE'))
    selection = Column(String(255), nullable=False)
    odds = Column(Float, nullable=False)
    implied_probability = Column(Float, nullable=False)
    model_probability = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    kelly_stake = Column(Float, nullable=False)
    recommended_stake = Column(Float, nullable=False)
    confidence_level = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=False)
    signal_type = Column(String(50), nullable=False)
    status = Column(String(50), default='active')
    execution_price = Column(Float)
    execution_timestamp = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    match = relationship("MatchRaw", back_populates="betting_signals")
    executed_bets = relationship("ExecutedBet", back_populates="signal")
    
    def __repr__(self):
        return f"<BettingSignal(match_id='{self.match_id}', selection='{self.selection}', ev={self.expected_value})>"

class ExecutedBet(Base):
    """Modelo para apuestas ejecutadas."""
    __tablename__ = 'executed_bets'
    
    id = Column(String, primary_key=True)
    signal_id = Column(String, ForeignKey('betting_signals.id'))
    stake = Column(Float, nullable=False)
    odds = Column(Float, nullable=False)
    potential_profit = Column(Float, nullable=False)
    status = Column(String(50), default='pending')
    result = Column(String(50))
    profit_loss = Column(Float)
    execution_timestamp = Column(DateTime, default=datetime.utcnow)
    settlement_timestamp = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    signal = relationship("BettingSignal", back_populates="executed_bets")
    
    def __repr__(self):
        return f"<ExecutedBet(signal_id='{self.signal_id}', stake={self.stake}, status='{self.status}')>"

class BacktestResult(Base):
    """Modelo para resultados de backtesting."""
    __tablename__ = 'backtest_results'
    
    id = Column(String, primary_key=True)
    strategy_name = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_bankroll = Column(Float, nullable=False)
    final_bankroll = Column(Float, nullable=False)
    total_profit = Column(Float, nullable=False)
    roi = Column(Float, nullable=False)
    total_bets = Column(Integer, nullable=False)
    winning_bets = Column(Integer, nullable=False)
    losing_bets = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float)
    calmar_ratio = Column(Float)
    results_data = Column(JSON)
    parameters = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<BacktestResult(strategy='{self.strategy_name}', roi={self.roi}, profit={self.total_profit})>"

class SystemMetric(Base):
    """Modelo para métricas del sistema."""
    __tablename__ = 'system_metrics'
    
    id = Column(String, primary_key=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta_data = Column(JSON)
    
    def __repr__(self):
        return f"<SystemMetric(name='{self.metric_name}', value={self.metric_value}, unit='{self.metric_unit}')>"

class SystemLog(Base):
    """Modelo para logs del sistema."""
    __tablename__ = 'system_logs'
    
    id = Column(String, primary_key=True)
    level = Column(String(20), nullable=False)
    module = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta_data = Column(JSON)
    
    def __repr__(self):
        return f"<SystemLog(level='{self.level}', module='{self.module}', message='{self.message[:50]}...')>"

class SystemConfig(Base):
    """Modelo para configuración del sistema."""
    __tablename__ = 'system_config'
    
    id = Column(String, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    config_type = Column(String(50), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemConfig(key='{self.config_key}', value='{self.config_value}', type='{self.config_type}')>"

# Instancia global del gestor de base de datos
db_manager = DatabaseManager()

# Función de utilidad para obtener sesión
def get_db() -> Session:
    """Obtener sesión de base de datos para inyección de dependencias."""
    return db_manager.get_session()

# Función para inicializar base de datos
def init_database():
    """Inicializar base de datos y crear tablas."""
    try:
        # Probar conexión
        if not db_manager.test_connection():
            raise RuntimeError("No se pudo conectar a la base de datos")
        
        # Crear tablas
        db_manager.create_tables()
        
        logger.info("Base de datos inicializada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        return False

# Función para limpiar recursos
def cleanup_database():
    """Limpiar recursos de base de datos."""
    try:
        if db_manager.engine:
            db_manager.engine.dispose()
        logger.info("Recursos de base de datos limpiados")
    except Exception as e:
        logger.error(f"Error limpiando recursos de BD: {e}")

if __name__ == "__main__":
    # Inicializar base de datos si se ejecuta directamente
    init_database()

