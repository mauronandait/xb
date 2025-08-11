FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY config/ ./config/

# Crear directorio de logs
RUN mkdir -p logs

# Exponer puertos
EXPOSE 8000 8501

# Comando por defecto
CMD ["python", "-m", "streamlit", "run", "src/dashboard.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
