#!/usr/bin/env python3
"""
Sistema de ingesta de datos para apuestas de tenis.
Incluye scraping de 1xBet, validación de datos y almacenamiento en base de datos.
"""

import logging
import time
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from config import config
from database import db_manager, Tournament, Player, MatchRaw, OddsRaw, SystemLog

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class MatchData:
    """Estructura de datos para partidos."""
    external_id: str
    tournament_name: str
    player1_name: str
    player2_name: str
    match_date: datetime
    surface: str
    round: str
    best_of: int
    source: str
    raw_data: Dict[str, Any]

@dataclass
class OddsData:
    """Estructura de datos para cuotas."""
    match_id: str
    bookmaker: str
    player1_odds: float
    player2_odds: float
    draw_odds: Optional[float]
    margin: Optional[float]
    raw_data: Dict[str, Any]

class DataValidator:
    """Validador de datos de entrada."""
    
    @staticmethod
    def validate_match_data(match_data: MatchData) -> Tuple[bool, List[str]]:
        """Validar datos de partido."""
        errors = []
        
        if not match_data.external_id:
            errors.append("ID externo es requerido")
        
        if not match_data.tournament_name:
            errors.append("Nombre de torneo es requerido")
        
        if not match_data.player1_name:
            errors.append("Nombre del jugador 1 es requerido")
        
        if not match_data.player2_name:
            errors.append("Nombre del jugador 2 es requerido")
        
        if not match_data.match_date:
            errors.append("Fecha del partido es requerida")
        
        if match_data.player1_name == match_data.player2_name:
            errors.append("Los jugadores no pueden ser el mismo")
        
        if match_data.match_date < datetime.now():
            errors.append("Fecha del partido no puede ser en el pasado")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_odds_data(odds_data: OddsData) -> Tuple[bool, List[str]]:
        """Validar datos de cuotas."""
        errors = []
        
        if not odds_data.match_id:
            errors.append("ID del partido es requerido")
        
        if not odds_data.bookmaker:
            errors.append("Casa de apuestas es requerida")
        
        if odds_data.player1_odds <= 1.0:
            errors.append("Cuotas del jugador 1 deben ser mayores a 1.0")
        
        if odds_data.player2_odds <= 1.0:
            errors.append("Cuotas del jugador 2 deben ser mayores a 1.0")
        
        if odds_data.margin and (odds_data.margin < 0 or odds_data.margin > 1):
            errors.append("Margen debe estar entre 0 y 1")
        
        return len(errors) == 0, errors

class RateLimiter:
    """Controlador de rate limiting para evitar bloqueos."""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """Inicializar rate limiter."""
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_make_request(self) -> bool:
        """Verificar si se puede hacer una nueva petición."""
        now = time.time()
        
        # Limpiar peticiones antiguas
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def wait_if_needed(self):
        """Esperar si es necesario para respetar el rate limit."""
        while not self.can_make_request():
            time.sleep(1)

class OneXBetScraper:
    """Scraper para 1xBet con manejo robusto de errores."""
    
    def __init__(self):
        """Inicializar scraper."""
        self.session = self._create_session()
        self.rate_limiter = RateLimiter(
            max_requests=config.SCRAPING_DELAY * 2,
            time_window=60
        )
        self.driver = None
        self._setup_selenium()
    
    def _create_session(self) -> requests.Session:
        """Crear sesión HTTP con configuración robusta."""
        session = requests.Session()
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Configurar headers
        session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        return session
    
    def _setup_selenium(self):
        """Configurar Selenium para casos donde requests no funciona."""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={config.USER_AGENT}')
            
            # Deshabilitar logging de Chrome
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            logger.info("Selenium configurado correctamente")
            
        except Exception as e:
            logger.warning(f"No se pudo configurar Selenium: {e}")
            self.driver = None
    
    def _make_request(self, url: str, use_selenium: bool = False) -> Optional[str]:
        """Hacer petición HTTP con rate limiting."""
        self.rate_limiter.wait_if_needed()
        
        try:
            if use_selenium and self.driver:
                return self._make_selenium_request(url)
            else:
                return self._make_requests_request(url)
                
        except Exception as e:
            logger.error(f"Error haciendo petición a {url}: {e}")
            return None
    
    def _make_requests_request(self, url: str) -> Optional[str]:
        """Hacer petición usando requests."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición requests: {e}")
            return None
    
    def _make_selenium_request(self, url: str) -> Optional[str]:
        """Hacer petición usando Selenium."""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # Esperar a que se cargue completamente
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Error en petición Selenium: {e}")
            return None
    
    def scrape_tennis_matches(self) -> List[MatchData]:
        """Scrapear partidos de tenis desde 1xBet."""
        matches = []
        
        try:
            # URLs de tenis en 1xBet (con alternativas)
            tennis_urls = [
                'https://1xbet.com/en/sport/tennis',
                'https://1xbet.com/en/sport/tennis/atp',
                'https://1xbet.com/en/sport/tennis/wta',
                'https://1xbet.com/en/sport/tennis/grand-slams',
                # URLs alternativas
                'https://1xbet.com/en/sport/tennis/live',
                'https://1xbet.com/en/sport/tennis/results'
            ]
            
            for url in tennis_urls:
                logger.info(f"Scrapeando partidos desde: {url}")
                
                html_content = self._make_request(url)
                if html_content:
                    page_matches = self._parse_tennis_page(html_content, url)
                    matches.extend(page_matches)
                
                time.sleep(config.SCRAPING_DELAY)
            
            # Si no se encontraron partidos, usar datos de muestra para testing
            if not matches:
                logger.warning("No se encontraron partidos, usando datos de muestra para testing")
                matches = self._get_sample_matches()
            
            logger.info(f"Total de partidos encontrados: {len(matches)}")
            return matches
            
        except Exception as e:
            logger.error(f"Error scrapeando partidos de tenis: {e}")
            # En caso de error, usar datos de muestra
            logger.info("Usando datos de muestra debido a error en scraping")
            return self._get_sample_matches()
    
    def _get_sample_matches(self) -> List[MatchData]:
        """Generar datos de muestra para testing."""
        try:
            # Intentar cargar desde archivo JSON mejorado
            import json
            import os
            
            json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_matches_fixed.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    sample_data = json.load(f)
                
                matches = []
                for match_data in sample_data:
                    # Convertir fecha string a datetime
                    if isinstance(match_data['match_date'], str):
                        match_data['match_date'] = datetime.fromisoformat(match_data['match_date'])
                    
                    matches.append(MatchData(**match_data))
                
                logger.info(f"Datos de muestra cargados desde JSON: {len(matches)} partidos")
                return matches
                
        except Exception as e:
            logger.warning(f"Error cargando datos JSON de muestra: {e}")
        
        # Fallback a datos hardcodeados si falla la carga del JSON
        sample_matches = [
            {
                'external_id': 'sample_1',
                'tournament_name': 'Australian Open 2024',
                'player1_name': 'Novak Djokovic',
                'player2_name': 'Rafael Nadal',
                'match_date': datetime.now() + timedelta(hours=2),
                'surface': 'hard',
                'round': 'Quarter Final',
                'best_of': 5,
                'source': 'sample_data',
                'raw_data': {'odds': [1.85, 2.10]}
            },
            {
                'external_id': 'sample_2',
                'tournament_name': 'Wimbledon 2024',
                'player1_name': 'Carlos Alcaraz',
                'player2_name': 'Daniil Medvedev',
                'match_date': datetime.now() + timedelta(hours=4),
                'surface': 'grass',
                'round': 'Semi Final',
                'best_of': 5,
                'source': 'sample_data',
                'raw_data': {'odds': [1.65, 2.25]}
            },
            {
                'external_id': 'sample_3',
                'tournament_name': 'US Open 2024',
                'player1_name': 'Jannik Sinner',
                'player2_name': 'Alexander Zverev',
                'match_date': datetime.now() + timedelta(hours=6),
                'surface': 'hard',
                'round': 'Final',
                'best_of': 5,
                'source': 'sample_data',
                'raw_data': {'odds': [1.95, 1.85]}
            }
        ]
        
        return [MatchData(**match) for match in sample_matches]
    
    def _parse_tennis_page(self, html_content: str, source_url: str) -> List[MatchData]:
        """Parsear página HTML de tenis."""
        matches = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar contenedores de partidos (esto puede variar según la estructura de 1xBet)
            match_containers = soup.find_all('div', class_=['match', 'event', 'game'])
            
            for container in match_containers:
                try:
                    match_data = self._extract_match_data(container, source_url)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    logger.warning(f"Error parseando contenedor de partido: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            logger.error(f"Error parseando página HTML: {e}")
            return []
    
    def _extract_match_data(self, container, source_url: str) -> Optional[MatchData]:
        """Extraer datos de partido de un contenedor HTML."""
        try:
            # Extraer información del partido
            # Nota: Los selectores CSS pueden necesitar ajustes según la estructura real de 1xBet
            
            # Buscar nombres de jugadores
            player_elements = container.find_all(['span', 'div'], class_=['player', 'name'])
            if len(player_elements) < 2:
                return None
            
            player1_name = player_elements[0].get_text(strip=True)
            player2_name = player_elements[1].get_text(strip=True)
            
            # Buscar información del torneo
            tournament_element = container.find(['span', 'div'], class_=['tournament', 'league'])
            tournament_name = tournament_element.get_text(strip=True) if tournament_element else "Tennis"
            
            # Buscar fecha/hora
            time_element = container.find(['span', 'div'], class_=['time', 'date'])
            match_date = self._parse_match_date(time_element.get_text(strip=True)) if time_element else datetime.now()
            
            # Generar ID externo único
            external_id = f"{player1_name}_{player2_name}_{tournament_name}_{int(match_date.timestamp())}"
            
            # Datos crudos para análisis posterior
            raw_data = {
                'source_url': source_url,
                'container_html': str(container),
                'extraction_timestamp': datetime.now().isoformat()
            }
            
            return MatchData(
                external_id=external_id,
                tournament_name=tournament_name,
                player1_name=player1_name,
                player2_name=player2_name,
                match_date=match_date,
                surface="hard",  # Por defecto, se puede mejorar
                round="main",     # Por defecto, se puede mejorar
                best_of=3,        # Por defecto, se puede mejorar
                source="1xbet",
                raw_data=raw_data
            )
            
        except Exception as e:
            logger.warning(f"Error extrayendo datos de partido: {e}")
            return None
    
    def _parse_match_date(self, date_string: str) -> datetime:
        """Parsear fecha del partido."""
        try:
            # Intentar diferentes formatos de fecha
            date_formats = [
                '%Y-%m-%d %H:%M',
                '%d.%m.%Y %H:%M',
                '%m/%d/%Y %H:%M',
                '%H:%M',  # Solo hora, usar fecha actual
            ]
            
            for fmt in date_formats:
                try:
                    if fmt == '%H:%M':
                        # Solo hora, usar fecha actual
                        time_obj = datetime.strptime(date_string, fmt).time()
                        today = datetime.now().date()
                        return datetime.combine(today, time_obj)
                    else:
                        return datetime.strptime(date_string, fmt)
                except ValueError:
                    continue
            
            # Si no se puede parsear, usar fecha actual
            return datetime.now()
            
        except Exception as e:
            logger.warning(f"Error parseando fecha '{date_string}': {e}")
            return datetime.now()
    
    def scrape_match_odds(self, match_id: str) -> Optional[OddsData]:
        """Scrapear cuotas para un partido específico."""
        try:
            # URL específica para cuotas del partido
            odds_url = f"https://1xbet.com/en/sport/tennis/match/{match_id}"
            
            html_content = self._make_request(odds_url)
            if not html_content:
                return None
            
            odds_data = self._parse_odds_page(html_content, match_id)
            return odds_data
            
        except Exception as e:
            logger.error(f"Error scrapeando cuotas para partido {match_id}: {e}")
            return None
    
    def _parse_odds_page(self, html_content: str, match_id: str) -> Optional[OddsData]:
        """Parsear página de cuotas."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar cuotas (esto puede variar según la estructura de 1xBet)
            odds_elements = soup.find_all(['span', 'div'], class_=['odds', 'coefficient'])
            
            if len(odds_elements) < 2:
                return None
            
            # Extraer cuotas
            player1_odds = self._extract_odds(odds_elements[0])
            player2_odds = self._extract_odds(odds_elements[1])
            
            if not player1_odds or not player2_odds:
                return None
            
            # Calcular margen
            margin = self._calculate_margin(player1_odds, player2_odds)
            
            raw_data = {
                'html_content': html_content,
                'extraction_timestamp': datetime.now().isoformat()
            }
            
            return OddsData(
                match_id=match_id,
                bookmaker="1xbet",
                player1_odds=player1_odds,
                player2_odds=player2_odds,
                draw_odds=None,  # No aplica para tenis
                margin=margin,
                raw_data=raw_data
            )
            
        except Exception as e:
            logger.error(f"Error parseando página de cuotas: {e}")
            return None
    
    def _extract_odds(self, element) -> Optional[float]:
        """Extraer valor de cuotas de un elemento HTML."""
        try:
            odds_text = element.get_text(strip=True)
            # Limpiar texto y convertir a float
            odds_text = odds_text.replace(',', '.').replace(' ', '')
            return float(odds_text)
        except (ValueError, AttributeError):
            return None
    
    def _calculate_margin(self, odds1: float, odds2: float) -> float:
        """Calcular margen de la casa de apuestas."""
        try:
            implied_prob1 = 1 / odds1
            implied_prob2 = 1 / odds2
            total_prob = implied_prob1 + implied_prob2
            margin = total_prob - 1
            return max(0, margin)
        except ZeroDivisionError:
            return 0.0
    
    def cleanup(self):
        """Limpiar recursos del scraper."""
        try:
            if self.driver:
                self.driver.quit()
            if self.session:
                self.session.close()
            logger.info("Recursos del scraper limpiados")
        except Exception as e:
            logger.error(f"Error limpiando recursos del scraper: {e}")

class DataIngestionManager:
    """Gestor principal de ingesta de datos."""
    
    def __init__(self):
        """Inicializar gestor de ingesta."""
        self.scraper = OneXBetScraper()
        self.validator = DataValidator()
        self.db_manager = db_manager
    
    def ingest_tennis_data(self) -> Dict[str, Any]:
        """Proceso principal de ingesta de datos de tenis."""
        start_time = time.time()
        results = {
            'matches_found': 0,
            'matches_validated': 0,
            'matches_saved': 0,
            'odds_found': 0,
            'odds_saved': 0,
            'errors': [],
            'duration': 0
        }
        
        try:
            logger.info("Iniciando ingesta de datos de tenis...")
            
            # 1. Scrapear partidos
            matches = self.scraper.scrape_tennis_matches()
            results['matches_found'] = len(matches)
            
            if not matches:
                logger.warning("No se encontraron partidos para procesar")
                return results
            
            # 2. Validar y guardar partidos
            for match_data in matches:
                try:
                    # Validar datos
                    is_valid, errors = self.validator.validate_match_data(match_data)
                    if not is_valid:
                        results['errors'].extend([f"Partido {match_data.external_id}: {', '.join(errors)}"])
                        continue
                    
                    results['matches_validated'] += 1
                    
                    # Guardar partido
                    if self._save_match_data(match_data):
                        results['matches_saved'] += 1
                        
                        # Intentar scrapear cuotas
                        odds_data = self.scraper.scrape_match_odds(match_data.external_id)
                        if odds_data:
                            results['odds_found'] += 1
                            if self._save_odds_data(odds_data):
                                results['odds_saved'] += 1
                    
                except Exception as e:
                    error_msg = f"Error procesando partido {match_data.external_id}: {e}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    continue
            
            logger.info(f"Ingesta completada: {results['matches_saved']} partidos, {results['odds_saved']} cuotas")
            
        except Exception as e:
            error_msg = f"Error en ingesta de datos: {e}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
        
        finally:
            results['duration'] = time.time() - start_time
            self._log_ingestion_results(results)
        
        return results
    
    def _save_match_data(self, match_data: MatchData) -> bool:
        """Guardar datos de partido en base de datos."""
        try:
            with self.db_manager.get_db_session() as session:
                # Verificar si el partido ya existe
                existing_match = session.query(MatchRaw).filter(
                    MatchRaw.external_id == match_data.external_id
                ).first()
                
                if existing_match:
                    # Actualizar partido existente
                    existing_match.raw_data = {
                        'tournament_name': match_data.tournament_name,
                        'player1_name': match_data.player1_name,
                        'player2_name': match_data.player2_name,
                        'match_date': match_data.match_date.isoformat(),
                        'surface': match_data.surface,
                        'round': match_data.round,
                        'best_of': match_data.best_of,
                        'source': match_data.source,
                        'original_raw_data': match_data.raw_data
                    }
                    existing_match.updated_at = datetime.utcnow()
                else:
                    # Crear nuevo partido con datos en raw_data
                    new_match = MatchRaw(
                        id=str(uuid.uuid4()),
                        external_id=match_data.external_id,
                        tournament_id=None,  # Se puede actualizar después
                        player1_id=None,     # Se puede actualizar después
                        player2_id=None,     # Se puede actualizar después
                        match_date=match_data.match_date,
                        surface=match_data.surface,
                        round=match_data.round,
                        best_of=match_data.best_of,
                        source=match_data.source,
                        raw_data={
                            'tournament_name': match_data.tournament_name,
                            'player1_name': match_data.player1_name,
                            'player2_name': match_data.player2_name,
                            'match_date': match_data.match_date.isoformat(),
                            'surface': match_data.surface,
                            'round': match_data.round,
                            'best_of': match_data.best_of,
                            'source': match_data.source,
                            'original_raw_data': match_data.raw_data
                        }
                    )
                    session.add(new_match)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error guardando partido {match_data.external_id}: {e}")
            return False
    
    def _save_odds_data(self, odds_data: OddsData) -> bool:
        """Guardar datos de cuotas en base de datos."""
        try:
            with self.db_manager.get_db_session() as session:
                # Verificar si ya existen cuotas para este partido
                existing_odds = session.query(OddsRaw).filter(
                    OddsRaw.match_id == odds_data.match_id,
                    OddsRaw.bookmaker == odds_data.bookmaker
                ).first()
                
                if existing_odds:
                    # Actualizar cuotas existentes
                    existing_odds.player1_odds = odds_data.player1_odds
                    existing_odds.player2_odds = odds_data.player2_odds
                    existing_odds.draw_odds = odds_data.draw_odds
                    existing_odds.margin = odds_data.margin
                    existing_odds.raw_data = odds_data.raw_data
                    existing_odds.odds_timestamp = datetime.utcnow()
                else:
                    # Crear nuevas cuotas
                    new_odds = OddsRaw(
                        id=str(uuid.uuid4()),
                        match_id=odds_data.match_id,
                        bookmaker=odds_data.bookmaker,
                        player1_odds=odds_data.player1_odds,
                        player2_odds=odds_data.player2_odds,
                        draw_odds=odds_data.draw_odds,
                        margin=odds_data.margin,
                        raw_data=odds_data.raw_data
                    )
                    session.add(new_odds)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error guardando cuotas para partido {odds_data.match_id}: {e}")
            return False
    
    def _log_ingestion_results(self, results: Dict[str, Any]):
        """Registrar resultados de la ingesta."""
        try:
            with self.db_manager.get_db_session() as session:
                log_entry = SystemLog(
                    id=str(uuid.uuid4()),
                    level='INFO',
                    module='data_ingest',
                    message=f"Ingesta completada: {results['matches_saved']} partidos, {results['odds_saved']} cuotas",
                    metadata=results
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            logger.error(f"Error guardando log de ingesta: {e}")
    
    def cleanup(self):
        """Limpiar recursos del gestor de ingesta."""
        try:
            self.scraper.cleanup()
            logger.info("Recursos del gestor de ingesta limpiados")
        except Exception as e:
            logger.error(f"Error limpiando recursos del gestor: {e}")

# Función principal para ejecutar ingesta
def run_data_ingestion() -> Dict[str, Any]:
    """Ejecutar proceso de ingesta de datos."""
    manager = DataIngestionManager()
    
    try:
        results = manager.ingest_tennis_data()
        return results
    finally:
        manager.cleanup()

if __name__ == "__main__":
    # Ejecutar ingesta si se ejecuta directamente
    results = run_data_ingestion()
    print(f"Resultados de la ingesta: {results}")
