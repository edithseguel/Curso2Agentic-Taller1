"""Construcción de fichas Agent Card para los agentes A2A."""

from collections.abc import Sequence

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


def crear_tarjeta(
    nombre: str,
    descripcion: str,
    url: str,
    skills: Sequence[tuple[str, str, str, str]],
) -> AgentCard:
    """Devuelve una ficha A2A con entrada y salida de texto."""
    habilidades = [
        AgentSkill(
            id=identificador,
            name=nombre_habilidad,
            description=descripcion_habilidad,
            tags=[identificador],
            examples=[ejemplo],
            input_modes=["text"],
            output_modes=["text"],
        )
        for identificador, nombre_habilidad, descripcion_habilidad, ejemplo in skills
    ]

    return AgentCard(
        name=nombre,
        description=descripcion,
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url=url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=habilidades,
    )
