"""Autenticación local y administración de usuarios autorizados."""

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, Request, status


RUTA_BASE = Path(__file__).resolve().parent.parent
RUTA_BD = RUTA_BASE / "data" / "usuarios.sqlite3"
_SESIONES: dict[str, tuple[str, str, datetime]] = {}
_DURACION_SESION = timedelta(hours=8)


def _conectar() -> sqlite3.Connection:
    """Abre la base local de usuarios."""
    RUTA_BD.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row
    return conexion


def _hash_clave(clave: str, sal: bytes | None = None) -> tuple[bytes, bytes]:
    """Genera un hash scrypt con sal aleatoria."""
    sal = sal or secrets.token_bytes(16)
    return sal, hashlib.scrypt(clave.encode(), salt=sal, n=2**14, r=8, p=1)


def preparar_usuarios() -> None:
    """Crea la tabla y el supervisor inicial definido en el entorno."""
    with _conectar() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario TEXT PRIMARY KEY,
                sal BLOB NOT NULL,
                clave_hash BLOB NOT NULL,
                rol TEXT NOT NULL CHECK (rol IN ('supervisor', 'externo')),
                activo INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        usuario = os.getenv("SUPERVISOR_USUARIO", "").strip()
        clave = os.getenv("SUPERVISOR_CLAVE", "")
        if not usuario or not clave:
            return
        existe = conexion.execute(
            "SELECT 1 FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()
        if not existe:
            sal, clave_hash = _hash_clave(clave)
            conexion.execute(
                "INSERT INTO usuarios (usuario, sal, clave_hash, rol) VALUES (?, ?, ?, 'supervisor')",
                (usuario, sal, clave_hash),
            )


def autenticar(usuario: str, clave: str) -> tuple[str, str] | None:
    """Valida credenciales y devuelve usuario y rol si son correctos."""
    with _conectar() as conexion:
        fila = conexion.execute(
            "SELECT usuario, sal, clave_hash, rol FROM usuarios WHERE usuario = ? AND activo = 1",
            (usuario,),
        ).fetchone()
    if not fila:
        return None
    _, hash_calculado = _hash_clave(clave, fila["sal"])
    if not hmac.compare_digest(hash_calculado, fila["clave_hash"]):
        return None
    return str(fila["usuario"]), str(fila["rol"])


def crear_sesion(usuario: str, rol: str) -> str:
    """Crea un token de sesión temporal."""
    token = secrets.token_urlsafe(32)
    _SESIONES[token] = (usuario, rol, datetime.now(UTC) + _DURACION_SESION)
    return token


def cerrar_sesion(token: str | None) -> None:
    """Invalida una sesión si existe."""
    if token:
        _SESIONES.pop(token, None)


def sesion_actual(request: Request) -> tuple[str, str]:
    """Obtiene la sesión válida desde la cookie HTTPOnly."""
    token = request.cookies.get("sesion_cotizaciones")
    datos = _SESIONES.get(token or "")
    if not datos or datos[2] <= datetime.now(UTC):
        if token:
            _SESIONES.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes iniciar sesión para usar el coordinador.",
        )
    return datos[0], datos[1]


def crear_usuario_externo(usuario: str, clave: str) -> None:
    """Registra un usuario externo con su clave hasheada."""
    sal, clave_hash = _hash_clave(clave)
    try:
        with _conectar() as conexion:
            conexion.execute(
                "INSERT INTO usuarios (usuario, sal, clave_hash, rol) VALUES (?, ?, ?, 'externo')",
                (usuario, sal, clave_hash),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("Ese usuario ya existe.") from error


def listar_usuarios() -> list[dict[str, str | bool]]:
    """Devuelve usuarios sin exponer claves ni hashes."""
    with _conectar() as conexion:
        filas = conexion.execute(
            "SELECT usuario, rol, activo FROM usuarios ORDER BY usuario"
        ).fetchall()
    return [
        {"usuario": str(fila["usuario"]), "rol": str(fila["rol"]), "activo": bool(fila["activo"])}
        for fila in filas
    ]
