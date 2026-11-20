"""Grafo LangGraph de enrutamiento A2A."""

import asyncio
import os
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from .cliente import obtener_cliente, preguntar


load_dotenv()

URL_OUTSOURCING = os.getenv("URL_OUTSOURCING", "http://127.0.0.1:8001")
URL_DESARROLLO = os.getenv("URL_DESARROLLO", "http://127.0.0.1:8002")
URL_MINERIA = os.getenv("URL_MINERIA", "http://127.0.0.1:8003")


def _texto_mensaje(mensaje: object) -> str:
    contenido = getattr(mensaje, "content", mensaje)
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return " ".join(
            str(parte.get("text", "")) if isinstance(parte, dict) else str(parte)
            for parte in contenido
        ).strip()
    return str(contenido)


def _url_para(texto: str) -> str:
    """Elige el agente por el tema explícito de la consulta."""
    texto = texto.lower()
    if any(palabra in texto for palabra in ("minería", "mineria", "datos", "etl", "analítica", "analitica")):
        return URL_MINERIA
    if any(palabra in texto for palabra in ("desarrollo", "software", "sistema", "aplicación", "aplicacion", "programar")):
        return URL_DESARROLLO
    return URL_OUTSOURCING


async def delegar(
    estado: MessagesState, config: RunnableConfig
) -> dict[str, list[AIMessage]]:
    """Enruta el último mensaje del usuario y repite la respuesta del agente."""
    texto = _texto_mensaje(estado["messages"][-1])
    configuracion = config.get("configurable", {})
    context_id = configuracion.get("thread_id") or str(uuid4())
    cliente = await obtener_cliente(_url_para(texto))
    respuesta = await preguntar(cliente, texto, context_id)
    return {"messages": [AIMessage(content=respuesta)]}


_constructor = StateGraph(MessagesState)
_constructor.add_node("delegar", delegar)
_constructor.add_edge(START, "delegar")
_constructor.add_edge("delegar", END)
graph = _constructor.compile(checkpointer=MemorySaver())


def _configuracion(context_id: str | None) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": context_id or str(uuid4())}}


async def responder(texto: str, context_id: str | None) -> str:
    estado = await graph.ainvoke(
        {"messages": [{"role": "user", "content": texto}]},
        config=_configuracion(context_id),
    )
    return _texto_mensaje(estado["messages"][-1])


def saltos(texto: str) -> str:
    respuesta = asyncio.run(responder(texto, None))
    print("Nodo: delegar")
    print("Total de saltos: 1")
    return respuesta


def diagrama() -> str:
    return graph.get_graph().draw_mermaid()
