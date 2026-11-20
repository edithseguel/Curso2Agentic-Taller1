"""Fábrica del servidor HTTP común para los agentes A2A."""

from collections.abc import Callable

from fastapi import FastAPI

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard

from .executor import Executor, Responder


def crear_app(tarjeta: AgentCard, responder: Responder) -> FastAPI:
    """Crea una aplicación FastAPI con las rutas A2A y de salud."""
    app = FastAPI(title=tarjeta.name or "Agente A2A")
    manejador = DefaultRequestHandler(
        agent_executor=Executor(responder),
        task_store=InMemoryTaskStore(),
        agent_card=tarjeta,
    )

    @app.get("/salud")
    async def salud() -> dict[str, bool]:
        return {"ok": True}

    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(tarjeta),
        # El panel web usa el método legado `message/send`; el SDK 1.x lo
        # acepta al activar compatibilidad v0.3 en las rutas A2A.
        jsonrpc_routes=create_jsonrpc_routes(
            manejador, rpc_url="/", enable_v0_3_compat=True
        ),
        rest_routes=create_rest_routes(manejador, enable_v0_3_compat=True),
    )
    return app
