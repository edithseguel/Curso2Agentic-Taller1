"""Grafo LangGraph que clasifica las consultas de cotizaciones."""

import asyncio
import os
import re
from collections.abc import Awaitable, Callable
from operator import add
from typing import Annotated, Literal
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.agente_Cristian_desarrollo_ti.graph import responder as responder_cristian
from src.agente_Edith_outsourcing_ti.crew import responder as responder_edith
from src.agente_Rodrigo_mineria_de_datos.graph import responder as responder_rodrigo

from .prompts import (
    PROMPT_COORDINADOR,
    PROMPT_REFORMULADOR,
    RESPUESTA_GENERICA,
)


load_dotenv()

RUTA_CRISTIAN = "agente_Cristian_desarrollo_ti"
RUTA_EDITH = "agente_Edith_outsourcing_ti"
RUTA_RODRIGO = "agente_Rodrigo_mineria_de_datos"
RUTA_GENERICA = "generica"


class Decision(BaseModel):
    """Decisión estructurada del nodo Coordinador."""

    rutas: list[
        Literal[
            "agente_Cristian_desarrollo_ti",
            "agente_Edith_outsourcing_ti",
            "agente_Rodrigo_mineria_de_datos",
            "generica",
        ]
    ] = Field(
        min_length=1,
        description="Uno o más agentes necesarios para atender el mensaje.",
    )
    motivo: str = Field(description="Una frase: por qué se eligieron esas rutas.")


class Reformulacion(BaseModel):
    """Consulta aclarada antes de decidir las rutas."""

    texto: str = Field(
        min_length=1,
        description="Consulta reformulada sin inventar datos del usuario.",
    )


class EstadoCoordinador(MessagesState):
    """Estado con la memoria del diálogo y el resultado del enrutamiento."""

    ruta: str
    rutas: list[str]
    motivo: str
    pregunta_reformulada: str
    respuesta: str
    resultados: Annotated[list[tuple[str, str]], add]


modelo = os.getenv("MODELO", "").strip()
if not modelo:
    raise RuntimeError("Falta la variable MODELO en el archivo .env")

llm = ChatGoogleGenerativeAI(model=modelo, temperature=0)
enrutador = llm.with_structured_output(Decision)
reformulador = llm.with_structured_output(Reformulacion)


def _texto_mensaje(mensaje: object) -> str:
    """Convierte el contenido de un mensaje de LangChain a texto."""
    contenido = getattr(mensaje, "content", mensaje)
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return " ".join(
            str(parte.get("text", "")) if isinstance(parte, dict) else str(parte)
            for parte in contenido
        ).strip()
    return str(contenido)


def _ultimo_texto(estado: EstadoCoordinador) -> str:
    """Obtiene la última consulta humana del estado."""
    for mensaje in reversed(estado["messages"]):
        if isinstance(mensaje, HumanMessage) or getattr(mensaje, "type", "") == "human":
            return _texto_mensaje(mensaje)
    return _texto_mensaje(estado["messages"][-1])


def _texto_consulta(estado: EstadoCoordinador) -> str:
    """Devuelve la versión reformulada cuando está disponible."""
    return str(estado.get("pregunta_reformulada") or _ultimo_texto(estado))


async def reformular(estado: EstadoCoordinador) -> dict[str, str]:
    """Aclara la consulta antes de que el coordinador elija sus rutas."""
    resultado = await reformulador.ainvoke(
        [
            SystemMessage(content=PROMPT_REFORMULADOR),
            HumanMessage(content=_ultimo_texto(estado)),
        ]
    )
    return {"pregunta_reformulada": resultado.texto.strip()}


def _intenciones_explicitas(texto: str) -> tuple[bool, bool, bool]:
    """Identifica solicitudes inequívocas para evitar rutas no requeridas."""
    texto_normalizado = texto.casefold()
    desarrollo = any(
        termino in texto_normalizado
        for termino in (
            "software",
            "portal",
            "aplicación",
            "aplicacion",
            "sistema",
            "sitio web",
            "plataforma web",
            "desarrollo web",
            "desarrollo de web",
            "implementar",
            "proyecto de desarrollo",
            "desarrollo de software",
        )
    )
    mineria = any(
        termino in texto_normalizado
        for termino in (
            "minería",
            "mineria",
            "análisis de datos",
            "analítica",
            "analitica",
            "tendencia",
            "fraude",
            "preprocesamiento",
            "modelado",
            "estados financieros",
            "análisis financiero",
            "analisis financiero",
        )
    )
    outsourcing = any(
        termino in texto_normalizado
        for termino in (
            "outsourcing",
            "recursos humanos",
            "personal ti",
            "contratar",
            "contratación",
            "contratacion",
            "equipo de qa",
            "analista de qa",
            "analista qa",
            "horas hombre",
            "hh",
        )
    ) or bool(
        re.search(
            r"\b\d+\s+(?:profesionales|personas|desarrolladores|arquitectos?|qa|"
            r"analistas?|analista\s+(?:de\s+)?qa)\b",
            texto_normalizado,
        )
    )
    return desarrollo, outsourcing, mineria


async def coordinador(estado: EstadoCoordinador) -> dict[str, str]:
    """Decide de forma estructurada cuál ruta debe seguir la consulta."""
    texto = _texto_consulta(estado)
    decision = await enrutador.ainvoke(
        [SystemMessage(content=PROMPT_COORDINADOR), HumanMessage(content=texto)]
    )
    rutas = list(dict.fromkeys(decision.rutas))
    desarrollo, outsourcing, mineria = _intenciones_explicitas(texto)

    rutas_explicitas = [
        ruta
        for ruta, aplica in (
            (RUTA_CRISTIAN, desarrollo),
            (RUTA_EDITH, outsourcing),
            (RUTA_RODRIGO, mineria),
        )
        if aplica
    ]
    if rutas_explicitas:
        rutas = rutas_explicitas
        if len(rutas) == 1 and rutas[0] == RUTA_CRISTIAN:
            motivo = (
                "La solicitud corresponde a un proyecto de desarrollo de software "
                "y no solicita personal TI."
            )
        elif len(rutas) == 1 and rutas[0] == RUTA_EDITH:
            motivo = "La solicitud pide explícitamente personal o perfiles TI."
        else:
            motivo = (
                "La solicitud combina necesidades de "
                + ", ".join(ruta.removeprefix("agente_").replace("_", " ") for ruta in rutas)
                + "."
            )
    else:
        if RUTA_EDITH in rutas and not outsourcing:
            rutas.remove(RUTA_EDITH)
        motivo = decision.motivo

    return {"ruta": ", ".join(rutas), "rutas": rutas, "motivo": motivo}


def _respuesta(ruta: str, texto: str) -> dict[str, object]:
    """Guarda una respuesta de ruta y la agrega a la memoria del diálogo."""
    return {"resultados": [(ruta, texto)], "messages": [AIMessage(content=texto)]}


def _solicitud_especializada(ruta: str, texto: str) -> str:
    """Aísla la necesidad relevante cuando la consulta solicita varios servicios."""
    servicio = {
        RUTA_CRISTIAN: "desarrollo de software",
        RUTA_EDITH: "outsourcing de recursos humanos TI",
        RUTA_RODRIGO: "minería de datos",
    }[ruta]
    return (
        f"Prepara únicamente la cotización de {servicio} solicitada por el usuario. "
        "El mensaje puede contener otros servicios: ignóralos por completo. No los "
        "menciones, no indiques que están fuera de tu alcance y no solicites datos "
        "para ellos. Usa solo los datos pertinentes a tu especialidad y tus "
        "herramientas para calcular una propuesta. Si faltan detalles, entrega la "
        "propuesta base de tu especialidad con plazo de 1 mes.\n\n"
        f"Mensaje original:\n{texto}"
    )


async def _consultar_agente(
    ruta: str,
    responder_agente: Callable[[str, str | None], Awaitable[str]],
    texto: str,
    config: RunnableConfig,
) -> dict[str, object]:
    """Consulta un agente especializado y conserva un error legible si falla."""
    context_id = config.get("configurable", {}).get("thread_id")
    try:
        respuesta = await responder_agente(_solicitud_especializada(ruta, texto), context_id)
        return _respuesta(ruta, respuesta)
    except Exception as error:
        mensaje = str(error).splitlines()[0] or "no se pudo generar la cotización"
        return _respuesta(ruta, f"No se pudo generar la cotización solicitada: {mensaje}")


async def agente_cristian(
    estado: EstadoCoordinador, config: RunnableConfig
) -> dict[str, object]:
    """Obtiene una propuesta del agente de cotizaciones de desarrollo."""
    return await _consultar_agente(
        RUTA_CRISTIAN, responder_cristian, _texto_consulta(estado), config
    )


async def agente_edith(
    estado: EstadoCoordinador, config: RunnableConfig
) -> dict[str, object]:
    """Obtiene una propuesta del agente de cotizaciones de outsourcing."""
    return await _consultar_agente(RUTA_EDITH, responder_edith, _texto_consulta(estado), config)


async def agente_rodrigo(
    estado: EstadoCoordinador, config: RunnableConfig
) -> dict[str, object]:
    """Obtiene una propuesta del agente de cotizaciones de minería de datos."""
    return await _consultar_agente(
        RUTA_RODRIGO, responder_rodrigo, _texto_consulta(estado), config
    )


async def respuesta_generica(_estado: EstadoCoordinador) -> dict[str, object]:
    """Responde asuntos no relacionados sin usar el modelo."""
    return _respuesta(RUTA_GENERICA, RESPUESTA_GENERICA)


def siguientes_rutas(estado: EstadoCoordinador) -> list[str]:
    """Devuelve todos los nodos correspondientes a la decisión."""
    return estado["rutas"]


_constructor = StateGraph(EstadoCoordinador)
_constructor.add_node("Coordinador", coordinador)
_constructor.add_node("Reformulador", reformular)
_constructor.add_node(RUTA_CRISTIAN, agente_cristian)
_constructor.add_node(RUTA_EDITH, agente_edith)
_constructor.add_node(RUTA_RODRIGO, agente_rodrigo)
_constructor.add_node(RUTA_GENERICA, respuesta_generica)
_constructor.add_edge(START, "Reformulador")
_constructor.add_edge("Reformulador", "Coordinador")
_constructor.add_conditional_edges(
    "Coordinador",
    siguientes_rutas,
    {
        RUTA_CRISTIAN: RUTA_CRISTIAN,
        RUTA_EDITH: RUTA_EDITH,
        RUTA_RODRIGO: RUTA_RODRIGO,
        RUTA_GENERICA: RUTA_GENERICA,
    },
)
_constructor.add_edge(RUTA_CRISTIAN, END)
_constructor.add_edge(RUTA_EDITH, END)
_constructor.add_edge(RUTA_RODRIGO, END)
_constructor.add_edge(RUTA_GENERICA, END)
graph = _constructor.compile(checkpointer=MemorySaver())


def _configuracion(context_id: str | None) -> dict[str, dict[str, str]]:
    """Configura el identificador de hilo para preservar memoria."""
    return {"configurable": {"thread_id": context_id or str(uuid4())}}


async def ejecutar(texto: str, context_id: str | None) -> EstadoCoordinador:
    """Ejecuta el grafo y devuelve el estado final completo."""
    estado = await graph.ainvoke(
        {"messages": [{"role": "user", "content": texto}]},
        config=_configuracion(context_id),
    )
    resultados = dict(estado["resultados"])
    respuestas = [resultados[ruta] for ruta in estado["rutas"] if ruta in resultados]
    estado["respuesta"] = "\n\n---\n\n".join(respuestas)
    return estado


async def responder(texto: str, context_id: str | None) -> str:
    """Cumple el contrato común y devuelve solamente la respuesta."""
    estado = await ejecutar(texto, context_id)
    return str(estado["respuesta"])


def saltos(texto: str) -> str:
    """Ejecuta el grafo e informa los nodos y motivo de enrutamiento."""
    estado = asyncio.run(ejecutar(texto, None))
    print("Nodo: Reformulador")
    print(f"Consulta reformulada: {estado['pregunta_reformulada']}")
    print("Nodo: Coordinador")
    print(f"Motivo: {estado['motivo']}")
    for ruta in estado["rutas"]:
        print(f"Nodo: {ruta}")
    print(f"Total de saltos: {len(estado['rutas']) + 2}")
    return str(estado["respuesta"])


def diagrama() -> str:
    """Devuelve la estructura Mermaid del grafo."""
    return graph.get_graph().draw_mermaid()
