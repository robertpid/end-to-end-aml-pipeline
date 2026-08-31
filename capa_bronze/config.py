import os

"""
Configuraciones y constantes globales del proyecto AML.
"""

# Umbrales
UMBRAL_ALERTA = 10000.0

# Probabilidad de que una transacción sufra alteraciones de formato
PROBABILIDAD_RUIDO = 0.15

# Moneda estándar para la tabla de hechos
MONEDA_ESTANDAR = 'USD'

# Tasas de cambio (1 USD = X Moneda)
TASAS_CAMBIO = {
    'USD': 1.00,
    'PEN': 3.35,  # Sol peruano
    'EUR': 0.86,  # Euro
    'GBP': 0.74,  # Libra esterlina
    'JPY': 159.35, # Yen japonés
    'CNY': 6.72   # Yuan chino
}

# Total de registros a generar como mínimo
TOTAL_REGISTROS = 10000

# Cadena de conexión para Azure SQL
AZURE_SQL_CONNECTION_STRING = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=tcp:sqldb-pitufeotracking-source.database.windows.net,1433;"
    "Database=free-sql-db-9553025;"
    "Uid=admin_robert;"
    f"Pwd={os.getenv('DB_PASSWORD')};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)
