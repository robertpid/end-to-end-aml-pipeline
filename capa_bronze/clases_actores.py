import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from config import UMBRAL_ALERTA, TASAS_CAMBIO

class PerfilFinanciero:
    """
    Clase base para todos los perfiles financieros en la simulación.
    """
    def __init__(self):
        self.pk_cliente = str(uuid.uuid4())
        self.edad = random.randint(18, 70)
        self.ocupacion_declarada = "Sin Declarar"
        self.ingreso_mensual_aprox = 0.0

    def obtener_dim_cliente(self) -> dict:
        """
        Retorna la información del cliente para la Dim_Cliente.
        """
        return {
            "PK_Cliente": self.pk_cliente,
            "Edad": self.edad,
            "Ocupacion_Declarada": self.ocupacion_declarada,
            "Ingreso_Mensual_Aprox": round(self.ingreso_mensual_aprox, 2)
        }

    def generar_transacciones(self, fecha_inicio: datetime) -> List[dict]:
        """
        Genera la lista de transacciones realizadas por el perfil.
        Debe ser implementada por las clases derivadas.
        """
        raise NotImplementedError("Este método debe ser sobrescrito por clases derivadas.")

    def _crear_transaccion(self, fk_origen: str, fk_destino: str, fecha: datetime, 
                           canal: str, geografia: str, monto: float) -> dict:
        """
        Método de apoyo para construir el diccionario de la transacción.
        """
        moneda = random.choice(list(TASAS_CAMBIO.keys()))
        tasa = TASAS_CAMBIO[moneda]
        monto_original = monto * tasa

        return {
            "PK_Transaccion": str(uuid.uuid4()),
            "FK_Cliente_Origen": fk_origen,
            "FK_Cliente_Destino": fk_destino,
            "FK_Tiempo": fecha.strftime("%Y-%m-%d %H:%M:%S"),
            "FK_Canal": canal,
            "FK_Geografia": geografia,
            "Monto_Original": round(monto_original, 2),
            "Moneda": moneda,
            "Monto_USD": round(monto, 2)
        }

    def _generar_fecha_legitima(self, fecha_base: datetime, es_salario: bool = False) -> Tuple[datetime, bool]:
        """
        Genera una fecha realista. Si es salario, fuerza día 15, 30 o 31.
        El 70% de las transacciones ocurren en horario de oficina (9am - 7pm).
        Retorna la fecha y un booleano indicando si es fin de semana.
        """
        if es_salario:
            dias_quincena = []
            for i in range(60):
                d = fecha_base + timedelta(days=i)
                if d.day in [15, 30, 31]:
                    dias_quincena.append(d)
            if not dias_quincena:
                dias_quincena = [fecha_base + timedelta(days=15)]
            fecha = random.choice(dias_quincena)
        else:
            fecha = fecha_base + timedelta(days=random.randint(0, 59))
        
        # Horario: 70% oficina (09:00 - 19:00), 30% fuera
        es_oficina = random.random() < 0.70
        if es_oficina:
            hora = random.randint(9, 18)
        else:
            horas_fuera = list(range(0, 9)) + list(range(19, 24))
            hora = random.choice(horas_fuera)
            
        fecha = fecha.replace(hour=hora, minute=random.randint(0, 59), second=random.randint(0, 59))
        es_fin_semana = fecha.weekday() >= 5
        return fecha, es_fin_semana

    def _generar_fecha_sospechosa(self, fecha_base: datetime, rafaga_anterior: datetime = None) -> datetime:
        """
        Genera fechas en horarios atípicos (01:00 AM - 05:00 AM) o ráfagas (pocos segundos después de la anterior).
        """
        if rafaga_anterior:
            return rafaga_anterior + timedelta(seconds=random.randint(0, 59))
        
        fecha = fecha_base + timedelta(days=random.randint(0, 59))
        fecha = fecha.replace(
            hour=random.randint(1, 5), 
            minute=random.randint(0, 59), 
            second=random.randint(0, 59)
        )
        return fecha


class ClienteNormal(PerfilFinanciero):
    """
    Simula el ruido de fondo legítimo. Recibe su salario y realiza múltiples gastos.
    """
    def __init__(self):
        super().__init__()
        self.ocupacion_declarada = random.choice(["Ingeniero", "Profesor", "Médico", "Comerciante", "Administrativo"])
        self.ingreso_mensual_aprox = random.uniform(1500, 5000)

    def generar_transacciones(self, fecha_inicio: datetime) -> List[dict]:
        transacciones = []
        
        # 1. Ingreso del Salario
        empresa_uuid = str(uuid.uuid4())
        fecha_salario, _ = self._generar_fecha_legitima(fecha_inicio, es_salario=True)
        t_salario = self._crear_transaccion(
            fk_origen=empresa_uuid,
            fk_destino=self.pk_cliente,
            fecha=fecha_salario,
            canal="Transferencia_Bancaria",
            geografia="Local",
            monto=self.ingreso_mensual_aprox
        )
        transacciones.append(t_salario)

        # 2. Transacciones de egreso (Compras)
        num_compras = random.randint(10, 30)
        for _ in range(num_compras):
            fecha_compra, es_fin_semana = self._generar_fecha_legitima(fecha_inicio, es_salario=False)
            
            if es_fin_semana:
                monto_compra = random.uniform(5, 50)
            else:
                monto_compra = random.uniform(10, 200)
                
            comercio_uuid = str(uuid.uuid4())
            t_compra = self._crear_transaccion(
                fk_origen=self.pk_cliente,
                fk_destino=comercio_uuid,
                fecha=fecha_compra,
                canal="Tarjeta_Credito",
                geografia="Local",
                monto=monto_compra
            )
            transacciones.append(t_compra)
            
        return transacciones


class PitufoBancario(PerfilFinanciero):
    """
    Simula estructuración de efectivo (Structuring).
    """
    def __init__(self):
        super().__init__()
        self.ocupacion_declarada = "Comerciante_Independiente"
        self.ingreso_mensual_aprox = random.uniform(1500, 3000)

    def generar_transacciones(self, fecha_inicio: datetime) -> List[dict]:
        transacciones = []
        
        num_transacciones = random.randint(3, 5)
        montos = []
        while True:
            montos = [random.uniform(2500.0, 9500.0) for _ in range(num_transacciones)]
            if sum(montos) > 10000.0:
                break
                
        # Elegir día de camuflaje (1, 15, 30, 31)
        dias_camuflaje = []
        for i in range(60):
            d = fecha_inicio + timedelta(days=i)
            if d.day in [1, 15, 30, 31]:
                dias_camuflaje.append(d)
        if not dias_camuflaje:
            dias_camuflaje = [fecha_inicio + timedelta(days=15)]
        fecha_base = random.choice(dias_camuflaje)
        
        # Generar horas pico comerciales
        fechas_transacciones = []
        for _ in range(num_transacciones):
            # Horario pico: 12:00 PM - 02:00 PM (12 a 13) o 05:00 PM - 07:00 PM (17 a 18)
            hora = random.randint(12, 13) if random.random() < 0.5 else random.randint(17, 18)
            fecha_tx = fecha_base.replace(hour=hora, minute=random.randint(0, 59), second=random.randint(0, 59))
            fechas_transacciones.append(fecha_tx)
            
        fechas_transacciones.sort()
        
        for fecha_actual, monto in zip(fechas_transacciones, montos):
            t_deposito = self._crear_transaccion(
                fk_origen=self.pk_cliente,
                fk_destino=self.pk_cliente, 
                fecha=fecha_actual,
                canal="Deposito_Efectivo",
                geografia="Cajero_Automatico",
                monto=monto
            )
            transacciones.append(t_deposito)
            
        return transacciones


class LavadorPlataformas(PerfilFinanciero):
    """
    Simula ingresos por propinas y retiros controlados (Creator Economy).
    """
    def __init__(self):
        super().__init__()
        self.ocupacion_declarada = "Creador_de_Contenido"
        self.ingreso_mensual_aprox = random.uniform(500, 1000)

    def generar_transacciones(self, fecha_inicio: datetime) -> List[dict]:
        transacciones = []
        
        num_ingresos = random.randint(100, 200)
        monto_total_acumulado = 0.0
        fecha_actual = None
        
        for _ in range(num_ingresos):
            fecha_actual = self._generar_fecha_sospechosa(fecha_inicio, rafaga_anterior=fecha_actual)
            
            monto_tip = random.uniform(50, 200)
            monto_total_acumulado += monto_tip
            origen_tip_uuid = str(uuid.uuid4())
            t_tip = self._crear_transaccion(
                fk_origen=origen_tip_uuid,
                fk_destino=self.pk_cliente,
                fecha=fecha_actual,
                canal="Plataforma_Terceros",
                geografia="Internacional",
                monto=monto_tip
            )
            transacciones.append(t_tip)
            
        # Retiro
        monto_retiro = monto_total_acumulado * random.uniform(0.90, 0.95)
        monto_retiro = min(monto_retiro, UMBRAL_ALERTA - 1.0)
        
        fecha_retiro = self._generar_fecha_sospechosa(fecha_inicio, rafaga_anterior=fecha_actual)
        t_retiro = self._crear_transaccion(
            fk_origen=self.pk_cliente,
            fk_destino=str(uuid.uuid4()),
            fecha=fecha_retiro,
            canal="Transferencia_Bancaria",
            geografia="Local",
            monto=monto_retiro
        )
        transacciones.append(t_retiro)
        
        return transacciones


class LavadorCrypto(PerfilFinanciero):
    """
    Simula saltos en blockchain hacia un Exchange (KYT).
    """
    def __init__(self):
        super().__init__()
        self.ocupacion_declarada = "Inversionista"
        self.ingreso_mensual_aprox = random.uniform(2000, 5000)
        self.bridge_wallet_id = self.pk_cliente

    def generar_transacciones(self, fecha_inicio: datetime) -> List[dict]:
        transacciones = []
        
        num_ingresos = random.randint(5, 10)
        monto_total = 0.0
        fecha_actual = None
        
        for _ in range(num_ingresos):
            fecha_actual = self._generar_fecha_sospechosa(fecha_inicio, rafaga_anterior=fecha_actual)
            monto_ingreso = random.uniform(500, 2000)
            monto_total += monto_ingreso
            origen_uuid = str(uuid.uuid4())
            t_ingreso = self._crear_transaccion(
                fk_origen=origen_uuid,
                fk_destino=self.bridge_wallet_id,
                fecha=fecha_actual,
                canal="Crypto_Wallet",
                geografia="Internacional",
                monto=monto_ingreso
            )
            transacciones.append(t_ingreso)
            
        monto_restante = monto_total
        exchange_uuid = str(uuid.uuid4())
        
        while monto_restante > 0:
            fecha_salida = self._generar_fecha_sospechosa(fecha_inicio, rafaga_anterior=fecha_actual)
            fecha_actual = fecha_salida
            monto_salida = min(monto_restante, random.uniform(1000, 2500))
            monto_restante -= monto_salida
            
            t_salida = self._crear_transaccion(
                fk_origen=self.bridge_wallet_id,
                fk_destino=exchange_uuid,
                fecha=fecha_salida,
                canal="Exchange_Crypto",
                geografia="Internacional",
                monto=monto_salida
            )
            transacciones.append(t_salida)
            
        return transacciones
