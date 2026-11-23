"""API HTTP para consultar el coordinador de cotizaciones."""

import logging
import os
from contextlib import asynccontextmanager
from hmac import compare_digest
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Body, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.coordinador.graph import (
    ejecutar,
    graph,
)


load_dotenv()
registro = logging.getLogger(__name__)
MODELO = os.getenv("MODELO", "").strip()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_SECRET = os.getenv("TELEGRAM_SECRET", "").strip()
TELEGRAM_ALLOWED_CHAT_IDS = {
    valor.strip()
    for valor in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
    if valor.strip()
}
TOKEN_ACCESO_CHAT = os.getenv("TOKEN_ACCESO_CHAT", "").strip()
_TIEMPO_ESPERA_TELEGRAM = httpx.Timeout(30.0)
RUTA_UI = Path(__file__).with_name("index.html")


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
                "consulta_reformulada": "Solicito cotizar dos desarrolladores Python por seis meses.",
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
    consulta_reformulada: Annotated[
        str,
        Field(
            description="Consulta aclarada por el reformulador antes de activar agentes.",
            examples=["Solicito cotizar dos desarrolladores Python por seis meses."],
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


@app.get("/", include_in_schema=False)
async def inicio() -> FileResponse:
    """Sirve la interfaz web del chat de cotizaciones."""
    return FileResponse(RUTA_UI)


@app.get("/health", tags=["agente_Cristian_desarrollo_ti"])
async def health() -> dict[str, object]:
    """Informa que la API está disponible."""
    return {"ok": True, "modelo": MODELO, "chat_protegido": bool(TOKEN_ACCESO_CHAT)}


def _validar_acceso_chat(token: str | None) -> None:
    """Valida el token configurado exclusivamente en el servidor."""
    if not TOKEN_ACCESO_CHAT:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El acceso al chat no está configurado en el servidor.",
        )
    if not token or not compare_digest(token, TOKEN_ACCESO_CHAT):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


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
        401: {"model": ErrorResponse, "description": "Token ausente o inválido."},
        503: {"model": ErrorResponse, "description": "Acceso no configurado en el servidor."},
        422: {"description": "El cuerpo no es válido; `texto` y `user_id` son obligatorios."},
        502: {
            "model": ErrorResponse,
            "description": "No fue posible obtener una respuesta del modelo o agente.",
        },
    },
)
async def chat(
    solicitud: ChatRequest,
    token_acceso: Annotated[
        str | None,
        Header(alias="X-Token-Acceso", description="Token de acceso al chat."),
    ] = None,
) -> ChatResponse | JSONResponse:
    """Ejecuta el grafo con el hilo asociado al usuario."""
    _validar_acceso_chat(token_acceso)
    ruta = "desconocida"
    try:
        estado: dict[str, Any] = await ejecutar(solicitud.texto, solicitud.user_id)
        ruta = str(estado["ruta"])
        return ChatResponse(
            ruta=ruta,
            motivo=str(estado["motivo"]),
            consulta_reformulada=str(estado["pregunta_reformulada"]),
            respuesta=str(estado["respuesta"]),
        )
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


async def _procesar_mensaje_telegram(chat_id: int | str, texto: str) -> None:
    """Genera y envía la respuesta sin retrasar el webhook de Telegram."""
    ruta = "desconocida"
    try:
        estado: dict[str, Any] = await ejecutar(texto, str(chat_id))
        ruta = str(estado["ruta"])
        respuesta = str(estado["respuesta"])
        await _enviar_mensaje_telegram(chat_id, respuesta)
        registro.info("Telegram chat_id=%s ruta=%s", chat_id, ruta)
    except Exception:
        registro.error("Falló Telegram para chat_id=%s ruta=%s", chat_id, ruta)


@app.post("/telegram", include_in_schema=False)
async def telegram(
    actualizacion: Annotated[
        Any, Body(description="Actualización JSON enviada por Telegram.")
    ],
    tareas: BackgroundTasks,
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
    if TELEGRAM_ALLOWED_CHAT_IDS and str(chat_id) not in TELEGRAM_ALLOWED_CHAT_IDS:
        registro.warning("Telegram rechazado para chat_id no autorizado")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")
    tareas.add_task(_procesar_mensaje_telegram, chat_id, texto)
    return {"ok": True}
