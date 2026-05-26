import asyncio
from datetime import datetime

class Scheduler:
    """Ejecuta una tarea asincrona de forma periodica.

    Esta clase sirve para correr un scraper u otra funcion ``async`` cada cierto
    numero de horas. Mantiene una bandera interna para saber si el ciclo debe
    seguir ejecutandose.
    """

    def __init__(self, intervalo_horas: int = 24):
        """Crea un scheduler con un intervalo fijo.

        Args:
            intervalo_horas: Cantidad de horas que se esperaran entre una
                ejecucion y la siguiente.

        Attributes:
            intervalo_horas: Intervalo configurado en horas.
            corriendo: Indica si el ciclo periodico esta activo.
        """
        self.intervalo_horas = intervalo_horas
        self.corriendo = False

    async def iniciar(self, tarea):
        """Inicia el ciclo periodico de ejecucion.

        La funcion recibida se ejecuta inmediatamente y despues vuelve a
        ejecutarse cada ``intervalo_horas``. Si la tarea falla, el error se
        imprime en consola y el scheduler continua con la siguiente vuelta.

        Args:
            tarea: Funcion asincrona sin argumentos que se desea ejecutar de
                manera periodica. Ejemplo: ``scheduler.iniciar(scraper.ejecutar)``.

        Returns:
            None. El metodo permanece en ejecucion hasta que ``detener`` cambie
            la bandera ``corriendo`` a ``False``.

        Side Effects:
            Imprime mensajes en consola y ejecuta la tarea recibida.
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
        """Detiene el ciclo periodico en la siguiente revision del bucle.

        Cambia la bandera ``corriendo`` a ``False``. Si ``iniciar`` esta
        esperando dentro de ``asyncio.sleep``, la detencion se reflejara cuando
        termine esa espera y el bucle vuelva a evaluar la condicion.

        Returns:
            None.
        """
        self.corriendo = False
        print("Scheduler detenido")
