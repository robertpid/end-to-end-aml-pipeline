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
    
    transacciones_batch = []
    clientes_batch = []
    total_generados = 0
    lote_numero = 1
    TAMANO_LOTE = 100000  # Procesar y subir de 100,000 en 100,000

    fecha_inicio_base = datetime.now() - timedelta(days=60)

    # Clases disponibles para simular
    clases_perfiles = [ClienteNormal, PitufoBancario, LavadorPlataformas, LavadorCrypto]
    
    # Determinamos la meta aleatoria de registros a generar
    meta_registros = random.randint(TOTAL_REGISTROS_MIN, TOTAL_REGISTROS_MAX)
    logger.info(f"Meta de registros a generar: {meta_registros:,}")
    
    # Generamos una probabilidad aleatoria para los casos anómalos entre 0.2% y 1%
    prob_sospechosos = random.uniform(0.002, 0.01)
    prob_normal = 1.0 - prob_sospechosos
    prob_por_lavador = prob_sospechosos / 3.0
    
    # Obtenemos el motor de base de datos una sola vez
    engine = obtener_engine_azure()
    if not engine:
        logger.warning("No se pudo conectar a Azure SQL. Los datos solo se guardarán en CSV.")
        
    fecha_hoy_str = datetime.now().strftime("%Y%m%d")
    archivo_csv_hechos = f"transacciones_aml_{fecha_hoy_str}.csv"
    archivo_csv_dim = f"clientes_aml_{fecha_hoy_str}.csv"
    
    # 1. Generación de Datos en Lotes
    while total_generados < meta_registros:
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
            
            transacciones_batch.extend(transacciones)
            clientes_batch.append(info_cliente)
            
        except Exception as e:
            logger.error(f"Error generando datos para la clase {perfil_class.__name__}: {e}")

        # Comprobar si llegamos al tamaño de lote o a la meta total
        if len(transacciones_batch) >= TAMANO_LOTE or (total_generados + len(transacciones_batch)) >= meta_registros:
            
            # Recortar si nos pasamos de la meta
            if total_generados + len(transacciones_batch) > meta_registros:
                exceso = (total_generados + len(transacciones_batch)) - meta_registros
                transacciones_batch = transacciones_batch[:-exceso]
                
            total_generados += len(transacciones_batch)
            logger.info(f"Generado Lote {lote_numero} - Procesando {len(transacciones_batch):,} transacciones (Total acumulado: {total_generados:,}/{meta_registros:,})...")
            
            # 2. Creación de DataFrames del Lote
            df_transacciones = pd.DataFrame(transacciones_batch)
            df_clientes = pd.DataFrame(clientes_batch)
            
            # 3. Inyección de Ruido
            df_transacciones_ruido = inyectar_ruido(df_transacciones)
            
            # 4. Exportación a CSV incremental (Append)
            modo_csv = 'w' if lote_numero == 1 else 'a'
            header_csv = True if lote_numero == 1 else False
            
            try:
                df_transacciones_ruido.to_csv(archivo_csv_hechos, mode=modo_csv, header=header_csv, index=False)
                df_clientes.to_csv(archivo_csv_dim, mode=modo_csv, header=header_csv, index=False)
            except Exception as e:
                logger.error(f"Error al exportar los CSV en lote {lote_numero}: {e}")

            # 5. Subida a Azure SQL
            if engine:
                modo_db = 'replace' if lote_numero == 1 else 'append'
                # Dim_Cliente crecerá mucho, un REPLACE en la primera y APPEND después.
                subir_dataframe_azure(df=df_clientes, nombre_tabla="Dim_Cliente", engine=engine, if_exists=modo_db)
                subir_dataframe_azure(df=df_transacciones_ruido, nombre_tabla="Fact_Transacciones", engine=engine, if_exists=modo_db)
                
            # Limpiar memoria para el siguiente lote
            transacciones_batch = []
            clientes_batch = []
            lote_numero += 1
            
    logger.info("Proceso finalizado exitosamente. El millón de transacciones ha sido cargado por lotes.")

if __name__ == "__main__":
    main()
