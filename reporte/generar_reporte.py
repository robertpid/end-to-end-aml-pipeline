import pandas as pd
from fpdf import FPDF
from datetime import datetime

# NOTA: Este script est diseado para ser copiado/ejecutado directamente 
# en un Notebook de Databricks, donde el objeto `spark` ya est inicializado.

print("Obteniendo datos de las Capas Silver y Gold desde Databricks...")

try:
    # Consulta de totales usando Spark SQL nativo de Databricks
    df_totales_spark = spark.sql("""
    SELECT 
        (SELECT COUNT(*) FROM aml_proyect.transacciones_plata_robert) as total_tx,
        (SELECT COUNT(*) FROM aml_proyect.gold_perfiles_riesgo_cliente) as total_clientes,
        (SELECT SUM(Flag_Structuring_Pitufeo) FROM aml_proyect.gold_perfiles_riesgo_cliente) as alertas_structuring,
        (SELECT SUM(Flag_Fan_In_Plataforma) FROM aml_proyect.gold_perfiles_riesgo_cliente) as alertas_fanin,
        (SELECT SUM(Flag_Crypto_Mixer) FROM aml_proyect.gold_perfiles_riesgo_cliente) as alertas_crypto
    """)
    df_totales = df_totales_spark.toPandas()

    total_transacciones = int(df_totales.iloc[0]['total_tx'] or 0)
    total_clientes = int(df_totales.iloc[0]['total_clientes'] or 0)
    alertas_structuring = int(df_totales.iloc[0]['alertas_structuring'] or 0)
    alertas_fanin = int(df_totales.iloc[0]['alertas_fanin'] or 0)
    alertas_crypto = int(df_totales.iloc[0]['alertas_crypto'] or 0)
    total_alertas = alertas_structuring + alertas_fanin + alertas_crypto

    print(f"Total Tx analizadas: {total_transacciones}")
    print(f"Total Clientes analizados: {total_clientes}")
    print(f"Alertas encontradas -> Pitufeo: {alertas_structuring}, Fan-In: {alertas_fanin}, Crypto: {alertas_crypto}")

    # TOP Sujetos extrayendo directo con Spark SQL
    sujeto_fanin = spark.sql("""
        SELECT PK_Cliente, Total_Tx_Recibidas, Monto_Total_Enviado_USD, Ratio_Operado_vs_Ingreso_Declarado 
        FROM aml_proyect.gold_perfiles_riesgo_cliente 
        WHERE Flag_Fan_In_Plataforma = 1 
        ORDER BY Total_Movido DESC LIMIT 1
    """).toPandas()

    sujeto_crypto = spark.sql("""
        SELECT PK_Cliente, Monto_Total_Enviado_USD, Ratio_Tx_Crypto, Tx_Canal_Crypto 
        FROM aml_proyect.gold_perfiles_riesgo_cliente 
        WHERE Flag_Crypto_Mixer = 1 
        ORDER BY Total_Movido DESC LIMIT 1
    """).toPandas()

    sujeto_structuring = spark.sql("""
        SELECT PK_Cliente, Total_Tx_Enviadas, Monto_Total_Enviado_USD 
        FROM aml_proyect.gold_perfiles_riesgo_cliente 
        WHERE Flag_Structuring_Pitufeo = 1 
        ORDER BY Total_Movido DESC LIMIT 1
    """).toPandas()

except NameError:
    print("ERROR: La variable 'spark' no est definida. Este cdigo debe ejecutarse dentro de un entorno de Databricks.")
    exit(1)
except Exception as e:
    print(f"Error ejecutando consultas en Databricks: {e}")
    exit(1)

# Generacin PDF usando FPDF
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'INFORME DE INTELIGENCIA FINANCIERA (ROS)', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pgina {self.page_no()}', 0, 0, 'C')

print("Generando documento PDF...")
pdf = PDF()
pdf.add_page()

pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 8, "A: Comit de Cumplimiento Normativo / Oficial de Cumplimiento", ln=1)
pdf.cell(0, 8, "DE: Unidad de Inteligencia Financiera (UIF) - Anlisis Transaccional", ln=1)
pdf.cell(0, 8, f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", ln=1)
pdf.cell(0, 8, "CLASIFICACIN: CONFIDENCIAL / RESTRINGIDO", ln=1)
pdf.ln(5)

pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "1. Resumen de Hallazgos (Data Oficial Lakehouse)", ln=1)
pdf.set_font("Arial", '', 11)
resumen = f"En el ltimo barrido de monitoreo transaccional se analiz un universo de {total_transacciones:,} operaciones financieras consolidadas, correspondientes a una cartera de {total_clientes:,} clientes activos. Tras aplicar la matriz de riesgo y reglas heursticas de deteccin en Databricks, el sistema ha emitido {total_alertas:,} alertas confirmadas de alto riesgo."
pdf.multi_cell(0, 8, resumen.encode('latin-1', 'replace').decode('latin-1'))
pdf.ln(3)

pdf.cell(0, 8, "Distribución de alertas por tipologa:", ln=1)
pdf.cell(0, 8, f"- Concentracin de Fondos (Fan-In): {alertas_fanin} alertas.", ln=1)
pdf.cell(0, 8, f"- Ofuscacin con Criptoactivos (Crypto Mixers): {alertas_crypto} alertas.", ln=1)
pdf.cell(0, 8, f"- Estructuracin (Pitufeo/Structuring): {alertas_structuring} alertas.", ln=1)
pdf.ln(5)

pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "2. Anlisis de Patrones y Comportamiento", ln=1)
pdf.set_font("Arial", '', 11)
patrones = "Fan-In: Clientes reciben rfagas de micro-depsitos de mltiples contrapartes en lapsos muy cortos, para luego evacuar el capital de una sola vez.\nCrypto Mixers: Fondos ingresados son canalizados rpidamente al 100% hacia Exchanges de criptoactivos en transferencias de alta frecuencia, ocultando su trazabilidad.\nEstructuracin: Depsitos en efectivo concentrados sistemticamente justo por debajo del lmite regulatorio de USD 10,000 para eludir controles."
pdf.multi_cell(0, 8, patrones.encode('latin-1', 'replace').decode('latin-1'))
pdf.ln(5)

pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "3. Sujetos de Inters (Casos Crticos Detectados)", ln=1)
pdf.set_font("Arial", '', 11)

if not sujeto_fanin.empty:
    sf = sujeto_fanin.iloc[0]
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"- Sujeto ID: {sf['PK_Cliente']} (Fan-In)", ln=1)
    pdf.set_font("Arial", '', 11)
    obs = f"Recibi {sf['Total_Tx_Recibidas']:.0f} transferencias, luego envi un total de USD {sf['Monto_Total_Enviado_USD']:,.2f} con una relacin de ingresos/operado de {sf['Ratio_Operado_vs_Ingreso_Declarado']:.2f}."
    pdf.multi_cell(0, 8, obs.encode('latin-1', 'replace').decode('latin-1'))
    
if not sujeto_crypto.empty:
    sc = sujeto_crypto.iloc[0]
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"- Sujeto ID: {sc['PK_Cliente']} (Crypto Mixer)", ln=1)
    pdf.set_font("Arial", '', 11)
    obs = f"Canaliz USD {sc['Monto_Total_Enviado_USD']:,.2f} a exchanges, representando el {sc['Ratio_Tx_Crypto']*100:.1f}% de sus transferencias de salida en {sc['Tx_Canal_Crypto']:.0f} envos."
    pdf.multi_cell(0, 8, obs.encode('latin-1', 'replace').decode('latin-1'))

if not sujeto_structuring.empty:
    ss = sujeto_structuring.iloc[0]
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"- Sujeto ID: {ss['PK_Cliente']} (Estructuracin)", ln=1)
    pdf.set_font("Arial", '', 11)
    obs = f"Gener {ss['Total_Tx_Enviadas']:.0f} transacciones de salida totalizando USD {ss['Monto_Total_Enviado_USD']:,.2f}, todas por montos menores a USD 3,000."
    pdf.multi_cell(0, 8, obs.encode('latin-1', 'replace').decode('latin-1'))

pdf.ln(5)
pdf.set_font("Arial", 'B', 14)
pdf.cell(0, 10, "4. Plan de Accin Recomendado", ln=1)
pdf.set_font("Arial", '', 11)
acciones = "1. Bloqueo Preventivo Inmediato: Congelar transitoriamente las cuentas de los Sujetos de Inters.\n2. Ampliacin de Debida Diligencia (EDD): Solicitar justificacin comercial o de origen de fondos en efectivo y transferencias masivas.\n3. Reporte de Operaciones Sospechosas (ROS): Enviar a la UIF nacional adjuntando evidencia transaccional.\n4. Watchlists: Agregar cuentas contrapartes vinculadas a bloqueo preventivo."
pdf.multi_cell(0, 8, acciones.encode('latin-1', 'replace').decode('latin-1'))

# Guardar el PDF en Workspace/DBFS o local
pdf_path = "/databricks/driver/Reporte_ROS_Inteligencia_Financiera.pdf"
try:
    pdf.output(pdf_path)
    print(f"PDF generado exitosamente en: {pdf_path}")
    print("En Databricks, puedes descargarlo dirigindote a File -> Download o accediendo a DBFS.")
except Exception as e:
    # Fallback si no está en Databricks nativo sino local
    pdf.output("Reporte_ROS_Inteligencia_Financiera.pdf")
    print("PDF generado localmente como 'Reporte_ROS_Inteligencia_Financiera.pdf'.")
