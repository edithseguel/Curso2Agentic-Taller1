"""Base de conocimiento para cotizaciones de minería de datos."""

ETAPAS_BASE = (
    ("Análisis de requisitos", 32),
    ("Recopilación y preprocesamiento", 48),
    ("Modelado", 48),
    ("Evaluación y conclusiones", 32),
)
TARIFA_REFERENCIAL_UF_HORA = 2.0


def total_horas_base() -> int:
    """Devuelve el total de horas de la propuesta estándar."""
    return sum(horas for _, horas in ETAPAS_BASE)
