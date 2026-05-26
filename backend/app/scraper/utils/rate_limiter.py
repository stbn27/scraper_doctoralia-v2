from datetime import datetime
from collections import deque
import asyncio


class RateLimiter:
    """Controla cuantas solicitudes se permiten en una ventana de tiempo.

    La clase guarda un historial de fechas recientes. Antes de permitir una
    nueva solicitud, elimina entradas antiguas y verifica si ya se alcanzo el
    maximo configurado. Si el limite ya se alcanzo, espera el tiempo necesario.
    """

    def __init__(self, max_requests: int = 10, ventana_segundos: int = 60):
        """Inicializa el limitador de solicitudes.

        Args:
            max_requests: Cantidad maxima de solicitudes permitidas dentro de
                una ventana.
            ventana_segundos: Duracion de la ventana de tiempo en segundos.

        Attributes:
            max_requests: Limite de solicitudes configurado.
            ventana: Duracion de la ventana en segundos.
            historial: Cola con las fechas de las solicitudes recientes.
        """
        self.max_requests = max_requests
        self.ventana = ventana_segundos
        self.historial = deque()

    async def esperar_si_necesario(self):
        """Espera si ya se alcanzo el limite de solicitudes.

        Debe llamarse justo antes de hacer una peticion. Si el historial indica
        que todavia hay demasiadas solicitudes dentro de la ventana actual, la
        funcion pausa la ejecucion usando ``asyncio.sleep``. Al final registra
        la nueva solicitud en el historial.

        Returns:
            None. La funcion solo retrasa la ejecucion cuando hace falta.

        Side Effects:
            Puede imprimir un mensaje en consola y modificar ``historial``.
        """
        ahora = datetime.now()
        while self.historial and (ahora - self.historial[0]).seconds > self.ventana:
            self.historial.popleft()

        if len(self.historial) >= self.max_requests:
            espera = self.ventana - (ahora - self.historial[0]).seconds
            print(f"Rate limit alcanzado, esperando {espera}s...")
            await asyncio.sleep(espera)

        self.historial.append(datetime.now())
