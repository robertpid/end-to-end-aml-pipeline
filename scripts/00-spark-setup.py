import os
import sys

# Definir la configuración de Spark y Delta Lake
from pyspark.sql import SparkSession

print("Inicializando SparkSession con soporte para Delta Lake...")

spark = (SparkSession.builder
    .appName("DatabricksSimulator")
    .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    # Ignoramos la autenticación de Databricks para entorno local
    .config("spark.databricks.workspaceUrl", "local")
    .getOrCreate())

print("✅ SparkSession iniciada correctamente. Variable global 'spark' inyectada.")

# Simular la función display() de Databricks
def display(df, limit=20):
    """
    Simulador de display() para entorno Jupyter local.
    Si es un DataFrame de Spark, muestra una tabla Pandas con un límite de filas.
    """
    try:
        # Verificamos si es DataFrame de Spark
        if hasattr(df, 'limit') and hasattr(df, 'toPandas'):
            from IPython.display import display as ipython_display
            print(f"Mostrando primeros {limit} registros (Simulación de display Databricks):")
            ipython_display(df.limit(limit).toPandas())
        else:
            # Fallback a print estándar
            print(df)
    except Exception as e:
        print(f"Error mostrando tabla: {e}")

print("✅ Función global 'display()' inyectada.")
