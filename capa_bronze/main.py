import logging
import random
from datetime import datetime, timedelta
import pandas as pd

from config import TOTAL_REGISTROS_MIN, TOTAL_REGISTROS_MAX
from clases_actores import ClienteNormal, PitufoBancario, LavadorPlataformas, LavadorCrypto
from data_quality import inyectar_ruido
from db_connection import obtener_engine_azure, subir_dataframe_azure

# Configurar logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Función principal que orquesta la generación de datos, inyección de ruido,
    exportación a CSV y subida a Azure SQL.
    """
    logger.info("Iniciando la generación de datos AML sintéticos...")
    
    transacciones_totales = []
    clientes_totales = []
    fecha_inicio_base = datetime.now() - timedelta(days=60)

    # Clases disponibles para simular
    clases_perfiles = [ClienteNormal, PitufoBancario, LavadorPlataformas, LavadorCrypto]
    
    # Determinamos la meta aleatoria de registros a generar
    meta_registros = random.randint(TOTAL_REGISTROS_MIN, TOTAL_REGISTROS_MAX)
    
    # Generamos una probabilidad aleatoria para los casos anómalos entre 0.2% y 1%
    prob_sospechosos = random.uniform(0.002, 0.01)
    prob_normal = 1.0 - prob_sospechosos
    prob_por_lavador = prob_sospechosos / 3.0
    
    # 1. Generación de Datos
    while len(transacciones_totales) < meta_registros:
        # Elegimos aleatoriamente un perfil.
        perfil_class = random.choices(
            population=clases_perfiles,
            weights=[prob_normal, prob_por_lavador, prob_por_lavador, prob_por_lavador],
            k=1
        )[0]
        
        perfil_instancia = perfil_class()
        
        try:
            transacciones = perfil_instancia.generar_transacciones(fecha_inicio=fecha_inicio_base)
            info_cliente = perfil_instancia.obtener_dim_cliente()
            
            transacciones_totales.extend(transacciones)
            clientes_totales.append(info_cliente)
            
        except Exception as e:
            logger.error(f"Error generando datos para la clase {perfil_class.__name__}: {e}")

    # Forzar exactamente meta_registros si se excede
    if len(transacciones_totales) > meta_registros:
        transacciones_totales = transacciones_totales[:meta_registros]

    logger.info(f"Generadas {len(transacciones_totales)} transacciones y {len(clientes_totales)} clientes.")

    # 2. Creación de DataFrames
    df_transacciones = pd.DataFrame(transacciones_totales)
    df_clientes = pd.DataFrame(clientes_totales)
    
    # 3. Inyección de Ruido
    logger.info("Iniciando inyección de ruido...")
    df_transacciones_ruido = inyectar_ruido(df_transacciones)
    logger.info(f"Ruido inyectado. Filas finales en hechos: {len(df_transacciones_ruido)}")
    
    # 4. Exportación a CSV
    fecha_hoy_str = datetime.now().strftime("%Y%m%d")
    archivo_csv_hechos = f"transacciones_aml_{fecha_hoy_str}.csv"
    archivo_csv_dim = f"clientes_aml_{fecha_hoy_str}.csv"
    
    try:
        df_transacciones_ruido.to_csv(archivo_csv_hechos, index=False)
        df_clientes.to_csv(archivo_csv_dim, index=False)
        logger.info(f"Archivos exportados exitosamente: {archivo_csv_hechos}, {archivo_csv_dim}")
    except Exception as e:
        logger.error(f"Error al exportar los CSV: {e}")

    # 5. Subida a Azure SQL
    engine = obtener_engine_azure()
    if engine:
        subir_dataframe_azure(df=df_clientes, nombre_tabla="Dim_Cliente", engine=engine)
        subir_dataframe_azure(df=df_transacciones_ruido, nombre_tabla="Fact_Transacciones", engine=engine)
    else:
        logger.warning("No se pudo conectar a Azure SQL. Los datos solo están en CSV.")
        
    logger.info("Proceso finalizado exitosamente.")

if __name__ == "__main__":
    main()
