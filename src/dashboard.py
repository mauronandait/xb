"""
Dashboard principal del sistema de apuestas de tenis.
Muestra partidos disponibles, cuotas y probabilidades en tiempo real.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine, text
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar página de Streamlit
st.set_page_config(
    page_title="Sistema de Apuestas de Tenis",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded"
)

class TennisDashboard:
    """Clase principal del dashboard de tenis."""
    
    def __init__(self):
        """Inicializar el dashboard."""
        self.db_engine = None
        self.setup_database()
    
    def setup_database(self):
        """Configurar conexión a la base de datos."""
        try:
            self.db_engine = create_engine(config.get_database_url())
            logger.info("Conexión a base de datos establecida")
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            st.error(f"Error de conexión a la base de datos: {e}")
    
    def get_tennis_matches(self):
        """Obtener partidos de tenis desde la base de datos o datos de ejemplo."""
        if not self.db_engine:
            # Usar datos de ejemplo si no hay base de datos
            return self.get_sample_data()
        
        try:
            query = """
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
            WHERE mr.sport_type = 'tennis'
            ORDER BY mr.match_time DESC
            """
            
            df = pd.read_sql(query, self.db_engine)
            
            # Calcular probabilidades implícitas
            if not df.empty and 'player1_odds' in df.columns and 'player2_odds' in df.columns:
                df['player1_prob'] = (1 / df['player1_odds']).fillna(0)
                df['player2_prob'] = (1 / df['player2_odds']).fillna(0)
                df['total_prob'] = df['player1_prob'] + df['player2_prob']
                df['margin'] = df['total_prob'] - 1
                
                # Ajustar probabilidades por margen
                df['player1_prob_adj'] = df['player1_prob'] / df['total_prob']
                df['player2_prob_adj'] = df['player2_prob'] / df['total_prob']
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo partidos: {e}")
            st.warning("Usando datos de ejemplo (base de datos no disponible)")
            return self.get_sample_data()
    
    def get_sample_data(self):
        """Obtener datos de ejemplo para demostración."""
        import numpy as np
        from datetime import datetime, timedelta
        
        # Datos de ejemplo
        tournaments = ['Australian Open', 'Wimbledon', 'US Open', 'French Open', 'Miami Open']
        players = ['Novak Djokovic', 'Rafael Nadal', 'Roger Federer', 'Daniil Medvedev', 
                  'Carlos Alcaraz', 'Jannik Sinner', 'Stefanos Tsitsipas', 'Alexander Zverev']
        
        # Generar partidos de ejemplo
        matches = []
        base_time = datetime.now() + timedelta(hours=1)
        
        for i in range(10):
            player1 = np.random.choice(players)
            player2 = np.random.choice([p for p in players if p != player1])
            tournament = np.random.choice(tournaments)
            
            # Generar odds realistas
            player1_odds = round(np.random.uniform(1.2, 3.0), 2)
            player2_odds = round(np.random.uniform(1.2, 3.0), 2)
            
            matches.append({
                'match_id': f'match_{i}_{int(base_time.timestamp())}',
                'tournament': tournament,
                'player1': player1,
                'player2': player2,
                'match_time': base_time + timedelta(hours=i),
                'player1_odds': player1_odds,
                'player2_odds': player2_odds,
                'created_at': datetime.now()
            })
        
        df = pd.DataFrame(matches)
        
        # Calcular probabilidades implícitas
        df['player1_prob'] = (1 / df['player1_odds']).fillna(0)
        df['player2_prob'] = (1 / df['player2_odds']).fillna(0)
        df['total_prob'] = df['player1_prob'] + df['player2_prob']
        df['margin'] = df['total_prob'] - 1
        
        # Ajustar probabilidades por margen
        df['player1_prob_adj'] = df['player1_prob'] / df['total_prob']
        df['player2_prob_adj'] = df['player2_prob'] / df['total_prob']
        
        return df
    
    def calculate_value_bets(self, df):
        """Calcular value bets basados en probabilidades implícitas."""
        if df.empty:
            return df
        
        # Simular probabilidades del modelo (en producción esto vendría de ML)
        import numpy as np
        np.random.seed(42)  # Para reproducibilidad
        
        df['model_prob1'] = np.random.beta(2, 2)  # Simulación
        df['model_prob2'] = 1 - df['model_prob1']
        
        # Calcular EV para cada jugador
        df['ev1'] = (df['model_prob1'] * df['player1_odds']) - 1
        df['ev2'] = (df['model_prob2'] * df['player2_odds']) - 1
        
        # Identificar value bets (EV > 0.05)
        df['value_bet1'] = df['ev1'] > 0.05
        df['value_bet2'] = df['ev2'] > 0.05
        
        # Calcular stakes Kelly
        df['kelly_stake1'] = np.where(
            df['value_bet1'],
            (df['model_prob1'] * df['player1_odds'] - 1) / (df['player1_odds'] - 1) * 0.5,  # Kelly fraccionado
            0
        )
        
        df['kelly_stake2'] = np.where(
            df['value_bet2'],
            (df['model_prob2'] * df['player2_odds'] - 1) / (df['player2_odds'] - 1) * 0.5,
            0
        )
        
        return df
    
    def render_header(self):
        """Renderizar encabezado del dashboard."""
        st.title("🎾 Sistema de Apuestas Deportivas para Tenis")
        st.markdown("---")
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Partidos Disponibles", "0", "0")
        
        with col2:
            st.metric("Value Bets", "0", "0")
        
        with col3:
            st.metric("ROI Promedio", "0%", "0%")
        
        with col4:
            st.metric("Última Actualización", datetime.now().strftime("%H:%M"))
    
    def render_filters(self):
        """Renderizar filtros del dashboard."""
        st.subheader("🔍 Filtros")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tournament_filter = st.selectbox(
                "Torneo",
                ["Todos"] + ["Australian Open", "French Open", "Wimbledon", "US Open", "ATP Finals"]
            )
        
        with col2:
            ev_filter = st.slider(
                "EV Mínimo",
                min_value=0.0,
                max_value=0.20,
                value=0.05,
                step=0.01,
                format="%.2f"
            )
        
        with col3:
            date_filter = st.date_input(
                "Fecha",
                value=datetime.now().date()
            )
        
        return {
            'tournament': tournament_filter,
            'ev_min': ev_filter,
            'date': date_filter
        }
    
    def render_matches_table(self, df, filters):
        """Renderizar tabla de partidos."""
        st.subheader("📊 Partidos de Tenis Disponibles")
        
        if df.empty:
            st.info("No hay partidos disponibles en este momento.")
            return
        
        # Aplicar filtros
        filtered_df = df.copy()
        
        if filters['tournament'] != "Todos":
            filtered_df = filtered_df[filtered_df['tournament'] == filters['tournament']]
        
        if filters['ev_min'] > 0:
            filtered_df = filtered_df[
                (filtered_df['ev1'] >= filters['ev_min']) | 
                (filtered_df['ev2'] >= filters['ev_min'])
            ]
        
        if filtered_df.empty:
            st.warning("No hay partidos que coincidan con los filtros seleccionados.")
            return
        
        # Mostrar tabla
        st.dataframe(
            filtered_df[[
                'tournament', 'player1', 'player2', 'match_time',
                'player1_odds', 'player2_odds', 'player1_prob_adj', 'player2_prob_adj',
                'ev1', 'ev2', 'value_bet1', 'value_bet2'
            ]].round(4),
            use_container_width=True
        )
    
    def render_value_bets(self, df):
        """Renderizar sección de value bets."""
        st.subheader("💰 Value Bets Detectados")
        
        if df.empty:
            st.info("No se detectaron value bets en este momento.")
            return
        
        # Filtrar solo value bets
        value_bets = df[(df['value_bet1'] == True) | (df['value_bet2'] == True)].copy()
        
        if value_bets.empty:
            st.info("No hay value bets disponibles en este momento.")
            return
        
        # Crear tabla de value bets
        value_bets_list = []
        
        for _, row in value_bets.iterrows():
            if row['value_bet1']:
                value_bets_list.append({
                    'Partido': f"{row['player1']} vs {row['player2']}",
                    'Torneo': row['tournament'],
                    'Selección': row['player1'],
                    'Cuota': f"{row['player1_odds']:.2f}",
                    'Prob. Modelo': f"{row['model_prob1']:.1%}",
                    'Prob. Implícita': f"{row['player1_prob_adj']:.1%}",
                    'EV': f"{row['ev1']:.1%}",
                    'Stake Kelly': f"{row['kelly_stake1']:.1%}"
                })
            
            if row['value_bet2']:
                value_bets_list.append({
                    'Partido': f"{row['player1']} vs {row['player2']}",
                    'Torneo': row['tournament'],
                    'Selección': row['player2'],
                    'Cuota': f"{row['player2_odds']:.2f}",
                    'Prob. Modelo': f"{row['model_prob2']:.1%}",
                    'Prob. Implícita': f"{row['player2_prob_adj']:.1%}",
                    'EV': f"{row['ev2']:.1%}",
                    'Stake Kelly': f"{row['kelly_stake2']:.1%}"
                })
        
        if value_bets_list:
            value_bets_df = pd.DataFrame(value_bets_list)
            st.dataframe(value_bets_df, use_container_width=True)
    
    def render_charts(self, df):
        """Renderizar gráficos y visualizaciones."""
        st.subheader("📈 Análisis Visual")
        
        if df.empty:
            st.info("No hay datos suficientes para generar gráficos.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de distribución de EV
            if 'ev1' in df.columns:
                fig_ev = px.histogram(
                    df,
                    x=['ev1', 'ev2'],
                    title="Distribución de Expected Value (EV)",
                    labels={'value': 'EV', 'variable': 'Jugador'},
                    nbins=20
                )
                st.plotly_chart(fig_ev, use_container_width=True)
        
        with col2:
            # Gráfico de margen por torneo
            if 'margin' in df.columns:
                fig_margin = px.box(
                    df,
                    x='tournament',
                    y='margin',
                    title="Margen por Torneo",
                    labels={'margin': 'Margen', 'tournament': 'Torneo'}
                )
                st.plotly_chart(fig_margin, use_container_width=True)
    
    def render_sidebar(self):
        """Renderizar barra lateral."""
        st.sidebar.title("⚙️ Configuración")
        
        # Configuración de actualización
        st.sidebar.subheader("Actualización")
        auto_refresh = st.sidebar.checkbox("Actualización automática", value=True)
        refresh_interval = st.sidebar.slider("Intervalo (minutos)", 1, 60, 15)
        
        # Configuración de alertas
        st.sidebar.subheader("Alertas")
        email_alerts = st.sidebar.checkbox("Alertas por email", value=False)
        telegram_alerts = st.sidebar.checkbox("Alertas por Telegram", value=False)
        
        # Configuración de apuestas
        st.sidebar.subheader("Apuestas")
        bankroll = st.sidebar.number_input("Bankroll ($)", min_value=1000, value=10000, step=1000)
        max_stake = st.sidebar.slider("Stake máximo (%)", 1, 10, 5)
        
        # Botón de actualización manual
        if st.sidebar.button("🔄 Actualizar Datos"):
            st.rerun()
        
        return {
            'auto_refresh': auto_refresh,
            'refresh_interval': refresh_interval,
            'email_alerts': email_alerts,
            'telegram_alerts': telegram_alerts,
            'bankroll': bankroll,
            'max_stake': max_stake
        }
    
    def run(self):
        """Ejecutar el dashboard principal."""
        try:
            # Renderizar encabezado
            self.render_header()
            
            # Renderizar barra lateral
            sidebar_config = self.render_sidebar()
            
            # Renderizar filtros
            filters = self.render_filters()
            
            # Obtener datos
            df = self.get_tennis_matches()
            
            if not df.empty:
                # Calcular value bets
                df = self.calculate_value_bets(df)
                
                # Renderizar secciones
                self.render_matches_table(df, filters)
                self.render_value_bets(df)
                self.render_charts(df)
                
                # Actualizar métricas
                self.update_metrics(df)
            
            # Footer
            st.markdown("---")
            st.markdown(
                "**Sistema de Apuestas Deportivas para Tenis** | "
                "Desarrollado para fines educativos y de investigación"
            )
            
        except Exception as e:
            logger.error(f"Error en dashboard: {e}")
            st.error(f"Error en el dashboard: {e}")
    
    def update_metrics(self, df):
        """Actualizar métricas del dashboard."""
        if df.empty:
            return
        
        # Contar partidos
        total_matches = len(df)
        
        # Contar value bets
        total_value_bets = 0
        if 'value_bet1' in df.columns and 'value_bet2' in df.columns:
            total_value_bets = df['value_bet1'].sum() + df['value_bets2'].sum()
        
        # Calcular ROI promedio (simulado)
        avg_roi = 0.0  # En producción esto vendría de resultados reales
        
        # Actualizar métricas en el header
        st.session_state.total_matches = total_matches
        st.session_state.total_value_bets = total_value_bets
        st.session_state.avg_roi = avg_roi

def main():
    """Función principal del dashboard."""
    try:
        dashboard = TennisDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"Error fatal en el dashboard: {e}")
        logger.error(f"Error fatal en el dashboard: {e}")

if __name__ == "__main__":
    main()
