"""Initial schema creation

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear extensión para UUIDs
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Tabla de torneos
    op.create_table('tournaments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('surface', sa.String(length=50), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('prize_money', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de jugadores
    op.create_table('players',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('ranking', sa.Integer(), nullable=True),
        sa.Column('ranking_points', sa.Integer(), nullable=True),
        sa.Column('birth_date', sa.DateTime(), nullable=True),
        sa.Column('height_cm', sa.Integer(), nullable=True),
        sa.Column('weight_kg', sa.Numeric(), nullable=True),
        sa.Column('playing_style', sa.String(length=100), nullable=True),
        sa.Column('preferred_surface', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de partidos crudos
    op.create_table('matches_raw',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('tournament_id', sa.String(), nullable=True),
        sa.Column('player1_id', sa.String(), nullable=True),
        sa.Column('player2_id', sa.String(), nullable=True),
        sa.Column('match_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('score', sa.String(length=100), nullable=True),
        sa.Column('winner_id', sa.String(), nullable=True),
        sa.Column('sets_played', sa.Integer(), nullable=True),
        sa.Column('games_played', sa.Integer(), nullable=True),
        sa.Column('surface', sa.String(length=50), nullable=True),
        sa.Column('round', sa.String(length=100), nullable=True),
        sa.Column('best_of', sa.Integer(), nullable=True),
        sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ),
        sa.ForeignKeyConstraint(['player1_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['player2_id'], ['players.id'], ),
        sa.ForeignKeyConstraint(['winner_id'], ['players.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id')
    )
    
    # Tabla de cuotas crudas
    op.create_table('odds_raw',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('match_id', sa.String(), nullable=True),
        sa.Column('bookmaker', sa.String(length=100), nullable=False),
        sa.Column('player1_odds', sa.Numeric(), nullable=True),
        sa.Column('player2_odds', sa.Numeric(), nullable=True),
        sa.Column('draw_odds', sa.Numeric(), nullable=True),
        sa.Column('margin', sa.Numeric(), nullable=True),
        sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('odds_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches_raw.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de partidos procesados
    op.create_table('matches_processed',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('match_raw_id', sa.String(), nullable=True),
        sa.Column('player1_implied_prob', sa.Numeric(), nullable=True),
        sa.Column('player2_implied_prob', sa.Numeric(), nullable=True),
        sa.Column('player1_model_prob', sa.Numeric(), nullable=True),
        sa.Column('player2_model_prob', sa.Numeric(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('features_used', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['match_raw_id'], ['matches_raw.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de señales de apuesta
    op.create_table('betting_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('match_id', sa.String(), nullable=True),
        sa.Column('selection', sa.String(length=255), nullable=False),
        sa.Column('odds', sa.Numeric(), nullable=False),
        sa.Column('implied_probability', sa.Numeric(), nullable=False),
        sa.Column('model_probability', sa.Numeric(), nullable=False),
        sa.Column('expected_value', sa.Numeric(), nullable=False),
        sa.Column('kelly_stake', sa.Numeric(), nullable=False),
        sa.Column('recommended_stake', sa.Numeric(), nullable=False),
        sa.Column('confidence_level', sa.String(length=20), nullable=False),
        sa.Column('confidence_score', sa.Numeric(), nullable=False),
        sa.Column('signal_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('execution_price', sa.Numeric(), nullable=True),
        sa.Column('execution_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches_raw.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de apuestas ejecutadas
    op.create_table('executed_bets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('signal_id', sa.String(), nullable=True),
        sa.Column('stake', sa.Numeric(), nullable=False),
        sa.Column('odds', sa.Numeric(), nullable=False),
        sa.Column('potential_profit', sa.Numeric(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('result', sa.String(length=50), nullable=True),
        sa.Column('profit_loss', sa.Numeric(), nullable=True),
        sa.Column('execution_timestamp', sa.DateTime(), nullable=True),
        sa.Column('settlement_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['signal_id'], ['betting_signals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de resultados de backtesting
    op.create_table('backtest_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_name', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('initial_bankroll', sa.Numeric(), nullable=False),
        sa.Column('final_bankroll', sa.Numeric(), nullable=False),
        sa.Column('total_profit', sa.Numeric(), nullable=False),
        sa.Column('roi', sa.Numeric(), nullable=False),
        sa.Column('total_bets', sa.Integer(), nullable=False),
        sa.Column('winning_bets', sa.Integer(), nullable=False),
        sa.Column('losing_bets', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Numeric(), nullable=False),
        sa.Column('max_drawdown', sa.Numeric(), nullable=False),
        sa.Column('sharpe_ratio', sa.Numeric(), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(), nullable=True),
        sa.Column('results_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de métricas del sistema
    op.create_table('system_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Numeric(), nullable=False),
        sa.Column('metric_unit', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de logs del sistema
    op.create_table('system_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('module', sa.String(length=100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tabla de configuración del sistema
    op.create_table('system_config',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=False),
        sa.Column('config_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )
    
    # Crear índices para mejorar rendimiento
    op.create_index('ix_matches_raw_external_id', 'matches_raw', ['external_id'])
    op.create_index('ix_matches_raw_match_date', 'matches_raw', ['match_date'])
    op.create_index('ix_matches_raw_status', 'matches_raw', ['status'])
    op.create_index('ix_odds_raw_match_id', 'odds_raw', ['match_id'])
    op.create_index('ix_betting_signals_match_id', 'betting_signals', ['match_id'])
    op.create_index('ix_betting_signals_status', 'betting_signals', ['status'])
    op.create_index('ix_executed_bets_signal_id', 'executed_bets', ['signal_id'])
    op.create_index('ix_system_logs_timestamp', 'system_logs', ['timestamp'])
    op.create_index('ix_system_metrics_timestamp', 'system_metrics', ['timestamp'])


def downgrade() -> None:
    # Eliminar índices
    op.drop_index('ix_system_metrics_timestamp', 'system_metrics')
    op.drop_index('ix_system_logs_timestamp', 'system_logs')
    op.drop_index('ix_executed_bets_signal_id', 'executed_bets')
    op.drop_index('ix_betting_signals_status', 'betting_signals')
    op.drop_index('ix_betting_signals_match_id', 'betting_signals')
    op.drop_index('ix_odds_raw_match_id', 'odds_raw')
    op.drop_index('ix_matches_raw_status', 'matches_raw')
    op.drop_index('ix_matches_raw_match_date', 'matches_raw')
    op.drop_index('ix_matches_raw_external_id', 'matches_raw')
    
    # Eliminar tablas en orden inverso (por dependencias)
    op.drop_table('system_config')
    op.drop_table('system_logs')
    op.drop_table('system_metrics')
    op.drop_table('backtest_results')
    op.drop_table('executed_bets')
    op.drop_table('betting_signals')
    op.drop_table('matches_processed')
    op.drop_table('odds_raw')
    op.drop_table('matches_raw')
    op.drop_table('players')
    op.drop_table('tournaments')
