"""Herramientas para preparar cotizaciones de minería de datos."""

from langchain_core.tools import tool

from .conocimiento import ETAPAS_BASE, TARIFA_REFERENCIAL_UF_HORA, total_horas_base


def _meses_validos(meses: int) -> bool:
    """Comprueba que el plazo sea un número entero y positivo."""
    return isinstance(meses, int) and not isinstance(meses, bool) and meses > 0


@tool
def planificador(requerimiento: str) -> str:
    """Devuelve las etapas y horas base de minería de datos."""
    if not requerimiento or not requerimiento.strip():
        return "Falta el requerimiento del cliente; acláralo antes de distribuir las horas."
    detalle = "; ".join(f"{etapa}: {horas} horas" for etapa, horas in ETAPAS_BASE)
    return f"Distribución base para el requerimiento indicado: {detalle}; total: {total_horas_base()} horas."


@tool
def cotizador(meses: int = 1) -> str:
    """Calcula subtotales mensuales y total para el plazo indicado."""
    if not _meses_validos(meses):
        return "El plazo debe ser una cantidad de meses entera y positiva."
    tarifa = TARIFA_REFERENCIAL_UF_HORA
    subtotales = "; ".join(
        f"{etapa}: {horas_etapa} horas × {tarifa:.2f} UF = {horas_etapa * tarifa:.2f} UF"
        for etapa, horas_etapa in ETAPAS_BASE
    )
    total_mensual = total_horas_base() * tarifa
    total = total_mensual * meses
    return (
        f"{subtotales}; total mensual: {total_mensual:.2f} UF; "
        f"plazo: {meses} mes(es); total estimado del período: {total:.2f} UF."
    )
