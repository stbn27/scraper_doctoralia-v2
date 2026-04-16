from datetime import datetime
from collections import deque
import asyncio


class RateLimiter:
    """Máximo N requests por ventana de tiempo."""

    def __init__(self, max_requests: int = 10, ventana_segundos: int = 60):
        self.max_requests = max_requests
        self.ventana = ventana_segundos
        self.historial = deque()

    async def esperar_si_necesario(self):
        ahora = datetime.now()
        while self.historial and (ahora - self.historial[0]).seconds > self.ventana:
            self.historial.popleft()

        if len(self.historial) >= self.max_requests:
            espera = self.ventana - (ahora - self.historial[0]).seconds
            print(f"Rate limit alcanzado, esperando {espera}s...")
            await asyncio.sleep(espera)

        self.historial.append(datetime.now())
