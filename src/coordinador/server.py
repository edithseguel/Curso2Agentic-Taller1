"""Ficha A2A y servidor HTTP del coordinador."""

import os

from dotenv import load_dotenv

from src.comun.servidor import crear_app
from src.comun.tarjeta import crear_tarjeta

from .graph import responder


load_dotenv()
URL_COORDINADOR = os.getenv("URL_COORDINADOR", "http://127.0.0.1:8004")

tarjeta = crear_tarjeta(
    "Coordinador",
    "Enruta cada pregunta al agente A2A especializado y repite su respuesta.",
    URL_COORDINADOR,
    [
        (
            "enrutamiento",
            "Enrutamiento de consultas",
            "Deriva una consulta al agente especializado correspondiente.",
            "Cotiza 100 horas de outsourcing TI.",
        )
    ],
)

app = crear_app(tarjeta, responder)
