-- Script de inicialización para la base de datos de apuestas de tenis
-- Este archivo se ejecuta automáticamente al crear el contenedor PostgreSQL

-- Crear base de datos si no existe
SELECT 'CREATE DATABASE tennis_betting'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tennis_betting')\gexec

-- Conectar a la base de datos
\c tennis_betting;

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla para datos crudos de partidos
CREATE TABLE IF NOT EXISTS matches_raw (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(100) UNIQUE NOT NULL,
    tournament VARCHAR(255),
    player1 VARCHAR(255),
    player2 VARCHAR(255),
    match_time TIMESTAMP,
    sport_type VARCHAR(50) DEFAULT 'tennis',
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para cuotas en tiempo real
CREATE TABLE IF NOT EXISTS odds_raw (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(100) REFERENCES matches_raw(match_id) ON DELETE CASCADE,
    bookmaker VARCHAR(100) DEFAULT '1xbet',
    market_type VARCHAR(100) DEFAULT 'match_winner',
    selection VARCHAR(255),
    odds DECIMAL(10,3),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para partidos procesados
CREATE TABLE IF NOT EXISTS matches_processed (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(100) REFERENCES matches_raw(match_id) ON DELETE CASCADE,
    player1 VARCHAR(255),
    player2 VARCHAR(255),
    tournament VARCHAR(255),
    match_time TIMESTAMP,
    player1_odds DECIMAL(10,3),
    player2_odds DECIMAL(10,3),
    player1_prob DECIMAL(10,6),
    player2_prob DECIMAL(10,6),
    margin DECIMAL(10,6),
    total_prob DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para señales de apuesta
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(100) REFERENCES matches_raw(match_id) ON DELETE CASCADE,
    selection VARCHAR(255),
    odds DECIMAL(10,3),
    model_prob DECIMAL(10,6),
    implied_prob DECIMAL(10,6),
    ev DECIMAL(10,6),
    kelly_stake DECIMAL(10,6),
    recommended_stake DECIMAL(10,2),
    confidence DECIMAL(10,6),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para resultados de partidos
CREATE TABLE IF NOT EXISTS match_results (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(100) REFERENCES matches_raw(match_id) ON DELETE CASCADE,
    winner VARCHAR(255),
    score VARCHAR(100),
    sets_player1 INTEGER,
    sets_player2 INTEGER,
    games_player1 INTEGER,
    games_player2 INTEGER,
    result_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para datos históricos de jugadores
CREATE TABLE IF NOT EXISTS player_stats (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255),
    surface VARCHAR(50),
    tournament_level VARCHAR(50),
    matches_played INTEGER,
    matches_won INTEGER,
    win_percentage DECIMAL(5,2),
    avg_odds DECIMAL(10,3),
    elo_rating DECIMAL(10,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para modelos entrenados
CREATE TABLE IF NOT EXISTS ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255),
    model_type VARCHAR(100),
    version VARCHAR(50),
    accuracy DECIMAL(10,6),
    precision DECIMAL(10,6),
    recall DECIMAL(10,6),
    f1_score DECIMAL(10,6),
    model_path TEXT,
    training_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para logs del sistema
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    log_level VARCHAR(20),
    module VARCHAR(100),
    message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    additional_data JSONB
);

-- Crear índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_matches_raw_tournament ON matches_raw(tournament);
CREATE INDEX IF NOT EXISTS idx_matches_raw_match_time ON matches_raw(match_time);
CREATE INDEX IF NOT EXISTS idx_odds_raw_match_id ON odds_raw(match_id);
CREATE INDEX IF NOT EXISTS idx_odds_raw_timestamp ON odds_raw(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_match_id ON signals(match_id);
CREATE INDEX IF NOT EXISTS idx_signals_ev ON signals(ev);
CREATE INDEX IF NOT EXISTS idx_player_stats_player_name ON player_stats(player_name);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);

-- Crear función para actualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Crear triggers para actualizar timestamps
CREATE TRIGGER update_matches_raw_updated_at 
    BEFORE UPDATE ON matches_raw 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_processed_updated_at 
    BEFORE UPDATE ON matches_processed 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_signals_updated_at 
    BEFORE UPDATE ON signals 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insertar datos de ejemplo para testing
INSERT INTO matches_raw (match_id, tournament, player1, player2, match_time, sport_type) VALUES
('Djokovic_Nadal_Australian_Open_20241201', 'Australian Open', 'Novak Djokovic', 'Rafael Nadal', '2024-12-01 15:00:00', 'tennis'),
('Medvedev_Zverev_US_Open_20241201', 'US Open', 'Daniil Medvedev', 'Alexander Zverev', '2024-12-01 16:30:00', 'tennis'),
('Alcaraz_Sinner_Wimbledon_20241201', 'Wimbledon', 'Carlos Alcaraz', 'Jannik Sinner', '2024-12-01 18:00:00', 'tennis')
ON CONFLICT (match_id) DO NOTHING;

-- Insertar cuotas de ejemplo
INSERT INTO odds_raw (match_id, bookmaker, market_type, selection, odds) VALUES
('Djokovic_Nadal_Australian_Open_20241201', '1xbet', 'match_winner', 'Novak Djokovic', 1.85),
('Djokovic_Nadal_Australian_Open_20241201', '1xbet', 'match_winner', 'Rafael Nadal', 2.10),
('Medvedev_Zverev_US_Open_20241201', '1xbet', 'match_winner', 'Daniil Medvedev', 1.65),
('Medvedev_Zverev_US_Open_20241201', '1xbet', 'match_winner', 'Alexander Zverev', 2.35),
('Alcaraz_Sinner_Wimbledon_20241201', '1xbet', 'match_winner', 'Carlos Alcaraz', 1.90),
('Alcaraz_Sinner_Wimbledon_20241201', '1xbet', 'match_winner', 'Jannik Sinner', 1.95)
ON CONFLICT DO NOTHING;

-- Crear vista para partidos con cuotas
CREATE OR REPLACE VIEW matches_with_odds AS
SELECT 
    mr.match_id,
    mr.tournament,
    mr.player1,
    mr.player2,
    mr.match_time,
    p1.odds as player1_odds,
    p2.odds as player2_odds,
    mr.created_at
FROM matches_raw mr
LEFT JOIN odds_raw p1 ON mr.match_id = p1.match_id AND p1.selection = mr.player1
LEFT JOIN odds_raw p2 ON mr.match_id = p2.match_id AND p2.selection = mr.player2
WHERE mr.sport_type = 'tennis';

-- Crear usuario para la aplicación (opcional)
-- CREATE USER tennis_app WITH PASSWORD 'tennis_app_password';
-- GRANT ALL PRIVILEGES ON DATABASE tennis_betting TO tennis_app;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tennis_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tennis_app;

-- Mensaje de confirmación
SELECT 'Base de datos de apuestas de tenis inicializada correctamente' as status;
