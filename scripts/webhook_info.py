"""Consulta el estado actual del webhook de Telegram."""

import asyncio
import os

import httpx
from dotenv import load_dotenv


load_dotenv()


async def main() -> None:
    """Imprime la respuesta de Telegram con los datos y errores del webhook."""
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        print("Falta TELEGRAM_TOKEN.")
        return

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as cliente:
            respuesta = await cliente.get(
                f"https://api.telegram.org/bot{token}/getWebhookInfo"
            )
            respuesta.raise_for_status()
            print(respuesta.text)
    except httpx.HTTPError:
        print("No se pudo consultar el webhook de Telegram. Revisa token y conexión.")


if __name__ == "__main__":
    asyncio.run(main())
