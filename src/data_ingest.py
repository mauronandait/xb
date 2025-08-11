"""
Módulo de ingesta de datos para obtener información de tenis desde 1xBet.
Implementa tanto API como scraping como fallback.
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from .config import config

logger = logging.getLogger(__name__)

class TennisDataIngestor:
    """Clase para ingerir datos de tenis desde 1xBet."""
    
    def __init__(self):
        """Inicializar el ingestor de datos."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Intentar conectar a la base de datos
        try:
            self.db_engine = create_engine(config.get_database_url())
            self._create_tables()
            logger.info("Conexión a base de datos establecida")
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            self.db_engine = None
    
    def _create_tables(self):
        """Crear tablas necesarias si no existen."""
        if not self.db_engine:
            return
            
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS matches_raw (
            id SERIAL PRIMARY KEY,
            match_id VARCHAR(100) UNIQUE,
            tournament VARCHAR(255),
            player1 VARCHAR(255),
            player2 VARCHAR(255),
            match_time TIMESTAMP,
            sport_type VARCHAR(50),
            raw_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS odds_raw (
            id SERIAL PRIMARY KEY,
            match_id VARCHAR(100),
            bookmaker VARCHAR(100),
            market_type VARCHAR(100),
            selection VARCHAR(255),
            odds DECIMAL(10,3),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches_raw(match_id)
        );
        
        CREATE TABLE IF NOT EXISTS matches_processed (
            id SERIAL PRIMARY KEY,
            match_id VARCHAR(100),
            player1 VARCHAR(255),
            player2 VARCHAR(255),
            tournament VARCHAR(255),
            match_time TIMESTAMP,
            player1_odds DECIMAL(10,3),
            player2_odds DECIMAL(10,3),
            player1_prob DECIMAL(10,6),
            player2_prob DECIMAL(10,6),
            margin DECIMAL(10,6),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches_raw(match_id)
        );
        """
        
        try:
            with self.db_engine.connect() as conn:
                conn.execute(text(create_tables_sql))
                conn.commit()
            logger.info("Tablas creadas/verificadas exitosamente")
        except SQLAlchemyError as e:
            logger.error(f"Error creando tablas: {e}")
    
    def get_tennis_matches_api(self) -> Optional[List[Dict]]:
        """Intentar obtener partidos de tenis vía API oficial."""
        if not config.ONEXBET_API_KEY:
            logger.warning("No hay API key configurada para 1xBet")
            return None
            
        try:
            # Endpoint para deportes (ajustar según documentación real de 1xBet)
            url = f"{config.ONEXBET_API_URL}/sports"
            params = {
                'sport': 'tennis',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'api_key': config.ONEXBET_API_KEY
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Datos obtenidos vía API: {len(data.get('matches', []))} partidos")
            return data.get('matches', [])
            
        except requests.RequestException as e:
            logger.error(f"Error en API de 1xBet: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando respuesta de API: {e}")
            return None
    
    def get_tennis_matches_scraping(self) -> List[Dict]:
        """Obtener partidos de tenis vía scraping web."""
        logger.info("Iniciando scraping de 1xBet para tenis")
        
        try:
            # URL principal de deportes de 1xBet
            url = "https://1xbet.com/en/sports/tennis"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            matches = []
            
            # Buscar contenedores de partidos (ajustar selectores según estructura real)
            match_containers = soup.find_all('div', class_='match-container') or \
                              soup.find_all('div', class_='event-item') or \
                              soup.find_all('tr', class_='event-row')
            
            for container in match_containers:
                try:
                    match_data = self._extract_match_data(container)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    logger.warning(f"Error extrayendo datos de partido: {e}")
                    continue
            
            logger.info(f"Scraping completado: {len(matches)} partidos encontrados")
            return matches
            
        except requests.RequestException as e:
            logger.error(f"Error en scraping: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado en scraping: {e}")
            return []
    
    def _extract_match_data(self, container) -> Optional[Dict]:
        """Extraer datos de un contenedor de partido."""
        try:
            # Extraer información básica del partido
            # Estos selectores deben ajustarse según la estructura real de 1xBet
            tournament = container.find('span', class_='tournament') or \
                        container.find('td', class_='tournament')
            tournament = tournament.get_text(strip=True) if tournament else "Torneo Desconocido"
            
            # Buscar nombres de jugadores
            players = container.find_all('span', class_='player') or \
                     container.find_all('td', class_='player') or \
                     container.find_all('a', class_='player-name')
            
            if len(players) < 2:
                return None
                
            player1 = players[0].get_text(strip=True)
            player2 = players[1].get_text(strip=True)
            
            # Buscar cuotas
            odds_elements = container.find_all('span', class_='odds') or \
                           container.find_all('td', class_='odds') or \
                           container.find_all('button', class_='bet-button')
            
            odds = []
            for odds_elem in odds_elements[:2]:  # Solo primeras 2 cuotas (jugador 1 y 2)
                try:
                    odds_text = odds_elem.get_text(strip=True)
                    odds_value = float(odds_text.replace(',', '.'))
                    odds.append(odds_value)
                except (ValueError, AttributeError):
                    odds.append(None)
            
            # Generar ID único para el partido
            match_id = f"{player1}_{player2}_{tournament}_{datetime.now().strftime('%Y%m%d')}"
            
            return {
                'match_id': match_id,
                'tournament': tournament,
                'player1': player1,
                'player2': player2,
                'match_time': datetime.now(),  # Por defecto, ajustar si hay timestamp real
                'sport_type': 'tennis',
                'odds': odds,
                'raw_data': {
                    'html_content': str(container),
                    'extracted_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.warning(f"Error extrayendo datos del contenedor: {e}")
            return None
    
    def get_tennis_matches(self) -> List[Dict]:
        """Obtener partidos de tenis usando el método disponible."""
        # Intentar API primero
        matches = self.get_tennis_matches_api()
        
        # Si no hay API o falla, usar scraping
        if not matches and config.SCRAPING_ENABLED:
            logger.info("API no disponible, usando scraping como fallback")
            matches = self.get_tennis_matches_scraping()
        
        if not matches:
            logger.warning("No se pudieron obtener partidos de tenis")
            return []
        
        return matches
    
    def save_matches_to_db(self, matches: List[Dict]) -> bool:
        """Guardar partidos en la base de datos."""
        if not self.db_engine or not matches:
            return False
        
        try:
            with self.db_engine.connect() as conn:
                for match in matches:
                    # Insertar partido
                    insert_match_sql = """
                    INSERT INTO matches_raw (match_id, tournament, player1, player2, match_time, sport_type, raw_data)
                    VALUES (:match_id, :tournament, :player1, :player2, :match_time, :sport_type, :raw_data)
                    ON CONFLICT (match_id) DO UPDATE SET
                        raw_data = EXCLUDED.raw_data,
                        created_at = CURRENT_TIMESTAMP
                    """
                    
                    conn.execute(text(insert_match_sql), {
                        'match_id': match['match_id'],
                        'tournament': match['tournament'],
                        'player1': match['player1'],
                        'player2': match['player2'],
                        'match_time': match['match_time'],
                        'sport_type': match['sport_type'],
                        'raw_data': json.dumps(match['raw_data'])
                    })
                    
                    # Insertar cuotas si están disponibles
                    if 'odds' in match and match['odds']:
                        for i, odds_value in enumerate(match['odds']):
                            if odds_value is not None:
                                insert_odds_sql = """
                                INSERT INTO odds_raw (match_id, bookmaker, market_type, selection, odds)
                                VALUES (:match_id, '1xbet', 'match_winner', :selection, :odds)
                                """
                                
                                selection = match['player1'] if i == 0 else match['player2']
                                conn.execute(text(insert_odds_sql), {
                                    'match_id': match['match_id'],
                                    'selection': selection,
                                    'odds': odds_value
                                })
                
                conn.commit()
                logger.info(f"{len(matches)} partidos guardados en la base de datos")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error guardando en base de datos: {e}")
            return False
    
    def calculate_implied_probabilities(self, matches: List[Dict]) -> List[Dict]:
        """Calcular probabilidades implícitas para los partidos."""
        processed_matches = []
        
        for match in matches:
            if 'odds' not in match or len(match['odds']) < 2:
                continue
                
            odds1, odds2 = match['odds'][0], match['odds'][1]
            
            if odds1 is None or odds2 is None:
                continue
            
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
            
            processed_match = {
                **match,
                'player1_odds': odds1,
                'player2_odds': odds2,
                'player1_prob': prob1_adjusted,
                'player2_prob': prob2_adjusted,
                'margin': margin,
                'total_prob': total_prob
            }
            
            processed_matches.append(processed_match)
        
        return processed_matches
    
    def run_data_ingestion(self) -> List[Dict]:
        """Ejecutar el proceso completo de ingesta de datos."""
        logger.info("Iniciando proceso de ingesta de datos de tenis")
        
        # Obtener partidos
        matches = self.get_tennis_matches()
        
        if not matches:
            logger.warning("No se obtuvieron partidos de tenis")
            return []
        
        # Guardar en base de datos
        if self.db_engine:
            self.save_matches_to_db(matches)
        
        # Calcular probabilidades implícitas
        processed_matches = self.calculate_implied_probabilities(matches)
        
        logger.info(f"Ingesta completada: {len(processed_matches)} partidos procesados")
        return processed_matches

def main():
    """Función principal para ejecutar la ingesta de datos."""
    # Configurar logging
    config.setup_logging()
    
    # Crear instancia del ingestor
    ingestor = TennisDataIngestor()
    
    # Ejecutar ingesta
    matches = ingestor.run_data_ingestion()
    
    # Mostrar resultados
    if matches:
        print(f"\n=== PARTIDOS DE TENIS DISPONIBLES HOY ===")
        print(f"Total de partidos: {len(matches)}\n")
        
        for i, match in enumerate(matches, 1):
            print(f"{i}. {match['tournament']}")
            print(f"   {match['player1']} vs {match['player2']}")
            print(f"   Cuotas: {match['player1']} @ {match['player1_odds']:.2f} | {match['player2']} @ {match['player2_odds']:.2f}")
            print(f"   Probabilidades: {match['player1_prob']:.1%} | {match['player2_prob']:.1%}")
            print(f"   Margen: {match['margin']:.2%}")
            print()
    else:
        print("No se pudieron obtener partidos de tenis")

if __name__ == "__main__":
    main()
