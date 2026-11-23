"""API HTTP para consultar el coordinador de cotizaciones."""

import logging
import os
from contextlib import asynccontextmanager
from hmac import compare_digest
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
import httpx
from pydantic import BaseModel, ConfigDict, Field

from api.seguridad import (
    autenticar,
    cerrar_sesion,
    crear_sesion,
    crear_usuario_externo,
    listar_usuarios,
    preparar_usuarios,
    sesion_actual,
)
from src.coordinador.graph import (
    ejecutar,
    graph,
)


load_dotenv()
registro = logging.getLogger(__name__)
MODELO = os.getenv("MODELO", "").strip()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_SECRET = os.getenv("TELEGRAM_SECRET", "").strip()
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


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    usuario: Annotated[str, Field(min_length=3, max_length=60)]
    clave: Annotated[str, Field(min_length=8, max_length=128)]


class UsuarioExternoRequest(LoginRequest):
    """Datos para crear un usuario externo."""


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    """Conserva el grafo compilado durante toda la vida de la aplicación."""
    preparar_usuarios()
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


def _cookie_segura(request: Request) -> bool:
    """Activa la marca Secure cuando la solicitud llegó mediante HTTPS."""
    return (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "").casefold() == "https"
    )


@app.post("/api/login", include_in_schema=False)
async def login(datos: LoginRequest, request: Request, response: Response) -> dict[str, str]:
    """Inicia sesión de un usuario autorizado."""
    resultado = autenticar(datos.usuario.strip(), datos.clave)
    if resultado is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")
    usuario, rol = resultado
    response.set_cookie(
        "sesion_cotizaciones",
        crear_sesion(usuario, rol),
        httponly=True,
        samesite="lax",
        secure=_cookie_segura(request),
        max_age=8 * 60 * 60,
    )
    return {"usuario": usuario, "rol": rol}


@app.post("/api/logout", include_in_schema=False)
async def logout(request: Request, response: Response) -> dict[str, bool]:
    """Cierra la sesión actual."""
    cerrar_sesion(request.cookies.get("sesion_cotizaciones"))
    response.delete_cookie("sesion_cotizaciones")
    return {"ok": True}


@app.get("/api/sesion", include_in_schema=False)
async def obtener_sesion(sesion: tuple[str, str] = Depends(sesion_actual)) -> dict[str, str]:
    """Devuelve los datos seguros de la sesión activa."""
    return {"usuario": sesion[0], "rol": sesion[1]}


@app.get("/api/usuarios", include_in_schema=False)
async def usuarios(sesion: tuple[str, str] = Depends(sesion_actual)) -> list[dict[str, str | bool]]:
    """Lista usuarios; disponible solo para el supervisor."""
    if sesion[1] != "supervisor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso exclusivo del supervisor.")
    return listar_usuarios()


@app.post("/api/usuarios", include_in_schema=False)
async def crear_usuario(
    datos: UsuarioExternoRequest, sesion: tuple[str, str] = Depends(sesion_actual)
) -> dict[str, bool]:
    """Crea un usuario externo; disponible solo para el supervisor."""
    if sesion[1] != "supervisor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso exclusivo del supervisor.")
    try:
        crear_usuario_externo(datos.usuario.strip(), datos.clave)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return {"ok": True}


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
async def chat(
    solicitud: ChatRequest,
    request: Request,
    sesion: tuple[str, str] = Depends(sesion_actual),
) -> ChatResponse | JSONResponse:
    """Ejecuta el grafo con el hilo asociado al usuario."""
    ruta = "desconocida"
    try:
        estado: dict[str, Any] = await ejecutar(solicitud.texto, solicitud.user_id)
        ruta = str(estado["ruta"])
        return ChatResponse(
            ruta=ruta,
            motivo=str(estado["motivo"]),
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
    tareas.add_task(_procesar_mensaje_telegram, chat_id, texto)
    return {"ok": True}
