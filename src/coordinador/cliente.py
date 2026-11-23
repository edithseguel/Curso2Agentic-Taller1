"""Cliente A2A del coordinador."""

import asyncio
import os
import time
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text, new_text_message
from a2a.types import (
    GetTaskRequest,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    TaskState,
)


TIEMPO_ESPERA_A2A = float(os.environ.get("TIEMPO_ESPERA_A2A", "30"))
_HTTPX = httpx.AsyncClient(timeout=httpx.Timeout(TIEMPO_ESPERA_A2A))
_CLIENTES: dict[str, Any] = {}
_ESTADOS_TERMINALES = {
    TaskState.Value("TASK_STATE_COMPLETED"),
    TaskState.Value("TASK_STATE_FAILED"),
    TaskState.Value("TASK_STATE_CANCELED"),
    TaskState.Value("TASK_STATE_REJECTED"),
}


async def obtener_cliente(url: str) -> Any:
    """Resuelve la ficha del agente y devuelve un cliente A2A cacheado."""
    if url not in _CLIENTES:
        resolvedor = A2ACardResolver(_HTTPX, url)
        tarjeta = await resolvedor.get_agent_card(
            http_kwargs={"timeout": TIEMPO_ESPERA_A2A}
        )
        _CLIENTES[url] = await create_client(
            tarjeta,
            ClientConfig(
                streaming=False,
                polling=False,
                httpx_client=_HTTPX,
                supported_protocol_bindings=["JSONRPC"],
            ),
        )
    return _CLIENTES[url]


async def preguntar(cliente: Any, texto: str, context_id: str) -> str:
    """Envía una pregunta y extrae la respuesta directa o los artifacts de la tarea."""
    mensaje = new_text_message(texto, context_id=context_id, role=Role.ROLE_USER)
    solicitud = SendMessageRequest(
        message=mensaje,
        configuration=SendMessageConfiguration(
            accepted_output_modes=["text"],
            return_immediately=False,
        ),
    )

    respuestas = [respuesta async for respuesta in cliente.send_message(solicitud)]
    if not respuestas:
        return "El agente no devolvió una respuesta."

    respuesta = respuestas[-1]
    if respuesta.HasField("message"):
        return get_message_text(respuesta.message)

    if not respuesta.HasField("task"):
        return "El agente devolvió una respuesta no reconocida."

    tarea = respuesta.task
    limite = time.monotonic() + TIEMPO_ESPERA_A2A
    while tarea.status.state not in _ESTADOS_TERMINALES:
        if time.monotonic() >= limite:
            return "El agente tardó demasiado en completar la tarea."
        await asyncio.sleep(0.1)
        tarea = await cliente.get_task(GetTaskRequest(id=tarea.id))

    textos = [get_artifact_text(artifact) for artifact in tarea.artifacts]
    return "\n".join(texto for texto in textos if texto) or "La tarea no produjo texto."


async def consultar_agente(url: str, texto: str, context_id: str) -> str:
    """Consulta un agente mediante su Agent Card y el protocolo A2A HTTP."""
    try:
        cliente = await obtener_cliente(url)
        return await preguntar(cliente, texto, context_id)
    except httpx.TimeoutException as error:
        raise RuntimeError("El agente especializado excedió el tiempo de espera.") from error
    except httpx.HTTPError as error:
        raise RuntimeError("No se pudo contactar al agente especializado.") from error
