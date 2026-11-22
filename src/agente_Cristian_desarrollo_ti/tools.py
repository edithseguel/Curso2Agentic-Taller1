"""Herramientas para preparar cotizaciones de desarrollo de sistemas."""

from langchain_core.tools import tool

from .conocimiento import ETAPAS_BASE, TARIFA_REFERENCIAL_UF_HORA, total_horas_base


def _meses_validos(meses: int) -> bool:
    """Comprueba que el plazo sea un número entero y positivo."""
    return isinstance(meses, int) and not isinstance(meses, bool) and meses > 0


@tool
def planeador(requerimiento: str) -> str:
    """Devuelve las etapas y horas base de la propuesta de desarrollo."""
    if not requerimiento or not requerimiento.strip():
        return "Falta el requerimiento del cliente; no puedo planear sin ese dato."
    detalle = "; ".join(f"{etapa}: {horas} horas" for etapa, horas in ETAPAS_BASE)
    return (
        f"Distribución base para el requerimiento indicado: {detalle}; "
        f"total: {total_horas_base()} horas."
    )


@tool
def cotizador(meses: int = 1) -> str:
    """Calcula la propuesta base mensual y total para el plazo indicado."""
    if not _meses_validos(meses):
        return "El plazo debe ser una cantidad de meses entera y positiva."
    horas = total_horas_base()
    tarifa = TARIFA_REFERENCIAL_UF_HORA
    total_mensual = horas * tarifa
    total = total_mensual * meses
    return (
        f"Desglose base mensual: {horas} horas × {tarifa:.2f} UF por hora = "
        f"{total_mensual:.2f} UF. "
        f"Plazo: {meses} mes(es). Total estimado del período: {total:.2f} UF."
    )
