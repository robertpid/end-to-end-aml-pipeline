import pandas as pd
import numpy as np
from config import PROBABILIDAD_RUIDO

def inyectar_ruido(df: pd.DataFrame) -> pd.DataFrame:
    """
    Inyecta ruido de forma aleatoria (data sucia) al DataFrame de transacciones.
    Utiliza operaciones vectorizadas de Pandas.
    
    Args:
        df (pd.DataFrame): DataFrame original limpio.
        
    Returns:
        pd.DataFrame: DataFrame con ruido inyectado.
    """
    df_ruido = df.copy()
    
    # Agregar columna de moneda para inyectar errores tipográficos
    if 'Moneda' not in df_ruido.columns:
        df_ruido['Moneda'] = 'USD'
        
    num_filas = len(df_ruido)
    
    # Generar máscara para el 15% de ruido
    # np.random.rand devuelve números entre 0 y 1. Si es < 0.15, es True
    mask_ruido = np.random.rand(num_filas) < PROBABILIDAD_RUIDO
    indices_ruido = df_ruido.index[mask_ruido].tolist()
    
    if not indices_ruido:
        return df_ruido # Sin ruido si la probabilidad no generó ninguno
        
    # Repartir los índices de ruido aleatoriamente entre los 4 tipos de errores
    np.random.shuffle(indices_ruido)
    num_errores = len(indices_ruido)
    
    # Dividir los índices en 4 grupos (aproximadamente iguales)
    splits = np.array_split(indices_ruido, 4)
    idx_fecha, idx_typo, idx_nulo, idx_duplicado = splits[0], splits[1], splits[2], splits[3]
    
    # 1. Alteración de Fecha (YYYY-MM-DD -> DD/MM/YYYY)
    if len(idx_fecha) > 0:
        # Vectorizado: Convertir strings a datetime, formatear y devolver
        try:
            fechas_dt = pd.to_datetime(df_ruido.loc[idx_fecha, 'FK_Tiempo'], errors='coerce')
            df_ruido.loc[idx_fecha, 'FK_Tiempo'] = fechas_dt.dt.strftime('%d/%m/%Y %H:%M:%S')
        except Exception as e:
            pass # Si falla el parseo simplemente no aplica el ruido
            
    # 2. Error Tipográfico en moneda
    if len(idx_typo) > 0:
        typos = ['usd', ' UDS ', 'US $', 'soles', ' pen ', 'eur ', ' GBP', 'yenes', 'cny', 'rmb ']
        # np.random.choice para elegir aleatoriamente un typo para cada fila en idx_typo
        df_ruido.loc[idx_typo, 'Moneda'] = np.random.choice(typos, size=len(idx_typo))
        
    # 3. Nulos Forzados
    if len(idx_nulo) > 0:
        df_ruido.loc[idx_nulo, 'PK_Transaccion'] = np.nan
        
    # 4. Duplicación de fila con +1 segundo
    if len(idx_duplicado) > 0:
        df_a_duplicar = df_ruido.loc[idx_duplicado].copy()
        try:
            fechas_dt = pd.to_datetime(df_a_duplicar['FK_Tiempo'], errors='coerce')
            fechas_dt = fechas_dt + pd.Timedelta(seconds=1)
            # Volver al formato original o dejar el timestamp (usamos el mismo que tenga)
            # Asumimos YYYY-MM-DD %H:%M:%S por defecto
            df_a_duplicar['FK_Tiempo'] = fechas_dt.dt.strftime('%Y-%m-%d %H:%M:%S')
            df_ruido = pd.concat([df_ruido, df_a_duplicar], ignore_index=True)
        except Exception:
            pass

    return df_ruido
