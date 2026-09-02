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

# Rango de registros a generar para mayor realismo (2.5 a 3 millones)
TOTAL_REGISTROS_MIN = 2500000
TOTAL_REGISTROS_MAX = 3000000

