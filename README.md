# Sistema de Apuestas Deportivas para Tenis 🎾

Un sistema completo y modular para automatización de apuestas deportivas que incluye ingesta de datos en tiempo real, modelos de machine learning, detección de value bets y dashboard interactivo.

## 🚀 Características Principales

- **Ingesta de Datos en Tiempo Real**: Obtención automática de cuotas y datos de tenis desde 1xBet
- **Base de Datos Robusta**: PostgreSQL con esquema optimizado para datos deportivos
- **Modelos de ML**: XGBoost, LightGBM y modelos estadísticos para estimación de probabilidades
- **Detección de Value Bets**: Cálculo automático de EV y stakes con Kelly fraccionado
- **Dashboard Interactivo**: Interface web con Streamlit para monitoreo en tiempo real
- **Backtesting**: Simulación de estrategias en datos históricos
- **Sistema de Alertas**: Notificaciones por email y Telegram
- **Automatización**: Scripts programados y preparación para ejecución automática

## 🏗️ Arquitectura del Sistema

```
project_root/
│
├── src/                    # Código fuente principal
│   ├── config.py          # Configuración centralizada
│   ├── data_ingest.py     # Ingesta de datos desde 1xBet
│   ├── data_clean.py      # Limpieza y procesamiento de datos
│   ├── model_train.py     # Entrenamiento de modelos ML
│   ├── betting_signals.py # Detección de señales de apuesta
│   ├── dashboard.py       # Dashboard Streamlit
│   ├── backtest.py        # Sistema de backtesting
│   └── alerts.py          # Sistema de alertas
│
├── notebooks/              # Jupyter notebooks para análisis
├── config/                 # Archivos de configuración
├── tests/                  # Pruebas unitarias
└── logs/                   # Archivos de log
```

## 📋 Requisitos del Sistema

- **Python**: 3.11 o superior
- **PostgreSQL**: 13 o superior
- **Docker**: 20.10 o superior (opcional)
- **Memoria**: Mínimo 4GB RAM
- **Almacenamiento**: Mínimo 10GB libre

## 🛠️ Instalación

### Opción 1: Instalación Local

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd tennis-betting-system
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate     # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar base de datos PostgreSQL**
   ```bash
   # Crear base de datos
   createdb tennis_betting
   
   # O usar psql
   psql -U postgres
   CREATE DATABASE tennis_betting;
   ```

5. **Configurar variables de entorno**
   ```bash
   cp config/env_example.txt config/.env
   # Editar config/.env con tus credenciales
   ```

### Opción 2: Instalación con Docker

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd tennis-betting-system
   ```

2. **Configurar variables de entorno**
   ```bash
   cp config/env_example.txt config/.env
   # Editar config/.env
   ```

3. **Ejecutar con Docker Compose**
   ```bash
   docker-compose up -d
   ```

## ⚙️ Configuración

### Variables de Entorno Principales

```bash
# Base de Datos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tennis_betting
DB_USER=postgres
DB_PASSWORD=your_password

# 1xBet
ONEXBET_API_KEY=your_api_key_here
SCRAPING_ENABLED=true

# Configuración de Apuestas
BANKROLL=10000
KELLY_FRACTION=0.5
MAX_STAKE_PERCENT=5
MIN_EV_THRESHOLD=0.05
```

### Configuración de Base de Datos

El sistema crea automáticamente las siguientes tablas:

- **matches_raw**: Datos crudos de partidos
- **odds_raw**: Cuotas en tiempo real
- **matches_processed**: Partidos procesados con probabilidades
- **signals**: Señales de apuesta generadas

## 🚀 Uso del Sistema

### 1. Ingesta de Datos

```python
from src.data_ingest import TennisDataIngestor

# Crear instancia del ingestor
ingestor = TennisDataIngestor()

# Ejecutar ingesta de datos
matches = ingestor.run_data_ingestion()

# Ver resultados
for match in matches:
    print(f"{match['player1']} vs {match['player2']}")
    print(f"Cuotas: {match['player1_odds']:.2f} | {match['player2_odds']:.2f}")
    print(f"Probabilidades: {match['player1_prob']:.1%} | {match['player2_prob']:.1%}")
```

### 2. Dashboard Web

```bash
# Ejecutar dashboard
streamlit run src/dashboard.py

# O con Python
python -m streamlit run src/dashboard.py
```

### 3. Ejecución Programada

```python
import schedule
import time
from src.data_ingest import TennisDataIngestor

ingestor = TennisDataIngestor()

# Programar ingesta cada 15 minutos
schedule.every(15).minutes.do(ingestor.run_data_ingestion)

# Ejecutar en bucle
while True:
    schedule.run_pending()
    time.sleep(60)
```

## 📊 Estructura de Datos

### Partidos de Tenis

```json
{
  "match_id": "Djokovic_Nadal_Australian_Open_20241201",
  "tournament": "Australian Open",
  "player1": "Novak Djokovic",
  "player2": "Rafael Nadal",
  "match_time": "2024-12-01T15:00:00",
  "player1_odds": 1.85,
  "player2_odds": 2.10,
  "player1_prob": 0.540,
  "player2_prob": 0.460,
  "margin": 0.050
}
```

### Señales de Apuesta

```json
{
  "match_id": "Djokovic_Nadal_Australian_Open_20241201",
  "selection": "Novak Djokovic",
  "odds": 1.85,
  "model_prob": 0.580,
  "implied_prob": 0.540,
  "ev": 0.073,
  "kelly_stake": 0.025,
  "recommended_stake": 250
}
```

## 🔧 Desarrollo

### Estructura de Pruebas

```bash
# Ejecutar todas las pruebas
pytest

# Con cobertura
pytest --cov=src

# Pruebas específicas
pytest tests/test_data_ingest.py
```

### Formateo de Código

```bash
# Formatear con Black
black src/

# Verificar con Flake8
flake8 src/

# Verificación de tipos con MyPy
mypy src/
```

## 📈 Modelos de Machine Learning

### Características Utilizadas

- **Estadísticas del Jugador**: Ranking, historial H2H, estadísticas de superficie
- **Estadísticas del Torneo**: Nivel, superficie, condiciones climáticas
- **Estadísticas de Forma**: Resultados recientes, sets/juegos ganados
- **Factores Externos**: Lesiones, descanso, viajes

### Algoritmos Implementados

1. **Modelo Estadístico**: ELO adaptado a tenis
2. **XGBoost**: Para features tabulares
3. **LightGBM**: Alternativa rápida y eficiente
4. **Ensemble**: Combinación de múltiples modelos
5. **Calibración**: Platt scaling para ajuste de probabilidades

## 🎯 Estrategias de Apuesta

### Criterios de Value Bet

- **EV > 0.05**: Valor esperado mínimo del 5%
- **Kelly Fraccionado**: 50% del stake Kelly completo
- **Stake Máximo**: 5% del bankroll
- **Filtros Adicionales**: Confianza del modelo > 70%

### Cálculo de Stakes

```python
# Fórmula Kelly
kelly_stake = (model_prob * odds - 1) / (odds - 1)

# Kelly fraccionado
fractional_stake = kelly_stake * kelly_fraction

# Stake final
final_stake = min(fractional_stake, max_stake_percent) * bankroll
```

## 🔔 Sistema de Alertas

### Tipos de Alertas

1. **Value Bets Detectados**: Nuevas oportunidades de apuesta
2. **Cambios de Cuotas**: Movimientos significativos en el mercado
3. **Resultados de Partidos**: Actualizaciones de resultados
4. **Errores del Sistema**: Problemas técnicos que requieren atención

### Canales de Notificación

- **Email**: Notificaciones detalladas
- **Telegram**: Alertas rápidas y móviles
- **Dashboard**: Visualización en tiempo real

## 📊 Backtesting

### Métricas Evaluadas

- **ROI**: Retorno sobre inversión
- **Profit Acumulado**: Ganancias/pérdidas totales
- **Drawdown Máximo**: Pérdida máxima consecutiva
- **Sharpe Ratio**: Relación riesgo/retorno
- **Win Rate**: Porcentaje de apuestas ganadoras

### Simulación de Estrategias

```python
from src.backtest import BacktestEngine

engine = BacktestEngine()
results = engine.run_backtest(
    start_date="2023-01-01",
    end_date="2023-12-31",
    strategy="kelly_fractional",
    bankroll=10000
)

print(f"ROI: {results['roi']:.2%}")
print(f"Profit: ${results['total_profit']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
```

## 🚨 Solución de Problemas

### Problemas Comunes

1. **Error de Conexión a Base de Datos**
   - Verificar credenciales en `.env`
   - Comprobar que PostgreSQL esté ejecutándose
   - Verificar puerto y host

2. **Error de Scraping**
   - Verificar conexión a internet
   - Comprobar que 1xBet esté accesible
   - Ajustar delays en configuración

3. **Error de Modelos ML**
   - Verificar que los datos estén disponibles
   - Comprobar versiones de dependencias
   - Revisar logs para errores específicos

### Logs del Sistema

Los logs se almacenan en `logs/tennis_betting.log` y incluyen:

- Información de ingesta de datos
- Errores y advertencias
- Métricas de rendimiento
- Actividad de modelos ML

## 🔮 Roadmap Futuro

### Próximas Funcionalidades

- [ ] **API REST**: Endpoints para integración externa
- [ ] **Más Deportes**: Expansión a fútbol, baloncesto, etc.
- [ ] **Machine Learning Avanzado**: Redes neuronales y deep learning
- [ ] **Análisis de Sentimiento**: Integración con redes sociales
- [ ] **Ejecución Automática**: Conexión directa con casas de apuestas
- [ ] **App Móvil**: Aplicación nativa para iOS/Android

### Mejoras Técnicas

- [ ] **Microservicios**: Arquitectura distribuida
- [ ] **Cache Redis**: Mejora de rendimiento
- [ ] **Kubernetes**: Orquestación de contenedores
- [ ] **CI/CD**: Pipeline de despliegue automático

## 📞 Soporte

### Canales de Contacto

- **Issues**: GitHub Issues para reportar bugs
- **Discussions**: GitHub Discussions para preguntas
- **Email**: soporte@tennisbetting.com

### Contribuciones

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## ⚠️ Descargo de Responsabilidad

**IMPORTANTE**: Este sistema es para fines educativos y de investigación. Las apuestas deportivas conllevan riesgos financieros significativos. Los usuarios son responsables de sus propias decisiones de apuesta y deben:

- Entender completamente los riesgos involucrados
- No apostar más de lo que pueden permitirse perder
- Usar el sistema como una herramienta de análisis, no como garantía de ganancias
- Cumplir con todas las leyes y regulaciones locales sobre apuestas

Los desarrolladores no se hacen responsables de pérdidas financieras resultantes del uso de este sistema.

---

**Desarrollado con ❤️ para la comunidad de apuestas deportivas**
