"""API HTTP para consultar el coordinador de cotizaciones."""

import logging
import os
from contextlib import asynccontextmanager
from hmac import compare_digest
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Body, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
import httpx
from langchain_core.messages import AIMessage
from pydantic import BaseModel, ConfigDict, Field

from src.coordinador.graph import (
    URL_DESARROLLO,
    URL_MINERIA,
    URL_OUTSOURCING,
    _configuracion,
    _texto_mensaje,
    _url_para,
    graph,
)


load_dotenv()
registro = logging.getLogger(__name__)
MODELO = os.getenv("MODELO", "").strip()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_SECRET = os.getenv("TELEGRAM_SECRET", "").strip()
_TIEMPO_ESPERA_TELEGRAM = httpx.Timeout(30.0)


class ChatRequest(BaseModel):
    """Consulta que se enviará al coordinador."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "cliente-123",
                "texto": "Necesito dos desarrolladores Python por seis meses.",
            }
        }
    )

    user_id: Annotated[
        str,
        Field(
            description="Identificador estable del usuario; mantiene el contexto de la conversación.",
            examples=["cliente-123"],
            min_length=1,
        ),
    ]
    texto: Annotated[
        str,
        Field(
            description="Solicitud de cotización que el coordinador enviará al agente especializado.",
            examples=["Necesito dos desarrolladores Python por seis meses."],
            min_length=1,
        ),
    ]


class ChatResponse(BaseModel):
    """Resultado entregado por el coordinador."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ruta": "agente_Edith_outsourcing_ti",
                "motivo": "La consulta corresponde a contratación de personal TI.",
                "respuesta": "Cotización de outsourcing: ...",
            }
        }
    )

    ruta: Annotated[
        str,
        Field(
            description="Agente especializado al que el coordinador derivó la consulta.",
            examples=["agente_Edith_outsourcing_ti"],
        ),
    ]
    motivo: Annotated[
        str,
        Field(
            description="Criterio usado por el coordinador para seleccionar la ruta.",
            examples=["La consulta corresponde a contratación de personal TI."],
        ),
    ]
    respuesta: Annotated[
        str,
        Field(
            description="Respuesta generada por el agente especializado.",
            examples=["Cotización de outsourcing: ..."],
        ),
    ]


class ErrorResponse(BaseModel):
    """Error seguro para clientes de la API."""

    detalle: Annotated[
        str,
        Field(
            description="Descripción legible del problema, sin datos sensibles.",
            examples=["No se pudo obtener una respuesta del modelo. Intenta nuevamente."],
        ),
    ]


def _datos_ruta(texto: str) -> tuple[str, str]:
    """Devuelve el nombre y motivo de la ruta elegida por el coordinador."""
    url = _url_para(texto)
    if url == URL_MINERIA:
        return (
            "agente_Rodrigo_mineria_de_datos",
            "La consulta menciona datos, analítica, ETL o minería de datos.",
        )
    if url == URL_DESARROLLO:
        return (
            "agente_Cristian_desarrollo_ti",
            "La consulta menciona desarrollo, software, sistemas o aplicaciones.",
        )
    return (
        "agente_Edith_outsourcing_ti",
        "La consulta se deriva a outsourcing de personal TI por defecto.",
    )


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    """Conserva el grafo compilado durante toda la vida de la aplicación."""
    app.state.grafo_coordinador = graph
    yield


app = FastAPI(
    title="Cotizaciones API",
    version="1.0.0",
    description=(
        "API del coordinador de cotizaciones TI. Deriva cada consulta a una de "
        "tres rutas: desarrollo TI, outsourcing TI o minería de datos."
    ),
    openapi_tags=[
        {
            "name": "agente_Cristian_desarrollo_ti",
            "description": "Consultas derivadas a cotizaciones de desarrollo TI.",
        },
        {
            "name": "agente_Edith_outsourcing_ti",
            "description": "Consultas derivadas a cotizaciones de outsourcing TI.",
        },
        {
            "name": "agente_Rodrigo_mineria_de_datos",
            "description": "Consultas derivadas a cotizaciones de minería de datos.",
        },
        {
            "name": "telegram",
            "description": "Punto de entrada reservado para Telegram.",
        },
    ],
    lifespan=ciclo_vida,
)


@app.get("/health", tags=["agente_Cristian_desarrollo_ti"])
async def health() -> dict[str, object]:
    """Informa que la API está disponible."""
    return {"ok": True, "modelo": MODELO}


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=[
        "agente_Cristian_desarrollo_ti",
        "agente_Edith_outsourcing_ti",
        "agente_Rodrigo_mineria_de_datos",
    ],
    summary="Enviar una consulta al coordinador",
    responses={
        200: {"description": "Consulta procesada y derivada al agente correspondiente."},
        422: {"description": "El cuerpo no es válido; `texto` y `user_id` son obligatorios."},
        502: {
            "model": ErrorResponse,
            "description": "No fue posible obtener una respuesta del modelo o agente.",
        },
    },
)
async def chat(solicitud: ChatRequest, request: Request) -> ChatResponse | JSONResponse:
    """Ejecuta el grafo con el hilo asociado al usuario."""
    ruta, motivo = _datos_ruta(solicitud.texto)
    try:
        estado: dict[str, Any] = await request.app.state.grafo_coordinador.ainvoke(
            {"messages": [{"role": "user", "content": solicitud.texto}]},
            config=_configuracion(solicitud.user_id),
        )
        respuesta = _texto_mensaje(estado["messages"][-1])
        return ChatResponse(ruta=ruta, motivo=motivo, respuesta=respuesta)
    except Exception as error:
        registro.error("Falló la consulta de chat para la ruta %s: %s", ruta, error)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "detalle": "No se pudo obtener una respuesta del modelo. Intenta nuevamente."
            },
        )


async def _enviar_mensaje_telegram(chat_id: int | str, texto: str) -> None:
    """Envía una respuesta de texto mediante la API HTTP de Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=_TIEMPO_ESPERA_TELEGRAM) as cliente:
        respuesta = await cliente.post(url, json={"chat_id": chat_id, "text": texto})
        respuesta.raise_for_status()
        cuerpo = respuesta.json()
    if not cuerpo.get("ok"):
        raise RuntimeError("Telegram rechazó el envío del mensaje.")


@app.post("/telegram", include_in_schema=False)
async def telegram(
    actualizacion: Annotated[
        Any, Body(description="Actualización JSON enviada por Telegram.")
    ],
    secreto: Annotated[
        str | None,
        Header(
            alias="X-Telegram-Bot-Api-Secret-Token",
            description="Secreto configurado al registrar el webhook.",
        ),
    ] = None,
) -> dict[str, bool]:
    """Procesa mensajes de texto recibidos desde el webhook de Telegram."""
    if not TELEGRAM_SECRET or not compare_digest(secreto or "", TELEGRAM_SECRET):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")

    if not isinstance(actualizacion, dict):
        return {"ok": True}
    mensaje = actualizacion.get("message")
    if not isinstance(mensaje, dict):
        return {"ok": True}
    chat = mensaje.get("chat")
    texto = mensaje.get("text")
    if not isinstance(chat, dict) or not chat.get("id") or not isinstance(texto, str):
        return {"ok": True}
    texto = texto.strip()
    if not texto:
        return {"ok": True}

    chat_id = chat["id"]
    ruta, _motivo = _datos_ruta(texto)
    try:
        estado: dict[str, Any] = await graph.ainvoke(
            {"messages": [{"role": "user", "content": texto}]},
            config=_configuracion(str(chat_id)),
        )
        respuesta = _texto_mensaje(estado["messages"][-1])
        await _enviar_mensaje_telegram(chat_id, respuesta)
        registro.info("Telegram chat_id=%s ruta=%s", chat_id, ruta)
    except Exception:
        registro.error("Falló Telegram para chat_id=%s ruta=%s", chat_id, ruta)
    return {"ok": True}
