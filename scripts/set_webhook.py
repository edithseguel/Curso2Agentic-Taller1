"""Registra el webhook de Telegram para la API desplegada."""

import asyncio
import os

import httpx
from dotenv import load_dotenv


load_dotenv()


async def main() -> None:
    """Registra el webhook usando la URL pública y el secreto configurados."""
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    secreto = os.getenv("TELEGRAM_SECRET", "").strip()
    url_publica = os.getenv("PUBLIC_URL", "").strip().rstrip("/")
    if not token or not secreto or not url_publica:
        print("Faltan TELEGRAM_TOKEN, TELEGRAM_SECRET o PUBLIC_URL.")
        return

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as cliente:
            respuesta = await cliente.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={"url": f"{url_publica}/telegram", "secret_token": secreto},
            )
            respuesta.raise_for_status()
            print(respuesta.text)
    except httpx.HTTPError:
        print("No se pudo registrar el webhook de Telegram. Revisa token, URL y conexión.")


if __name__ == "__main__":
    asyncio.run(main())
