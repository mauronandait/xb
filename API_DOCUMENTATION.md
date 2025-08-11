# 📚 Documentación de la API REST - Sistema de Apuestas de Tenis

## 🚀 Descripción General

La API REST del Sistema de Apuestas de Tenis proporciona endpoints para acceder a todas las funcionalidades del sistema, incluyendo señales de apuestas, partidos, backtesting y alertas.

**URL Base:** `http://localhost:8000/api`

**Versión:** 1.0.0

## 🔐 Autenticación

La API utiliza autenticación basada en API Key que debe incluirse en el header `X-API-Key`.

```bash
curl -H "X-API-Key: your_api_key_here" \
     http://localhost:8000/api/signals
```

## 📊 Endpoints Disponibles

### 1. Health Check

#### `GET /api/health`

Verifica el estado de salud del sistema.

**Respuesta:**
```json
{
  "status": "healthy",
  "timestamp": "2024-08-10T23:30:00",
  "version": "1.0.0",
  "database": "connected",
  "services": {
    "database": true,
    "alerts": true,
    "signals": true
  }
}
```

**Códigos de Estado:**
- `200`: Sistema saludable
- `503`: Sistema no saludable

---

### 2. Señales de Apuestas

#### `GET /api/signals`

Obtiene las señales de apuestas generadas por el sistema.

**Parámetros de Consulta:**
- `limit` (opcional): Número máximo de señales (default: 50)
- `confidence` (opcional): Nivel de confianza (`high`, `medium`, `low`, `all`)
- `min_ev` (opcional): Valor esperado mínimo (default: 0.0)

**Ejemplo:**
```bash
curl -H "X-API-Key: your_key" \
     "http://localhost:8000/api/signals?confidence=high&min_ev=0.05&limit=20"
```

**Respuesta:**
```json
{
  "signals": [
    {
      "match_id": "Djokovic_Nadal_Australian_Open_20241201",
      "tournament": "Australian Open",
      "player1": "Novak Djokovic",
      "player2": "Rafael Nadal",
      "recommended_bet": "player1",
      "player_name": "Novak Djokovic",
      "odds": 1.85,
      "expected_value": 0.073,
      "confidence_level": "high",
      "signal_type": "value_bet"
    }
  ],
  "summary": {
    "total_signals": 15,
    "high_confidence": 8,
    "medium_confidence": 5,
    "low_confidence": 2,
    "average_ev": 0.045
  },
  "filters_applied": {
    "confidence": "high",
    "min_ev": 0.05,
    "limit": 20
  },
  "timestamp": "2024-08-10T23:30:00"
}
```

#### `GET /api/signals/{signal_id}`

Obtiene una señal específica por ID.

**Ejemplo:**
```bash
curl -H "X-API-Key: your_key" \
     "http://localhost:8000/api/signals/Djokovic_Nadal_Australian_Open_20241201"
```

---

### 3. Partidos

#### `GET /api/matches`

Obtiene los partidos disponibles para análisis.

**Parámetros de Consulta:**
- `limit` (opcional): Número máximo de partidos (default: 50)
- `tournament` (opcional): Filtrar por torneo
- `surface` (opcional): Filtrar por superficie (`hard`, `clay`, `grass`)
- `date_from` (opcional): Fecha de inicio (ISO format)
- `date_to` (opcional): Fecha de fin (ISO format)

**Ejemplo:**
```bash
curl -H "X-API-Key: your_key" \
     "http://localhost:8000/api/matches?tournament=Australian%20Open&surface=hard&limit=100"
```

**Respuesta:**
```json
{
  "matches": [
    {
      "match_id": "Djokovic_Nadal_Australian_Open_20241201",
      "tournament": "Australian Open",
      "player1": "Novak Djokovic",
      "player2": "Rafael Nadal",
      "match_time": "2024-12-01T15:00:00",
      "surface": "hard",
      "round": "Final",
      "player1_odds": 1.85,
      "player2_odds": 2.10
    }
  ],
  "total": 25,
  "filters_applied": {
    "tournament": "Australian Open",
    "surface": "hard",
    "limit": 100
  },
  "timestamp": "2024-08-10T23:30:00"
}
```

---

### 4. Backtesting

#### `POST /api/backtest`

Ejecuta backtesting de estrategias de apuestas.

**Cuerpo de la Petición:**
```json
{
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "strategy": "kelly_fractional",
  "bankroll": 10000
}
```

**Parámetros:**
- `start_date` (requerido): Fecha de inicio del backtest
- `end_date` (requerido): Fecha de fin del backtest
- `strategy` (opcional): Estrategia a probar (default: `kelly_fractional`)
- `bankroll` (opcional): Bankroll inicial (default: 10000)

**Ejemplo:**
```bash
curl -X POST -H "X-API-Key: your_key" \
     -H "Content-Type: application/json" \
     -d '{"start_date": "2023-01-01", "end_date": "2023-12-31", "strategy": "kelly_fractional"}' \
     "http://localhost:8000/api/backtest"
```

**Respuesta:**
```json
{
  "backtest_results": {
    "total_bets": 156,
    "winning_bets": 89,
    "losing_bets": 67,
    "win_rate": 0.571,
    "roi": 0.089,
    "total_profit": 890.50,
    "max_drawdown": -0.045,
    "sharpe_ratio": 1.23
  },
  "parameters": {
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "strategy": "kelly_fractional",
    "bankroll": 10000
  },
  "timestamp": "2024-08-10T23:30:00"
}
```

---

### 5. Alertas

#### `GET /api/alerts`

Obtiene el historial de alertas del sistema.

**Parámetros de Consulta:**
- `type` (opcional): Tipo de alerta (`value_bet`, `odds_change`, `system`)
- `limit` (opcional): Número máximo de alertas (default: 100)

**Ejemplo:**
```bash
curl -H "X-API-Key: your_key" \
     "http://localhost:8000/api/alerts?type=value_bet&limit=50"
```

**Respuesta:**
```json
{
  "alerts": [
    {
      "timestamp": "2024-08-10T23:25:00",
      "type": "value_bet",
      "data": {
        "player_name": "Novak Djokovic",
        "expected_value": 0.073
      },
      "success": true
    }
  ],
  "stats": {
    "total_alerts": 45,
    "successful_alerts": 43,
    "failed_alerts": 2,
    "success_rate": 95.56,
    "type_counts": {
      "value_bet": 30,
      "odds_change": 10,
      "system": 5
    }
  },
  "filters_applied": {
    "type": "value_bet",
    "limit": 50
  },
  "timestamp": "2024-08-10T23:30:00"
}
```

#### `POST /api/alerts/test`

Prueba el sistema de alertas enviando una alerta de prueba.

**Cuerpo de la Petición:**
```json
{
  "type": "system",
  "message": "Prueba del sistema de alertas",
  "severity": "info"
}
```

**Ejemplo:**
```bash
curl -X POST -H "X-API-Key: your_key" \
     -H "Content-Type: application/json" \
     -d '{"type": "system", "message": "Prueba del sistema", "severity": "info"}' \
     "http://localhost:8000/api/alerts/test"
```

---

### 6. Estadísticas del Sistema

#### `GET /api/stats`

Obtiene estadísticas completas del sistema.

**Ejemplo:**
```bash
curl -H "X-API-Key: your_key" \
     "http://localhost:8000/api/stats"
```

**Respuesta:**
```json
{
  "database": {
    "total_matches": 1250,
    "total_signals": 89,
    "last_update": "2024-08-10T23:25:00"
  },
  "alerts": {
    "total_alerts": 45,
    "success_rate": 95.56
  },
  "signals": {
    "total_signals": 15,
    "high_confidence": 8,
    "average_ev": 0.045
  },
  "system": {
    "version": "1.0.0",
    "environment": "development"
  },
  "timestamp": "2024-08-10T23:30:00"
}
```

---

### 7. Actualización de Datos

#### `POST /api/refresh`

Fuerza la actualización de datos del sistema.

**Ejemplo:**
```bash
curl -X POST -H "X-API-Key: your_key" \
     "http://localhost:8000/api/refresh"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Actualización de datos iniciada",
  "timestamp": "2024-08-10T23:30:00"
}
```

---

## 🔧 Códigos de Estado HTTP

- `200`: Éxito
- `400`: Error en la petición (datos inválidos)
- `401`: No autorizado (API key faltante o inválida)
- `404`: Recurso no encontrado
- `500`: Error interno del servidor

## 📝 Ejemplos de Uso

### Ejemplo 1: Obtener Señales de Alta Confianza

```python
import requests

api_key = "your_api_key_here"
base_url = "http://localhost:8000/api"

headers = {"X-API-Key": api_key}

# Obtener señales de alta confianza
response = requests.get(
    f"{base_url}/signals",
    headers=headers,
    params={"confidence": "high", "min_ev": 0.05}
)

if response.status_code == 200:
    signals = response.json()["signals"]
    print(f"Señales encontradas: {len(signals)}")
    
    for signal in signals:
        print(f"🎾 {signal['player_name']} - EV: {signal['expected_value']:.3f}")
else:
    print(f"Error: {response.status_code}")
```

### Ejemplo 2: Ejecutar Backtest

```python
import requests

api_key = "your_api_key_here"
base_url = "http://localhost:8000/api"

headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

# Ejecutar backtest
backtest_data = {
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "strategy": "kelly_fractional",
    "bankroll": 10000
}

response = requests.post(
    f"{base_url}/backtest",
    headers=headers,
    json=backtest_data
)

if response.status_code == 200:
    results = response.json()["backtest_results"]
    print(f"ROI: {results['roi']:.1%}")
    print(f"Win Rate: {results['win_rate']:.1%}")
    print(f"Profit: ${results['total_profit']:.2f}")
else:
    print(f"Error: {response.status_code}")
```

### Ejemplo 3: Monitorear Sistema

```python
import requests
import time

api_key = "your_api_key_here"
base_url = "http://localhost:8000/api"

headers = {"X-API-Key": api_key}

def monitor_system():
    while True:
        try:
            # Verificar salud del sistema
            health_response = requests.get(f"{base_url}/health", headers=headers)
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"✅ Sistema: {health_data['status']}")
                print(f"📊 Base de datos: {health_data['database']}")
            else:
                print(f"❌ Error en health check: {health_response.status_code}")
            
            # Obtener estadísticas
            stats_response = requests.get(f"{base_url}/stats", headers=headers)
            
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                print(f"🎾 Partidos: {stats_data['database']['total_matches']}")
                print(f"📈 Señales: {stats_data['signals']['total_signals']}")
            
            time.sleep(60)  # Verificar cada minuto
            
        except Exception as e:
            print(f"Error en monitoreo: {e}")
            time.sleep(60)

# Ejecutar monitoreo
monitor_system()
```

## 🚀 Iniciar la API

Para iniciar la API REST del sistema:

```bash
# Modo API
python main.py --mode api --host 0.0.0.0 --api-port 8000

# O directamente
python src/api.py
```

## 📋 Configuración

### Variables de Entorno

```bash
# API Key para autenticación
API_KEY=your_secret_api_key_here

# Configuración de JWT (para futuras funcionalidades)
JWT_SECRET_KEY=your_jwt_secret_key_here
```

### Configuración de CORS

La API está configurada para permitir acceso desde cualquier origen (`*`). En producción, considera restringir esto a dominios específicos.

## 🔒 Seguridad

- **API Key**: Todas las peticiones requieren una API key válida
- **Rate Limiting**: Considera implementar limitación de tasa en producción
- **HTTPS**: En producción, usa HTTPS para todas las comunicaciones
- **Validación**: Todos los inputs son validados antes del procesamiento

## 📚 Recursos Adicionales

- **Dashboard Web**: `http://localhost:5000` - Interfaz web del sistema
- **Logs**: `logs/tennis_betting.log` - Logs del sistema
- **Configuración**: `config/.env` - Variables de entorno

## 🤝 Soporte

Para soporte técnico o preguntas sobre la API:

1. Revisa los logs del sistema
2. Verifica la configuración de variables de entorno
3. Usa el endpoint `/api/health` para diagnosticar problemas
4. Consulta la documentación del sistema principal

---

**Desarrollado con ❤️ para la comunidad de apuestas deportivas**
