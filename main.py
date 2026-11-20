"""Punto de entrada de los agentes del proyecto."""

import importlib
import asyncio
import sys


def main() -> None:
    """Recibe un agente y una pregunta y deja preparado el enrutamiento."""
    argumentos = sys.argv[1:]
    if not argumentos:
        print("Uso: python main.py {agente} \"pregunta\" [--saltos|--diagrama]")
        return

    agente = argumentos.pop(0)
    if agente not in {
        "viajes",
        "restaurantes",
        "coordinador",
        "Cristian_desarrollo_ti",
        "Edith_outsourcing_ti",
        "Rodrigo_mineria_de_datos",
    }:
        print(f"El agente '{agente}' todavía no existe.")
        return

    modo = None
    if "--saltos" in argumentos:
        modo = "saltos"
        argumentos.remove("--saltos")
    elif "--diagrama" in argumentos:
        modo = "diagrama"
        argumentos.remove("--diagrama")

    pregunta = " ".join(argumentos)
    try:
        if agente == "coordinador":
            modulo = importlib.import_module("src.coordinador.graph")
        else:
            modulo_base = "crew" if agente == "Edith_outsourcing_ti" else "graph"
            modulo = importlib.import_module(f"src.agente_{agente}.{modulo_base}")
    except Exception as error:
        mensaje = str(error).splitlines()[0] or "no se pudo cargar"
        print(f"Error al cargar el agente '{agente}': {mensaje}")
        return

    if modo == "diagrama":
        funcion = getattr(modulo, "diagrama", None)
        if funcion is None:
            print(f"El agente '{agente}' todavía no existe.")
            return
        try:
            print(funcion())
        except Exception as error:
            print(f"Error al generar el diagrama: {str(error).splitlines()[0]}")
        return

    if modo == "saltos":
        funcion = getattr(modulo, "saltos", None)
        if funcion is None:
            print(f"El agente '{agente}' todavía no existe.")
            return
        try:
            print(funcion(pregunta))
        except Exception as error:
            print(f"Error al ejecutar el agente: {str(error).splitlines()[0]}")
        return

    responder = getattr(modulo, "responder", None)
    if responder is None:
        print(f"El agente '{agente}' todavía no existe.")
        return
    try:
        print(asyncio.run(responder(pregunta, None)))
    except Exception as error:
        print(f"Error al ejecutar el agente: {str(error).splitlines()[0]}")


if __name__ == "__main__":
    main()
