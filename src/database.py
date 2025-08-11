"""
Módulo de base de datos para el sistema de apuestas de tenis.
Incluye conexión a PostgreSQL, creación de tablas y operaciones CRUD básicas.
"""

import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
from src.config import config

logger = logging.getLogger(__name__)

class TennisDatabase:
    """Clase para gestionar la base de datos de tenis."""
    
    def __init__(self):
        """Inicializar la conexión a la base de datos."""
        self.connection_string = config.get_database_url()
        self.engine = None
        self.connection = None
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """
        Establecer conexión a la base de datos.
        
        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        try:
            self.engine = create_engine(self.connection_string)
            self.connection = self.engine.connect()
            self.logger.info("Conexión a la base de datos establecida")
            return True
        except Exception as e:
            self.logger.error(f"Error conectando a la base de datos: {e}")
            return False
    
    def disconnect(self):
        """Cerrar conexión a la base de datos."""
        try:
            if self.connection:
                self.connection.close()
            if self.engine:
                self.engine.dispose()
            self.logger.info("Conexión a la base de datos cerrada")
        except Exception as e:
            self.logger.error(f"Error cerrando conexión: {e}")
    
    def create_tables(self) -> bool:
        """
        Crear las tablas necesarias para el sistema.
        
        Returns:
            True si las tablas se crearon exitosamente
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            # Crear tablas
            self._create_matches_raw_table()
            self._create_odds_raw_table()
            self._create_matches_processed_table()
            self._create_signals_table()
            self._create_results_table()
            self._create_models_table()
            
            self.logger.info("Todas las tablas fueron creadas exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creando tablas: {e}")
            return False
    
    def _create_matches_raw_table(self):
        """Crear tabla de partidos crudos."""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS matches_raw (
                id SERIAL PRIMARY KEY,
                match_id VARCHAR(255) UNIQUE NOT NULL,
                tournament VARCHAR(255),
                player1 VARCHAR(255),
                player2 VARCHAR(255),
                match_time TIMESTAMP,
                surface VARCHAR(100),
                round VARCHAR(100),
                raw_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            self.connection.execute(text(create_table_sql))
            self.connection.commit()
            self.logger.info("Tabla matches_raw creada/verificada")
            
        except Exception as e:
            self.logger.error(f"Error creando tabla matches_raw: {e}")
            raise
    
    def _create_odds_raw_table(self):
        """Crear tabla de cuotas crudas."""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS odds_raw (
                id SERIAL PRIMARY KEY,
                match_id VARCHAR(255) REFERENCES matches_raw(match_id),
                player1_odds DECIMAL(10,2),
                player2_odds DECIMAL(10,2),
                bookmaker VARCHAR(100),
                odds_time TIMESTAMP,
                raw_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            self.connection.execute(text(create_table_sql))
            self.connection.commit()
            self.logger.info("Tabla odds_raw creada/verificada")
            
        except Exception as e:
            self.logger.error(f"Error creando tabla odds_raw: {e}")
            raise
    
    def _create_matches_processed_table(self):
        """Crear tabla de partidos procesados."""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS matches_processed (
                id SERIAL PRIMARY KEY,
                match_id VARCHAR(255) REFERENCES matches_raw(match_id),
                tournament VARCHAR(255),
                player1 VARCHAR(255),
                player2 VARCHAR(255),
                match_time TIMESTAMP,
                player1_odds DECIMAL(10,2),
                player2_odds DECIMAL(10,2),
                player1_implied_prob DECIMAL(5,4),
                player2_implied_prob DECIMAL(5,4),
                player1_prob DECIMAL(5,4),
                player2_prob DECIMAL(5,4),
                margin DECIMAL(5,4),
                tournament_level VARCHAR(100),
                surface_type VARCHAR(100),
                features JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            self.connection.execute(text(create_table_sql))
            self.connection.commit()
            self.logger.info("Tabla matches_processed creada/verificada")
            
        except Exception as e:
            self.logger.error(f"Error creando tabla matches_processed: {e}")
            raise
    
    def _create_signals_table(self):
        """Crear tabla de señales de apuesta."""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS signals (
                id SERIAL PRIMARY KEY,
                match_id VARCHAR(255) REFERENCES matches_raw(match_id),
                selection VARCHAR(255),
                opponent VARCHAR(255),
                tournament VARCHAR(255),
                match_time TIMESTAMP,
                odds DECIMAL(10,2),
                model_prob DECIMAL(5,4),
                implied_prob DECIMAL(5,4),
                ev DECIMAL(6,4),
                kelly_stake DECIMAL(6,4),
                recommended_stake DECIMAL(10,2),
                selection_type VARCHAR(50),
                confidence DECIMAL(5,4),
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            self.connection.execute(text(create_table_sql))
            self.connection.commit()
            self.logger.info("Tabla signals creada/verificada")
            
        except Exception as e:
            self.logger.error(f"Error creando tabla signals: {e}")
            raise
    
    def _create_results_table(self):
        """Crear tabla de resultados de partidos."""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                match_id VARCHAR(255) REFERENCES matches_raw(match_id),
                winner VARCHAR(255),
                score VARCHAR(100),
                sets_won_player1 INTEGER,
                sets_won_player2 INTEGER,
                games_won_player1 INTEGER,
                games_won_player2 INTEGER,
                match_duration INTEGER,
                result_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            self.connection.execute(text(create_table_sql))
            self.connection.commit()
            self.logger.info("Tabla results creada/verificada")
            
        except Exception as e:
            self.logger.error(f"Error creando tabla results: {e}")
            raise
    
    def _create_models_table(self):
        """Crear tabla de modelos de ML."""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS models (
                id SERIAL PRIMARY KEY,
                model_name VARCHAR(255),
                model_type VARCHAR(100),
                version VARCHAR(50),
                features JSONB,
                hyperparameters JSONB,
                performance_metrics JSONB,
                model_file_path VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT FALSE
            );
            """
            
            self.connection.execute(text(create_table_sql))
            self.connection.commit()
            self.logger.info("Tabla models creada/verificada")
            
        except Exception as e:
            self.logger.error(f"Error creando tabla models: {e}")
            raise
    
    def insert_matches_raw(self, matches_data: List[Dict]) -> bool:
        """
        Insertar partidos crudos en la base de datos.
        
        Args:
            matches_data: Lista de diccionarios con datos de partidos
            
        Returns:
            True si la inserción fue exitosa
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            for match in matches_data:
                insert_sql = """
                INSERT INTO matches_raw (match_id, tournament, player1, player2, match_time, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) 
                DO UPDATE SET 
                    tournament = EXCLUDED.tournament,
                    player1 = EXCLUDED.player1,
                    player2 = EXCLUDED.player2,
                    match_time = EXCLUDED.match_time,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                """
                
                self.connection.execute(text(insert_sql), (
                    match['match_id'],
                    match.get('tournament'),
                    match.get('player1'),
                    match.get('player2'),
                    match.get('match_time'),
                    match
                ))
            
            self.connection.commit()
            self.logger.info(f"{len(matches_data)} partidos insertados/actualizados")
            return True
            
        except Exception as e:
            self.logger.error(f"Error insertando partidos: {e}")
            self.connection.rollback()
            return False
    
    def insert_odds_raw(self, odds_data: List[Dict]) -> bool:
        """
        Insertar cuotas crudas en la base de datos.
        
        Args:
            odds_data: Lista de diccionarios con datos de cuotas
            
        Returns:
            True si la inserción fue exitosa
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            for odds in odds_data:
                insert_sql = """
                INSERT INTO odds_raw (match_id, player1_odds, player2_odds, bookmaker, odds_time, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                self.connection.execute(text(insert_sql), (
                    odds['match_id'],
                    odds.get('player1_odds'),
                    odds.get('player2_odds'),
                    odds.get('bookmaker', '1xBet'),
                    odds.get('odds_time', datetime.now()),
                    odds
                ))
            
            self.connection.commit()
            self.logger.info(f"{len(odds_data)} registros de cuotas insertados")
            return True
            
        except Exception as e:
            self.logger.error(f"Error insertando cuotas: {e}")
            self.connection.rollback()
            return False
    
    def insert_processed_matches(self, processed_data: pd.DataFrame) -> bool:
        """
        Insertar partidos procesados en la base de datos.
        
        Args:
            processed_data: DataFrame con datos procesados
            
        Returns:
            True si la inserción fue exitosa
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            # Convertir DataFrame a lista de diccionarios
            records = processed_data.to_dict('records')
            
            for record in records:
                insert_sql = """
                INSERT INTO matches_processed (
                    match_id, tournament, player1, player2, match_time,
                    player1_odds, player2_odds, player1_implied_prob, player2_implied_prob,
                    player1_prob, player2_prob, margin, tournament_level, surface_type, features
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) 
                DO UPDATE SET 
                    player1_odds = EXCLUDED.player1_odds,
                    player2_odds = EXCLUDED.player2_odds,
                    player1_implied_prob = EXCLUDED.player1_implied_prob,
                    player2_implied_prob = EXCLUDED.player2_implied_prob,
                    player1_prob = EXCLUDED.player1_prob,
                    player2_prob = EXCLUDED.player2_prob,
                    margin = EXCLUDED.margin,
                    features = EXCLUDED.features
                """
                
                self.connection.execute(text(insert_sql), (
                    record['match_id'],
                    record.get('tournament'),
                    record.get('player1'),
                    record.get('player2'),
                    record.get('match_time'),
                    record.get('player1_odds'),
                    record.get('player2_odds'),
                    record.get('player1_implied_prob'),
                    record.get('player2_implied_prob'),
                    record.get('player1_prob'),
                    record.get('player2_prob'),
                    record.get('margin'),
                    record.get('tournament_level'),
                    record.get('surface_type'),
                    record.to_dict()
                ))
            
            self.connection.commit()
            self.logger.info(f"{len(records)} partidos procesados insertados/actualizados")
            return True
            
        except Exception as e:
            self.logger.error(f"Error insertando partidos procesados: {e}")
            self.connection.rollback()
            return False
    
    def get_recent_matches(self, hours: int = 24) -> pd.DataFrame:
        """
        Obtener partidos recientes de la base de datos.
        
        Args:
            hours: Número de horas hacia atrás para buscar
            
        Returns:
            DataFrame con partidos recientes
        """
        try:
            if not self.connection:
                if not self.connect():
                    return pd.DataFrame()
            
            query = """
            SELECT * FROM matches_processed 
            WHERE match_time >= NOW() - INTERVAL '%s hours'
            ORDER BY match_time DESC
            """
            
            df = pd.read_sql(query, self.connection, params=[hours])
            self.logger.info(f"Se obtuvieron {len(df)} partidos recientes")
            return df
            
        except Exception as e:
            self.logger.error(f"Error obteniendo partidos recientes: {e}")
            return pd.DataFrame()
    
    def get_active_signals(self) -> pd.DataFrame:
        """
        Obtener señales de apuesta activas.
        
        Returns:
            DataFrame con señales activas
        """
        try:
            if not self.connection:
                if not self.connect():
                    return pd.DataFrame()
            
            query = """
            SELECT * FROM signals 
            WHERE status = 'active' AND match_time > NOW()
            ORDER BY ev DESC
            """
            
            df = pd.read_sql(query, self.connection)
            self.logger.info(f"Se obtuvieron {len(df)} señales activas")
            return df
            
        except Exception as e:
            self.logger.error(f"Error obteniendo señales: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Cerrar conexión a la base de datos."""
        self.disconnect()

# Función de conveniencia para crear la base de datos
def setup_database() -> bool:
    """
    Configurar la base de datos completa.
    
    Returns:
        True si la configuración fue exitosa
    """
    try:
        db = TennisDatabase()
        if db.connect():
            success = db.create_tables()
            db.close()
            return success
        return False
    except Exception as e:
        logger.error(f"Error configurando base de datos: {e}")
        return False

