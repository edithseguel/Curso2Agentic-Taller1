"""Ficha A2A y servidor del agente de cotizaciones de desarrollo TI."""

import os

from dotenv import load_dotenv

from src.comun.servidor import crear_app
from src.comun.tarjeta import crear_tarjeta

from .graph import responder


load_dotenv()

URL_CRISTIAN_DESARROLLO_TI = os.getenv(
    "URL_CRISTIAN_DESARROLLO_TI",
    os.getenv("URL_DESARROLLO", "http://127.0.0.1:8002"),
)

tarjeta = crear_tarjeta(
    "Agente de Cristian_desarrollo_ti",
    "Prepara cotizaciones simples de desarrollo de sistemas según requerimiento, horas y valor por hora. No desarrolla ni implementa sistemas ni aprueba cotizaciones.",
    URL_CRISTIAN_DESARROLLO_TI,
    [
        (
            "planeacion",
            "Planeación orientativa",
            "Distribuye las horas entre análisis, desarrollo y pruebas.",
            "Distribuye 100 horas para un sistema de inventario.",
        ),
        (
            "cotizacion",
            "Cotización en UF",
            "Calcula el desglose y total usando el valor hora configurado.",
            "Cotiza un desarrollo de 100 horas.",
        ),
    ],
)

app = crear_app(tarjeta, responder)
