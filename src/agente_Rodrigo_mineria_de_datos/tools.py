"""Herramientas para preparar cotizaciones de minería de datos."""

import os

from dotenv import load_dotenv
from langchain_core.tools import tool


load_dotenv()

ETAPAS = (
    ("análisis de requisitos", 0.20),
    ("recopilación y preprocesamiento", 0.30),
    ("modelado", 0.30),
    ("evaluación y conclusiones", 0.20),
)


def _horas_validas(horas: float) -> bool:
    """Comprueba que las horas sean un número positivo."""
    return isinstance(horas, (int, float)) and not isinstance(horas, bool) and horas > 0


def _tarifa() -> tuple[float | None, str | None]:
    """Obtiene y valida el valor hora configurado en el entorno."""
    valor = os.getenv("vhorahom", "").strip()
    if not valor:
        return None, "Falta la variable vhorahom en el archivo .env; no puedo inventar la tarifa."
    try:
        tarifa = float(valor.replace(",", "."))
    except ValueError:
        return None, "La variable vhorahom no contiene una tarifa numérica válida."
    if tarifa <= 0:
        return None, "La variable vhorahom debe contener una tarifa positiva."
    return tarifa, None


@tool
def planificador(requerimiento: str, horas: float) -> str:
    """Distribuye orientativamente las horas entre las cuatro etapas obligatorias."""
    if not requerimiento or not requerimiento.strip():
        return "Falta el requerimiento del cliente; acláralo antes de distribuir las horas."
    if not _horas_validas(horas):
        return "Faltan horas válidas y positivas; no puedo inventar una estimación."

    distribucion = [(etapa, round(horas * proporcion, 2)) for etapa, proporcion in ETAPAS]
    diferencia = round(horas - sum(valor for _, valor in distribucion), 2)
    distribucion[-1] = (distribucion[-1][0], round(distribucion[-1][1] + diferencia, 2))
    detalle = "; ".join(f"{etapa}: {valor:g} horas" for etapa, valor in distribucion)
    return f"Distribución orientativa para el requerimiento indicado: {detalle}; total: {horas:g} horas."


@tool
def cotizador(horas: float) -> str:
    """Calcula el subtotal de cada etapa y el total de la cotización en UF."""
    if not _horas_validas(horas):
        return "Faltan horas válidas y positivas; acláralas antes de calcular la cotización."

    tarifa, error = _tarifa()
    if error:
        return error
    assert tarifa is not None

    distribucion = [(etapa, round(horas * proporcion, 2)) for etapa, proporcion in ETAPAS]
    diferencia = round(horas - sum(valor for _, valor in distribucion), 2)
    distribucion[-1] = (distribucion[-1][0], round(distribucion[-1][1] + diferencia, 2))
    subtotales = "; ".join(
        f"{etapa}: {horas_etapa:g} horas × {tarifa:.2f} UF = {horas_etapa * tarifa:.2f} UF"
        for etapa, horas_etapa in distribucion
    )
    total = horas * tarifa
    return f"{subtotales}; total: {total:.2f} UF."
