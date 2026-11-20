"""Ficha A2A y servidor del agente de cotizaciones de minería de datos."""

import os

from dotenv import load_dotenv

from src.comun.servidor import crear_app
from src.comun.tarjeta import crear_tarjeta

from .graph import responder


load_dotenv()
URL_RODRIGO_MINERIA_DE_DATOS = os.getenv(
    "URL_RODRIGO_MINERIA_DE_DATOS",
    os.getenv("URL_MINERIA", "http://127.0.0.1:8003"),
)

tarjeta = crear_tarjeta(
    "Agente de Rodrigo_mineria_de_datos",
    "Prepara cotizaciones simples de servicios de minería de datos según requerimiento, horas y valor por hora, considerando análisis de requisitos, recopilación y preprocesamiento, modelado, evaluación y conclusiones. No ejecuta análisis ni modelos ni aprueba cotizaciones.",
    URL_RODRIGO_MINERIA_DE_DATOS,
    [
        (
            "planificacion_mineria",
            "Planificación de minería de datos",
            "Distribuye las horas entre las cuatro etapas obligatorias.",
            "Distribuye 100 horas para un servicio de minería de datos.",
        ),
        (
            "cotizacion_mineria",
            "Cotización de minería de datos",
            "Calcula el subtotal por etapa y el total en UF usando el valor hora configurado.",
            "Cotiza un servicio de minería de datos de 100 horas.",
        ),
    ],
)

app = crear_app(tarjeta, responder)
