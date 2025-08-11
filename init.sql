-- Sistema de Apuestas de Tenis - Esquema de Base de Datos
-- ========================================================

-- Crear extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla de torneos
CREATE TABLE IF NOT EXISTS tournaments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL, -- grand_slam, atp_1000, atp_500, atp_250, challenger
    surface VARCHAR(50) NOT NULL, -- hard, clay, grass, carpet
    country VARCHAR(100),
    start_date DATE,
    end_date DATE,
    prize_money DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de jugadores
CREATE TABLE IF NOT EXISTS players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    ranking INTEGER,
    ranking_points INTEGER,
    birth_date DATE,
    height_cm INTEGER,
    weight_kg DECIMAL(5,2),
    playing_style VARCHAR(100), -- aggressive, defensive, all-court
    preferred_surface VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de partidos (datos crudos)
CREATE TABLE IF NOT EXISTS matches_raw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE,
    tournament_id UUID REFERENCES tournaments(id),
    player1_id UUID REFERENCES players(id),
    player2_id UUID REFERENCES players(id),
    match_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'scheduled', -- scheduled, live, finished, cancelled
    score VARCHAR(100),
    winner_id UUID REFERENCES players(id),
    sets_played INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    surface VARCHAR(50),
    round VARCHAR(100),
    best_of INTEGER DEFAULT 3, -- 3 o 5 sets
    raw_data JSONB, -- Datos crudos de la fuente
    source VARCHAR(100), -- 1xbet, bet365, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de cuotas (datos crudos)
CREATE TABLE IF NOT EXISTS odds_raw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches_raw(id) ON DELETE CASCADE,
    bookmaker VARCHAR(100) NOT NULL,
    player1_odds DECIMAL(8,2),
    player2_odds DECIMAL(8,2),
    draw_odds DECIMAL(8,2), -- Para sets específicos
    margin DECIMAL(5,4), -- Margen de la casa de apuestas
    raw_data JSONB,
    odds_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de partidos procesados
CREATE TABLE IF NOT EXISTS matches_processed (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_raw_id UUID REFERENCES matches_raw(id) ON DELETE CASCADE,
    player1_implied_prob DECIMAL(5,4),
    player2_implied_prob DECIMAL(5,4),
    player1_model_prob DECIMAL(5,4),
    player2_model_prob DECIMAL(5,4),
    confidence_score DECIMAL(5,4),
    model_version VARCHAR(50),
    features_used JSONB,
    processing_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de señales de apuesta
CREATE TABLE IF NOT EXISTS betting_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches_raw(id) ON DELETE CASCADE,
    selection VARCHAR(255) NOT NULL, -- Jugador seleccionado
    odds DECIMAL(8,2) NOT NULL,
    implied_probability DECIMAL(5,4) NOT NULL,
    model_probability DECIMAL(5,4) NOT NULL,
    expected_value DECIMAL(6,4) NOT NULL,
    kelly_stake DECIMAL(6,4) NOT NULL,
    recommended_stake DECIMAL(10,2) NOT NULL,
    confidence_level VARCHAR(20) NOT NULL, -- low, medium, high
    confidence_score DECIMAL(5,4) NOT NULL,
    signal_type VARCHAR(50) NOT NULL, -- value_bet, arbitrage, etc.
    status VARCHAR(50) DEFAULT 'active', -- active, executed, expired, cancelled
    execution_price DECIMAL(8,2),
    execution_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de apuestas ejecutadas
CREATE TABLE IF NOT EXISTS executed_bets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID REFERENCES betting_signals(id),
    stake DECIMAL(10,2) NOT NULL,
    odds DECIMAL(8,2) NOT NULL,
    potential_profit DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, won, lost, void
    result VARCHAR(50), -- win, loss, void
    profit_loss DECIMAL(10,2),
    execution_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settlement_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de resultados de backtesting
CREATE TABLE IF NOT EXISTS backtest_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_bankroll DECIMAL(12,2) NOT NULL,
    final_bankroll DECIMAL(12,2) NOT NULL,
    total_profit DECIMAL(12,2) NOT NULL,
    roi DECIMAL(6,4) NOT NULL,
    total_bets INTEGER NOT NULL,
    winning_bets INTEGER NOT NULL,
    losing_bets INTEGER NOT NULL,
    win_rate DECIMAL(5,4) NOT NULL,
    max_drawdown DECIMAL(6,4) NOT NULL,
    sharpe_ratio DECIMAL(6,4),
    calmar_ratio DECIMAL(6,4),
    results_data JSONB, -- Datos detallados del backtest
    parameters JSONB, -- Parámetros utilizados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de métricas del sistema
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4) NOT NULL,
    metric_unit VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Tabla de logs del sistema
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL, -- INFO, WARNING, ERROR, DEBUG
    module VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Tabla de configuración del sistema
CREATE TABLE IF NOT EXISTS system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(50) NOT NULL, -- string, integer, float, boolean, json
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_matches_raw_tournament ON matches_raw(tournament_id);
CREATE INDEX IF NOT EXISTS idx_matches_raw_date ON matches_raw(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_raw_status ON matches_raw(status);
CREATE INDEX IF NOT EXISTS idx_odds_raw_match ON odds_raw(match_id);
CREATE INDEX IF NOT EXISTS idx_odds_raw_timestamp ON odds_raw(odds_timestamp);
CREATE INDEX IF NOT EXISTS idx_betting_signals_match ON betting_signals(match_id);
CREATE INDEX IF NOT EXISTS idx_betting_signals_status ON betting_signals(status);
CREATE INDEX IF NOT EXISTS idx_executed_bets_signal ON executed_bets(signal_id);
CREATE INDEX IF NOT EXISTS idx_executed_bets_status ON executed_bets(status);
CREATE INDEX IF NOT EXISTS idx_backtest_results_strategy ON backtest_results(strategy_name);
CREATE INDEX IF NOT EXISTS idx_backtest_results_dates ON backtest_results(start_date, end_date);

-- Función para actualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para actualizar timestamps
CREATE TRIGGER update_tournaments_updated_at BEFORE UPDATE ON tournaments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_raw_updated_at BEFORE UPDATE ON matches_raw
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_processed_updated_at BEFORE UPDATE ON matches_processed
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_betting_signals_updated_at BEFORE UPDATE ON betting_signals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_executed_bets_updated_at BEFORE UPDATE ON executed_bets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insertar configuración inicial del sistema
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('BANKROLL', '10000', 'float', 'Capital inicial del sistema'),
('KELLY_FRACTION', '0.5', 'float', 'Fracción Kelly para cálculo de stakes'),
('MAX_STAKE_PERCENT', '5', 'float', 'Porcentaje máximo del bankroll por apuesta'),
('MIN_EV_THRESHOLD', '0.05', 'float', 'Umbral mínimo de valor esperado'),
('SCRAPING_DELAY', '2', 'integer', 'Delay entre requests de scraping'),
('LOG_LEVEL', 'INFO', 'string', 'Nivel de logging del sistema'),
('MODEL_UPDATE_FREQUENCY', '3600', 'integer', 'Frecuencia de actualización de modelos (segundos)'),
('HISTORICAL_DATA_DAYS', '365', 'integer', 'Días de datos históricos a mantener')
ON CONFLICT (config_key) DO NOTHING;

-- Crear vistas útiles
CREATE OR REPLACE VIEW active_signals AS
SELECT 
    bs.*,
    mr.player1_id,
    mr.player2_id,
    mr.match_date,
    mr.status as match_status,
    t.name as tournament_name,
    t.surface as tournament_surface
FROM betting_signals bs
JOIN matches_raw mr ON bs.match_id = mr.id
JOIN tournaments t ON mr.tournament_id = t.id
WHERE bs.status = 'active' AND mr.status IN ('scheduled', 'live');

CREATE OR REPLACE VIEW recent_matches AS
SELECT 
    mr.*,
    p1.name as player1_name,
    p2.name as player2_name,
    t.name as tournament_name,
    t.surface as tournament_surface,
    t.category as tournament_category
FROM matches_raw mr
JOIN players p1 ON mr.player1_id = p1.id
JOIN players p2 ON mr.player2_id = p2.id
JOIN tournaments t ON mr.tournament_id = t.id
ORDER BY mr.match_date DESC;

-- Función para limpiar datos antiguos
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Limpiar logs antiguos (más de 30 días)
    DELETE FROM system_logs WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Limpiar métricas antiguas (más de 90 días)
    DELETE FROM system_metrics WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    -- Limpiar partidos crudos antiguos (más de 1 año)
    DELETE FROM matches_raw WHERE match_date < CURRENT_TIMESTAMP - INTERVAL '1 year';
    
    RAISE NOTICE 'Limpieza de datos antiguos completada';
END;
$$ LANGUAGE plpgsql;

-- Comentarios en las tablas
COMMENT ON TABLE tournaments IS 'Información de torneos de tenis';
COMMENT ON TABLE players IS 'Información de jugadores de tenis';
COMMENT ON TABLE matches_raw IS 'Datos crudos de partidos obtenidos de fuentes externas';
COMMENT ON TABLE odds_raw IS 'Cuotas en tiempo real de diferentes casas de apuestas';
COMMENT ON TABLE matches_processed IS 'Partidos procesados con probabilidades del modelo';
COMMENT ON TABLE betting_signals IS 'Señales de apuesta generadas por el sistema';
COMMENT ON TABLE executed_bets IS 'Apuestas ejecutadas por el sistema';
COMMENT ON TABLE backtest_results IS 'Resultados de backtesting de estrategias';
COMMENT ON TABLE system_metrics IS 'Métricas de rendimiento del sistema';
COMMENT ON TABLE system_logs IS 'Logs del sistema para debugging y monitoreo';
COMMENT ON TABLE system_config IS 'Configuración configurable del sistema';
