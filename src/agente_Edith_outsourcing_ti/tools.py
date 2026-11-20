"""Herramientas de Edith para cotizar outsourcing de recursos humanos TI."""

import os

from crewai.tools import tool
from dotenv import load_dotenv


load_dotenv()


PERFILES = (
    "Programador/Desarrollador",
    "Desarrollador Full Stack",
    "Administrador de Base de Datos (DBA)",
    "Desarrollador Java/.NET",
    "Analista QA/Testing",
    "Analista de Sistemas/BI",
)

VARIABLES_TARIFA = {
    "Programador/Desarrollador": "vh_perf_prog",
    "Desarrollador Full Stack": "vh_perf_progfs",
    "Administrador de Base de Datos (DBA)": "vh_perf_dba",
    "Desarrollador Java/.NET": "vh_perf_prognet",
    "Analista QA/Testing": "vh_perf_qa",
    "Analista de Sistemas/BI": "vh_perf_analis",
}


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
    """Calcula la cotización usando la tarifa del perfil definida en .env.

    ``tarifa_mensual`` se conserva solo por compatibilidad con conversaciones
    anteriores, pero nunca se usa: la fuente válida es .env.
    """
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
    variable = VARIABLES_TARIFA[nombre_perfil]
    valor_hora_texto = os.getenv(variable, "").strip()
    if not valor_hora_texto:
        return f"Falta la tarifa horaria UF del perfil en la variable {variable} del archivo .env."
    try:
        valor_hora = float(valor_hora_texto.replace(",", "."))
    except ValueError:
        return f"La variable {variable} no contiene una tarifa horaria UF válida."
    if not _numero_positivo(valor_hora):
        return f"La variable {variable} debe contener una tarifa horaria UF positiva."

    tarifa_mensual_calculada = valor_hora * 120
    subtotal = cantidad * tarifa_mensual_calculada
    total = subtotal * meses
    return (
        f"Cotización para {cantidad} persona(s) de {nombre_perfil} durante {meses} mes(es): "
        f"valor hora {valor_hora:.2f} UF; tarifa mensual calculada "
        f"({valor_hora:.2f} × 120) {tarifa_mensual_calculada:.2f} UF; "
        f"subtotal mensual {subtotal:.2f} UF; total del período {total:.2f} UF."
    )
