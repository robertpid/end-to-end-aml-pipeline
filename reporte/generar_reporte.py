import os
import glob
import pandas as pd
import numpy as np
from fpdf import FPDF
from datetime import datetime

print("Generando datos mediante main.py...")
os.system("python capa_bronze/main.py")

# Encontrar los CSVs recién generados
fecha_hoy = datetime.now().strftime("%Y%m%d")
archivos_hechos = glob.glob(f"transacciones_aml_{fecha_hoy}.csv")
archivos_dim = glob.glob(f"clientes_aml_{fecha_hoy}.csv")

if not archivos_hechos or not archivos_dim:
    print("No se encontraron archivos CSV generados.")
    exit(1)

archivo_hechos = max(archivos_hechos, key=os.path.getctime)
archivo_dim = max(archivos_dim, key=os.path.getctime)

print(f"Leyendo {archivo_hechos} y {archivo_dim}...")
df_transacciones_bronce = pd.read_csv(archivo_hechos)
df_clientes_bronce = pd.read_csv(archivo_dim)

# --- CAPA PLATA ---
print("Procesando Capa Plata...")
df_plata = df_transacciones_bronce.copy()
# Filtrar nulos
df_plata = df_plata[df_plata['PK_Transaccion'].notnull()]
# Filtro > 0
df_plata = df_plata[df_plata['Monto_USD'] > 0]
# Eliminar duplicados
df_plata = df_plata.drop_duplicates(subset=['PK_Transaccion'])
df_plata['Monto_Original'] = df_plata['Monto_Original'].astype(float).round(2)
df_plata['Monto_USD'] = df_plata['Monto_USD'].astype(float).round(2)
df_plata['FK_Canal'] = df_plata['FK_Canal'].str.strip()
df_plata['Moneda'] = df_plata['Moneda'].str.strip().str.upper()

# --- CAPA ORO ---
print("Procesando Capa Oro...")
# Agrupaciones de origen
agg_origen = df_plata.groupby('FK_Cliente_Origen').agg(
    Total_Tx_Enviadas=('PK_Transaccion', 'count'),
    Monto_Total_Enviado_USD=('Monto_USD', 'sum'),
    Monto_Max_Enviado_USD=('Monto_USD', 'max'),
    Destinatarios_Unicos=('FK_Cliente_Destino', 'nunique'),
    Tx_Canal_Crypto=('FK_Canal', lambda x: x.str.contains('(?i)Crypto|Exchange|Bridge').sum()),
    Tx_Canal_Plataformas=('FK_Canal', lambda x: x.str.contains('(?i)Plataforma|Terceros').sum())
).reset_index().rename(columns={'FK_Cliente_Origen': 'PK_Cliente'})

# Agrupaciones de destino
agg_destino = df_plata.groupby('FK_Cliente_Destino').agg(
    Total_Tx_Recibidas=('PK_Transaccion', 'count'),
    Monto_Total_Recibido_USD=('Monto_USD', 'sum'),
    Remitentes_Unicos=('FK_Cliente_Origen', 'nunique')
).reset_index().rename(columns={'FK_Cliente_Destino': 'PK_Cliente'})

# Joins
df_features = df_clientes_bronce.merge(agg_origen, on='PK_Cliente', how='left').merge(agg_destino, on='PK_Cliente', how='left').fillna(0)

df_features['Total_Movido'] = df_features['Monto_Total_Enviado_USD'] + df_features['Monto_Total_Recibido_USD']
df_features['Indice_Fan_In'] = np.where(df_features['Total_Tx_Recibidas'] > 0, df_features['Remitentes_Unicos'] / df_features['Total_Tx_Recibidas'], 0)
df_features['Ratio_Tx_Crypto'] = np.where(df_features['Total_Tx_Enviadas'] > 0, df_features['Tx_Canal_Crypto'] / df_features['Total_Tx_Enviadas'], 0)
df_features['Ratio_Operado_vs_Ingreso_Declarado'] = df_features['Total_Movido'] / (np.where(df_features['Ingreso_Mensual_Aprox'] <= 0, 1000.0, df_features['Ingreso_Mensual_Aprox']) * 12.0)

# REGLAS
cond_structuring = (df_features["Total_Tx_Enviadas"].between(3, 10)) & (df_features["Monto_Max_Enviado_USD"] <= 3000.0) & (df_features["Monto_Total_Enviado_USD"].between(8000.0, 10500.0))
cond_fan_in = (df_features["Total_Tx_Recibidas"] >= 40) & (df_features["Indice_Fan_In"] >= 0.70) & (df_features["Monto_Total_Enviado_USD"] >= 0.70 * df_features["Monto_Total_Recibido_USD"]) & (df_features["Monto_Total_Enviado_USD"] < 10000.0)
cond_crypto = (df_features["Tx_Canal_Crypto"] >= 3) & (df_features["Monto_Max_Enviado_USD"] <= 2600.0) & (df_features["Ratio_Tx_Crypto"] >= 0.50)

df_features['Flag_Structuring_Pitufeo'] = cond_structuring.astype(int)
df_features['Flag_Fan_In_Plataforma'] = cond_fan_in.astype(int)
df_features['Flag_Crypto_Mixer'] = cond_crypto.astype(int)

# Métricas
total_transacciones = len(df_plata)
total_clientes = len(df_clientes_bronce)
alertas_structuring = df_features['Flag_Structuring_Pitufeo'].sum()
alertas_fanin = df_features['Flag_Fan_In_Plataforma'].sum()
alertas_crypto = df_features['Flag_Crypto_Mixer'].sum()
total_alertas = alertas_structuring + alertas_fanin + alertas_crypto

print(f"Total Tx: {total_transacciones}")
print(f"Total Clientes: {total_clientes}")
print(f"Alertas Pitufeo: {alertas_structuring}, Fan-In: {alertas_fanin}, Crypto: {alertas_crypto}")

# TOP Sujetos (Simulados para PDF tomando los de mayor total movido por cada flag)
sujeto_fanin = df_features[df_features['Flag_Fan_In_Plataforma'] == 1].sort_values('Total_Movido', ascending=False).head(1)
sujeto_crypto = df_features[df_features['Flag_Crypto_Mixer'] == 1].sort_values('Total_Movido', ascending=False).head(1)
sujeto_structuring = df_features[df_features['Flag_Structuring_Pitufeo'] == 1].sort_values('Total_Movido', ascending=False).head(1)

# Generación PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'INFORME DE INTELIGENCIA FINANCIERA (ROS)', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

pdf = PDF()
pdf.add_page()

pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 8, "A: Comité de Cumplimiento Normativo / Oficial de Cumplimiento", ln=1)
pdf.cell(0, 8, "DE: Unidad de Inteligencia Financiera (UIF) - Análisis Transaccional", ln=1)
pdf.cell(0, 8, f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", ln=1)
pdf.cell(0, 8, "CLASIFICACIÓN: CONFIDENCIAL / RESTRINGIDO", ln=1)
pdf.ln(5)

pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "1. Resumen de Hallazgos", ln=1)
pdf.set_font("Arial", '', 11)
resumen = f"En el último barrido de monitoreo transaccional se analizó un universo de {total_transacciones:,} operaciones financieras consolidadas, correspondientes a una cartera de {total_clientes:,} clientes activos. Tras aplicar la matriz de riesgo y reglas heurísticas de detección, el sistema ha emitido {total_alertas:,} alertas confirmadas de alto riesgo."
pdf.multi_cell(0, 8, resumen.encode('latin-1', 'replace').decode('latin-1'))
pdf.ln(3)

pdf.cell(0, 8, "Distribución de alertas por tipología:", ln=1)
pdf.cell(0, 8, f"- Concentración de Fondos (Fan-In): {alertas_fanin} alertas.", ln=1)
pdf.cell(0, 8, f"- Ofuscación con Criptoactivos (Crypto Mixers): {alertas_crypto} alertas.", ln=1)
pdf.cell(0, 8, f"- Estructuración (Pitufeo/Structuring): {alertas_structuring} alertas.", ln=1)
pdf.ln(5)

pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "2. Análisis de Patrones y Comportamiento", ln=1)
pdf.set_font("Arial", '', 11)
patrones = "Fan-In: Clientes reciben ráfagas de micro-depósitos de múltiples contrapartes en lapsos muy cortos, para luego evacuar el capital de una sola vez.\nCrypto Mixers: Fondos ingresados son canalizados rápidamente al 100% hacia Exchanges de criptoactivos en transferencias de alta frecuencia, ocultando su trazabilidad.\nEstructuración: Depósitos en efectivo concentrados sistemáticamente justo por debajo del límite regulatorio de USD 10,000 para eludir controles."
pdf.multi_cell(0, 8, patrones.encode('latin-1', 'replace').decode('latin-1'))
pdf.ln(5)

pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "3. Sujetos de Interés (Casos Críticos Detectados)", ln=1)
pdf.set_font("Arial", '', 11)

if not sujeto_fanin.empty:
    sf = sujeto_fanin.iloc[0]
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"- Sujeto ID: {sf['PK_Cliente']} (Fan-In)", ln=1)
    pdf.set_font("Arial", '', 11)
    obs = f"Recibió {sf['Total_Tx_Recibidas']:.0f} transferencias, luego envió un total de USD {sf['Monto_Total_Enviado_USD']:,.2f} con una relación de ingresos/operado de {sf['Ratio_Operado_vs_Ingreso_Declarado']:.2f}."
    pdf.multi_cell(0, 8, obs.encode('latin-1', 'replace').decode('latin-1'))
    
if not sujeto_crypto.empty:
    sc = sujeto_crypto.iloc[0]
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"- Sujeto ID: {sc['PK_Cliente']} (Crypto Mixer)", ln=1)
    pdf.set_font("Arial", '', 11)
    obs = f"Canalizó USD {sc['Monto_Total_Enviado_USD']:,.2f} a exchanges, representando el {sc['Ratio_Tx_Crypto']*100:.1f}% de sus transferencias de salida en {sc['Tx_Canal_Crypto']:.0f} envíos."
    pdf.multi_cell(0, 8, obs.encode('latin-1', 'replace').decode('latin-1'))

if not sujeto_structuring.empty:
    ss = sujeto_structuring.iloc[0]
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"- Sujeto ID: {ss['PK_Cliente']} (Estructuración)", ln=1)
    pdf.set_font("Arial", '', 11)
    obs = f"Generó {ss['Total_Tx_Enviadas']:.0f} transacciones de salida totalizando USD {ss['Monto_Total_Enviado_USD']:,.2f}, todas por montos menores a USD 3,000."
    pdf.multi_cell(0, 8, obs.encode('latin-1', 'replace').decode('latin-1'))

pdf.ln(5)
pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "4. Plan de Acción Recomendado", ln=1)
pdf.set_font("Arial", '', 11)
acciones = "1. Bloqueo Preventivo Inmediato: Congelar transitoriamente las cuentas de los Sujetos de Interés.\n2. Ampliación de Debida Diligencia (EDD): Solicitar justificación comercial o de origen de fondos en efectivo y transferencias masivas.\n3. Reporte de Operaciones Sospechosas (ROS): Enviar a la UIF nacional adjuntando evidencia transaccional.\n4. Watchlists: Agregar cuentas contrapartes vinculadas a bloqueo preventivo."
pdf.multi_cell(0, 8, acciones.encode('latin-1', 'replace').decode('latin-1'))

pdf_path = "Reporte_ROS_Inteligencia_Financiera.pdf"
pdf.output(pdf_path)
print(f"PDF generado exitosamente en: {pdf_path}")
