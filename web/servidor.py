"""Servidor del panel web y puente HTTP hacia los agentes A2A."""
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Panel de agentes")
RUTA_WEB = Path(__file__).parent
AGENTES = {
    "cristian": {"nombre": "Cristian", "rol": "Desarrollo TI", "url": "http://127.0.0.1:8002"},
    "edith": {"nombre": "Edith", "rol": "Outsourcing TI", "url": "http://127.0.0.1:8001"},
    "rodrigo": {"nombre": "Rodrigo", "rol": "Minería de datos", "url": "http://127.0.0.1:8003"},
    "coordinador": {"nombre": "Coordinador", "rol": "Enrutamiento A2A", "url": "http://127.0.0.1:8004"},
}

class Consulta(BaseModel):
    agente: str
    pregunta: str
    context_id: str | None = None

@app.get("/", include_in_schema=False)
async def inicio() -> FileResponse:
    return FileResponse(RUTA_WEB / "index.html")

@app.post("/api/estado/{agente}")
async def estado(agente: str) -> dict[str, bool | str]:
    datos = AGENTES.get(agente)
    if datos is None:
        raise HTTPException(404, "Agente no encontrado")
    try:
        async with httpx.AsyncClient(timeout=4.0) as cliente:
            respuesta = await cliente.get(f"{datos['url']}/salud")
            respuesta.raise_for_status()
        return {"disponible": True, "mensaje": "En línea"}
    except httpx.HTTPError:
        return {"disponible": False, "mensaje": "Sin conexión"}

@app.post("/api/consulta")
async def consultar(consulta: Consulta) -> dict[str, str]:
    datos = AGENTES.get(consulta.agente)
    if datos is None:
        raise HTTPException(404, "Agente no encontrado")
    if not consulta.pregunta.strip():
        raise HTTPException(400, "Escribe una pregunta")
    mensaje = {
        "role": "ROLE_USER",
        "parts": [{"text": consulta.pregunta}],
        "messageId": "panel-web",
    }
    if consulta.context_id:
        mensaje["contextId"] = consulta.context_id
    cuerpo = {
        "jsonrpc": "2.0",
        "id": "panel-web",
        "method": "SendMessage",
        "params": {"message": mensaje},
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as cliente:
            respuesta = await cliente.post(
                datos["url"],
                json=cuerpo,
                headers={"A2A-Version": "1.0"},
            )
            respuesta.raise_for_status()
            contenido = respuesta.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "El agente tardó demasiado en responder")
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "No se pudo conectar con el agente")
    texto = extraer_texto(contenido)
    if not texto:
        raise HTTPException(502, "El agente entregó una respuesta vacía")
    return {"respuesta": texto}

def extraer_texto(datos: object) -> str:
    if not isinstance(datos, dict):
        return ""
    resultado = datos.get("result", datos)
    if not isinstance(resultado, dict):
        return ""
    mensaje = resultado.get("message", resultado.get("artifact", resultado))
    if isinstance(mensaje, dict):
        partes = mensaje.get("parts", [])
        if isinstance(partes, list):
            return "\n".join(str(p["text"]) for p in partes if isinstance(p, dict) and p.get("text"))
    return mensaje if isinstance(mensaje, str) else ""
