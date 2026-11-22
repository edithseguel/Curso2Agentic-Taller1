"""Base de conocimiento para cotizaciones de desarrollo TI."""

ETAPAS_BASE = (
    ("Análisis", 40),
    ("Desarrollo", 120),
    ("Pruebas", 40),
)
TARIFA_REFERENCIAL_UF_HORA = 2.0


def total_horas_base() -> int:
    """Devuelve el total de horas de la propuesta estándar."""
    return sum(horas for _, horas in ETAPAS_BASE)
