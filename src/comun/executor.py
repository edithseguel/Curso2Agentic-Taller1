"""Adaptador común entre A2A y la función responder de cada agente."""

import inspect
from collections.abc import Awaitable, Callable
from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part


Responder = Callable[[str, str], str | Awaitable[str]]


class Executor(AgentExecutor):
    """Ejecuta la función responder y publica su resultado en A2A."""

    def __init__(self, responder: Responder) -> None:
        self.responder = responder

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        texto = context.get_user_input()
        context_id = context.context_id or str(uuid4())

        try:
            respuesta = self.responder(texto, context_id)
            if inspect.isawaitable(respuesta):
                respuesta = await respuesta
            texto_respuesta = str(respuesta)
        except Exception as error:  # noqa: BLE001
            detalle = " ".join(str(error).split()) or "error desconocido"
            texto_respuesta = f"No se pudo obtener una respuesta: {detalle}"

        await event_queue.enqueue_event(
            Message(
                message_id=str(uuid4()),
                context_id=context_id,
                task_id=context.task_id or "",
                role=2,
                parts=[Part(text=texto_respuesta)],
            )
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        context_id = context.context_id or str(uuid4())
        await event_queue.enqueue_event(
            Message(
                message_id=str(uuid4()),
                context_id=context_id,
                task_id=context.task_id or "",
                role=2,
                parts=[Part(text="La cancelación no está soportada.")],
            )
        )
