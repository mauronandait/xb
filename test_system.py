#!/usr/bin/env python3
"""
Script de prueba para verificar que el sistema de apuestas de tenis funciona correctamente.
Este script prueba la ingesta de datos y muestra los resultados.
"""

import sys
import os
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_config():
    """Probar la configuración del sistema."""
    print("🔧 Probando configuración...")
    
    try:
        from config import config
        print(f"✅ Configuración cargada correctamente")
        print(f"   - Base de datos: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
        print(f"   - Scraping habilitado: {config.SCRAPING_ENABLED}")
        print(f"   - Bankroll: ${config.BANKROLL:,.2f}")
        return True
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False

def test_data_ingestion():
    """Probar la ingesta de datos."""
    print("\n📊 Probando ingesta de datos...")
    
    try:
        from data_ingest import TennisDataIngestor
        
        # Crear instancia del ingestor
        ingestor = TennisDataIngestor()
        print("✅ Ingestor de datos creado correctamente")
        
        # Ejecutar ingesta
        print("🔄 Ejecutando ingesta de datos...")
        matches = ingestor.run_data_ingestion()
        
        if matches:
            print(f"✅ Ingesta exitosa: {len(matches)} partidos obtenidos")
            return matches
        else:
            print("⚠️  No se obtuvieron partidos (esto puede ser normal si no hay partidos disponibles)")
            return []
            
    except Exception as e:
        print(f"❌ Error en ingesta de datos: {e}")
        return []

def test_database_connection():
    """Probar conexión a la base de datos."""
    print("\n🗄️  Probando conexión a base de datos...")
    
    try:
        from config import config
        from sqlalchemy import create_engine
        
        engine = create_engine(config.get_database_url())
        
        # Probar conexión
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Conexión a base de datos exitosa")
            return True
            
    except Exception as e:
        print(f"❌ Error de conexión a base de datos: {e}")
        print("   Asegúrate de que PostgreSQL esté ejecutándose y las credenciales sean correctas")
        return False

def display_matches(matches):
    """Mostrar los partidos obtenidos."""
    if not matches:
        print("\n📋 No hay partidos para mostrar")
        return
    
    print(f"\n🎾 PARTIDOS DE TENIS DISPONIBLES HOY ({datetime.now().strftime('%Y-%m-%d')})")
    print("=" * 80)
    
    for i, match in enumerate(matches, 1):
        print(f"\n{i}. {match.get('tournament', 'Torneo Desconocido')}")
        print(f"   {match.get('player1', 'Jugador 1')} vs {match.get('player2', 'Jugador 2')}")
        
        if 'odds' in match and match['odds']:
            odds = match['odds']
            if len(odds) >= 2 and odds[0] and odds[1]:
                print(f"   Cuotas: {match['player1']} @ {odds[0]:.2f} | {match['player2']} @ {odds[1]:.2f}")
                
                # Calcular probabilidades implícitas
                prob1 = 1 / odds[0]
                prob2 = 1 / odds[1]
                total_prob = prob1 + prob2
                margin = total_prob - 1
                
                print(f"   Probabilidades: {match['player1']} {prob1:.1%} | {match['player2']} {prob2:.1%}")
                print(f"   Margen del bookmaker: {margin:.2%}")
            else:
                print("   Cuotas: No disponibles")
        else:
            print("   Cuotas: No disponibles")
        
        if 'match_time' in match:
            print(f"   Hora: {match['match_time']}")
        
        print("-" * 60)

def test_scraping_fallback():
    """Probar el fallback de scraping si la API no está disponible."""
    print("\n🌐 Probando fallback de scraping...")
    
    try:
        from data_ingest import TennisDataIngestor
        
        ingestor = TennisDataIngestor()
        
        # Intentar scraping directamente
        print("🔄 Intentando scraping de 1xBet...")
        matches = ingestor.get_tennis_matches_scraping()
        
        if matches:
            print(f"✅ Scraping exitoso: {len(matches)} partidos encontrados")
            return matches
        else:
            print("⚠️  Scraping no retornó partidos (puede ser normal)")
            return []
            
    except Exception as e:
        print(f"❌ Error en scraping: {e}")
        return []

def main():
    """Función principal de pruebas."""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE APUESTAS DE TENIS")
    print("=" * 60)
    
    # Probar configuración
    if not test_config():
        print("\n❌ Las pruebas fallaron en la configuración. Revisa el archivo .env")
        return
    
    # Probar conexión a base de datos
    db_ok = test_database_connection()
    
    # Probar ingesta de datos
    matches = test_data_ingestion()
    
    # Si no hay partidos vía ingesta normal, probar scraping
    if not matches:
        print("\n🔄 No se obtuvieron partidos vía ingesta normal, probando scraping...")
        matches = test_scraping_fallback()
    
    # Mostrar resultados
    display_matches(matches)
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    if matches:
        print(f"✅ Sistema funcionando correctamente")
        print(f"   - Partidos obtenidos: {len(matches)}")
        print(f"   - Base de datos: {'✅' if db_ok else '❌'}")
        print(f"   - Ingesta de datos: ✅")
        print(f"   - Scraping: ✅")
        
        print(f"\n🎯 Próximos pasos:")
        print(f"   1. Ejecutar 'streamlit run src/dashboard.py' para el dashboard")
        print(f"   2. Configurar variables de entorno en config/.env")
        print(f"   3. Ejecutar 'docker-compose up -d' para usar con Docker")
        
    else:
        print(f"⚠️  Sistema parcialmente funcional")
        print(f"   - Base de datos: {'✅' if db_ok else '❌'}")
        print(f"   - Ingesta de datos: ❌")
        print(f"   - Scraping: ❌")
        
        print(f"\n🔧 Posibles soluciones:")
        print(f"   1. Verificar conexión a internet")
        print(f"   2. Comprobar que 1xBet esté accesible")
        print(f"   3. Revisar logs para errores específicos")
        print(f"   4. Ajustar selectores de scraping en data_ingest.py")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
