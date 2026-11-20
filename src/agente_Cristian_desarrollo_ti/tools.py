"""Herramientas para preparar cotizaciones de desarrollo de sistemas."""

import os

from dotenv import load_dotenv
from langchain_core.tools import tool


load_dotenv()


def _horas_validas(horas: float) -> bool:
    """Comprueba que las horas sean un número positivo."""
    return isinstance(horas, (int, float)) and horas > 0


@tool
def planeador(requerimiento: str, horas: float) -> str:
    """Distribuye las horas disponibles entre análisis, desarrollo y pruebas."""
    if not requerimiento or not requerimiento.strip():
        return "Falta el requerimiento del cliente; no puedo planear sin ese dato."
    if not _horas_validas(horas):
        return "Faltan horas válidas y positivas; no puedo inventar una estimación."

    analisis = round(horas * 0.20, 2)
    desarrollo = round(horas * 0.60, 2)
    pruebas = round(horas - analisis - desarrollo, 2)
    return (
        "Distribución orientativa para el requerimiento indicado "
        "(20% análisis, 60% desarrollo y 20% pruebas): "
        f"análisis: {analisis:g} horas; desarrollo: {desarrollo:g} horas; "
        f"pruebas: {pruebas:g} horas; total: {horas:g} horas."
    )


@tool
def cotizador(horas: float) -> str:
    """Calcula el desglose y total de una cotización en UF."""
    if not _horas_validas(horas):
        return "Faltan horas válidas y positivas; no puedo calcular la cotización."

    valor_hora = os.getenv("vhorahom", "").strip()
    if not valor_hora:
        return "Falta la variable vhorahom en el archivo .env; no puedo inventar la tarifa."
    try:
        tarifa = float(valor_hora.replace(",", "."))
    except ValueError:
        return "La variable vhorahom no contiene una tarifa numérica válida."
    if tarifa <= 0:
        return "La variable vhorahom debe contener una tarifa positiva."

    total = horas * tarifa
    return (
        f"Desglose: {horas:g} horas × {tarifa:.2f} UF por hora = "
        f"{total:.2f} UF. Total estimado: {total:.2f} UF."
    )
