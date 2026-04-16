import asyncio
from datetime import datetime

class Scheduler:
    """Ejecuta el scraper periódicamente según intervalo configurado."""

    def __init__(self, intervalo_horas: int = 24):
        self.intervalo_horas = intervalo_horas
        self.corriendo = False

    async def iniciar(self, tarea):
        """
        tarea: función async a ejecutar periódicamente
        Ejemplo: scheduler.iniciar(scraper.ejecutar)
        """
        self.corriendo = True
        print(f"Scheduler iniciado — ejecutando cada {self.intervalo_horas}h")

        while self.corriendo:
            inicio = datetime.now()
            print(f"[{inicio.strftime('%Y-%m-%d %H:%M')}] Iniciando scraping...")

            try:
                await tarea()
            except Exception as e:
                print(f"Error en tarea programada: {e}")

            print(f"Scraping completado. Próxima ejecución en {self.intervalo_horas}h")
            await asyncio.sleep(self.intervalo_horas * 3600)

    def detener(self):
        self.corriendo = False
        print("Scheduler detenido")
