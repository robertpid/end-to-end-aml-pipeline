import urllib
import logging
from sqlalchemy import create_engine
import pandas as pd
from config import AZURE_SQL_CONNECTION_STRING

# Configurar logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def obtener_engine_azure():
    """
    Crea y retorna un motor de SQLAlchemy configurado para conectarse a Azure SQL
    utilizando pyodbc.
    
    Returns:
        sqlalchemy.engine.Engine: Motor de conexión a la base de datos o None si falla.
    """
    try:
        params = urllib.parse.quote_plus(AZURE_SQL_CONNECTION_STRING)
        # Formato de conexión para sqlalchemy usando pyodbc
        engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", fast_executemany=True)
        return engine
    except Exception as e:
        logger.error(f"Error al crear el engine de SQLAlchemy: {e}")
        return None

def subir_dataframe_azure(df: pd.DataFrame, nombre_tabla: str, engine, if_exists: str = 'replace') -> bool:
    """
    Sube un DataFrame de Pandas a una tabla en Azure SQL.
    
    Args:
        df (pd.DataFrame): DataFrame a subir.
        nombre_tabla (str): Nombre de la tabla destino.
        engine (sqlalchemy.engine.Engine): Motor de conexión.
        
    Returns:
        bool: True si fue exitoso, False en caso contrario.
    """
    if engine is None:
        logger.error("El engine proporcionado es None. No se puede subir los datos.")
        return False
        
    try:
        logger.info(f"Iniciando la carga de datos a la tabla '{nombre_tabla}' en Azure SQL...")
        df.to_sql(name=nombre_tabla, con=engine, if_exists=if_exists, index=False, chunksize=50000)
        logger.info(f"Carga exitosa a '{nombre_tabla}'. ({len(df)} filas insertadas)")
        return True
    except Exception as e:
        logger.error(f"Error al subir el DataFrame a la tabla '{nombre_tabla}': {e}")
        return False
