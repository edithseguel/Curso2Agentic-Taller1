"""CrewAI de Edith, con memoria manual por context_id."""

import asyncio
import os
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv

from .prompts import HISTORIA, OBJETIVO, ROL
from .tools import catalogo_perfiles, cotizador


load_dotenv()
MODELO = os.getenv("MODELO", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
if not MODELO:
    raise RuntimeError("Falta la variable MODELO en el archivo .env")

modelo = LLM(model="gemini/" + MODELO, api_key=GOOGLE_API_KEY, timeout=120)
historiales: dict[str, list[str]] = {}


def _crear_crew(texto: str, historial: list[str], verbose: bool = False, callback: Any = None) -> Crew:
    agente = Agent(
        role=ROL,
        goal=OBJETIVO,
        backstory=HISTORIA,
        tools=[catalogo_perfiles, cotizador],
        llm=modelo,
        verbose=verbose,
        step_callback=callback,
    )
    contexto = "\n".join(historial) if historial else "(sin conversación previa)"
    tarea = Task(
        description=(
            f"Pregunta actual del usuario:\n{texto}\n\n"
            f"Lo hablado antes en esta conversación:\n{contexto}\n\n"
            "Responde según tu rol y entrega solo una respuesta breve en español."
        ),
        expected_output="Una respuesta breve en español o una solicitud de aclaración.",
        agent=agente,
    )
    return Crew(agents=[agente], tasks=[tarea], process=Process.sequential, verbose=verbose)


def _resultado_texto(resultado: Any) -> str:
    return str(getattr(resultado, "raw", resultado)).strip()


async def responder(texto: str, context_id: str | None) -> str:
    """Responde con memoria manual agrupada por context_id."""
    clave = context_id or "sin-contexto"
    historial = historiales.setdefault(clave, [])
    crew = _crear_crew(texto, historial)
    if hasattr(crew, "kickoff_async"):
        resultado = await crew.kickoff_async()
    else:
        resultado = await asyncio.to_thread(crew.kickoff)
    respuesta = _resultado_texto(resultado)
    historial.extend([f"Usuario: {texto}", f"Edith: {respuesta}"])
    return respuesta


def _mostrar_paso(paso: Any) -> None:
    pensamiento = getattr(paso, "thought", None) or getattr(paso, "log", None)
    herramienta = getattr(paso, "tool", None)
    argumentos = getattr(paso, "tool_input", None)
    resultado = getattr(paso, "result", None) or getattr(paso, "observation", None)
    if pensamiento:
        print(f"Pensamiento: {pensamiento}")
    if herramienta:
        print(f"Herramienta llamada: {herramienta}; argumentos: {argumentos}")
    if resultado:
        print(f"Devolución: {resultado}")


def saltos(texto: str) -> str:
    """Ejecuta el crew en modo visible y muestra sus herramientas."""
    herramientas_usadas: list[str] = []

    def mostrar_y_contar(paso: Any) -> None:
        _mostrar_paso(paso)
        herramienta = getattr(paso, "tool", None)
        if herramienta:
            herramientas_usadas.append(str(herramienta))

    crew = _crear_crew(texto, [], verbose=True, callback=mostrar_y_contar)
    resultado = crew.kickoff()
    print(f"Total de herramientas usadas: {len(herramientas_usadas)}")
    return _resultado_texto(resultado)


def diagrama() -> str:
    """Devuelve una representación Mermaid del crew."""
    return "\n".join(
        [
            "flowchart TD",
            "    Tarea[Task: preparar cotización] --> Agente[Agent: Edith]",
            "    Agente --> Catalogo[catalogo_perfiles]",
            "    Agente --> Cotizador[cotizador]",
        ]
    )
