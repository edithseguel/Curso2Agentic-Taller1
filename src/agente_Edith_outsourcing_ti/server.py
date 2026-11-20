"""Ficha A2A y servidor común del agente de Edith."""

import os

from dotenv import load_dotenv

from src.comun.servidor import crear_app
from src.comun.tarjeta import crear_tarjeta

from .crew import responder


load_dotenv()
URL_EDITH_OUTSOURCING_TI = os.getenv(
    "URL_EDITH_OUTSOURCING_TI",
    os.getenv("URL_OUTSOURCING", "http://127.0.0.1:8001"),
)

tarjeta = crear_tarjeta(
    "Agente de Edith_outsourcing_ti",
    "Prepara cotizaciones simples de outsourcing de recursos humanos TI según perfil, cantidad y período; calcula la tarifa mensual desde el valor hora del perfil configurado en .env. No selecciona ni contrata personas.",
    URL_EDITH_OUTSOURCING_TI,
    [
        (
            "catalogo_perfiles",
            "Catálogo de perfiles TI",
            "Devuelve los perfiles TI disponibles para outsourcing.",
            "¿Qué perfiles TI están disponibles?",
        ),
        (
            "cotizador",
            "Cotización de outsourcing TI",
            "Calcula subtotal y total usando el valor hora UF del perfil en .env y una tarifa mensual igual a valor hora × 120.",
            "Cotiza 2 desarrolladores Full Stack por 6 meses.",
        ),
    ],
)

app = crear_app(tarjeta, responder)
