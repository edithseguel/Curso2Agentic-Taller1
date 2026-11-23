"""Herramientas de Edith para cotizar outsourcing de recursos humanos TI."""

from crewai.tools import tool

from .conocimiento import TARIFAS_MENSUALES_UF


PERFILES = (
    "Programador/Desarrollador",
    "Desarrollador Full Stack",
    "Administrador de Base de Datos (DBA)",
    "Desarrollador Java/.NET",
    "Analista QA/Testing",
    "Analista de Sistemas/BI",
    "Otro perfil",
)


def _numero_positivo(valor: object) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and valor > 0


@tool
def catalogo_perfiles() -> str:
    """Devuelve los perfiles TI disponibles para outsourcing."""
    return "Perfiles TI disponibles: " + "; ".join(PERFILES) + "."


@tool
def cotizador(
    perfil: str,
    cantidad: int,
    meses: int,
    tarifa_mensual: float | None = None,
) -> str:
    """Calcula la cotización usando la tarifa base definida para el perfil."""
    if not perfil or not perfil.strip():
        return "Falta el perfil TI requerido; acláralo antes de cotizar."
    perfil_limpio = perfil.strip()
    if perfil_limpio.casefold() not in {nombre.casefold() for nombre in PERFILES}:
        return "El perfil no está en el catálogo; aclara uno de los perfiles disponibles."
    if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
        return "Falta una cantidad de personas entera y positiva; aclárala antes de cotizar."
    if not isinstance(meses, int) or isinstance(meses, bool) or meses <= 0:
        return "Falta un período en meses entero y positivo; acláralo antes de cotizar."

    nombre_perfil = next(
        nombre for nombre in PERFILES if nombre.casefold() == perfil_limpio.casefold()
    )
    tarifa_mensual_calculada = TARIFAS_MENSUALES_UF[nombre_perfil]
    subtotal = cantidad * tarifa_mensual_calculada
    total = subtotal * meses
    return (
        f"Cotización para {cantidad} persona(s) de {nombre_perfil} durante {meses} mes(es): "
        f"tarifa mensual referencial {tarifa_mensual_calculada:.2f} UF por persona; "
        f"subtotal mensual {subtotal:.2f} UF; total del período {total:.2f} UF."
    )
