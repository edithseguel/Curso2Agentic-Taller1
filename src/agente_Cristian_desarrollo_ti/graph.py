"""Grafo LangGraph del agente de cotizaciones de desarrollo TI."""

import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

from .prompts import SYSTEM_PROMPT
from .tools import cotizador, planeador


load_dotenv()

modelo = os.getenv("MODELO", "").strip()
if not modelo:
    raise RuntimeError("Falta la variable MODELO en el archivo .env")

graph = create_agent(
    model=ChatGoogleGenerativeAI(model=modelo),
    tools=[planeador, cotizador],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=MemorySaver(),
)


def _texto_mensaje(mensaje: Any) -> str:
    """Convierte el contenido de un mensaje de LangChain a texto."""
    contenido = getattr(mensaje, "content", mensaje)
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = []
        for parte in contenido:
            if isinstance(parte, dict) and parte.get("text"):
                partes.append(str(parte["text"]))
            elif isinstance(parte, str):
                partes.append(parte)
        return " ".join(partes)
    return str(contenido)


def _configuracion(context_id: str | None) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": context_id or "sin-contexto"}}


async def responder(texto: str, context_id: str | None) -> str:
    """Responde usando el mismo hilo cuando se entrega el mismo context_id."""
    estado = await graph.ainvoke(
        {"messages": [{"role": "user", "content": texto}]},
        config=_configuracion(context_id),
    )
    return _texto_mensaje(estado["messages"][-1])


def saltos(texto: str) -> str:
    """Ejecuta el grafo e imprime los nodos y herramientas recorridos."""
    respuesta = ""
    cantidad = 0
    for actualizacion in graph.stream(
        {"messages": [{"role": "user", "content": texto}]},
        config=_configuracion(None),
        stream_mode="updates",
    ):
        for nodo, estado in actualizacion.items():
            cantidad += 1
            print(f"Nodo: {nodo}")
            mensajes = estado.get("messages", []) if isinstance(estado, dict) else []
            for mensaje in mensajes:
                for llamada in getattr(mensaje, "tool_calls", []) or []:
                    print(f"Herramienta llamada: {llamada.get('name', 'desconocida')}")
                if getattr(mensaje, "type", "") == "ai" and _texto_mensaje(mensaje):
                    respuesta = _texto_mensaje(mensaje)
    print(f"Total de saltos: {cantidad}")
    return respuesta


def diagrama() -> str:
    """Devuelve la estructura Mermaid del grafo."""
    return graph.get_graph().draw_mermaid()
