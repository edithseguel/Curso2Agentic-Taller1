"""Pruebas unitarias del enrutamiento y de la llamada A2A."""

import asyncio

import pytest

from src.coordinador import graph


@pytest.mark.parametrize(
    ("texto", "esperadas"),
    [
        ("Necesito un portal web", (True, False, False)),
        ("Necesito 2 analistas QA por 3 meses", (False, True, False)),
        ("Quiero un análisis de incidentes", (False, False, True)),
        (
            "Necesito un portal web, 2 analistas QA y análisis de incidentes",
            (True, True, True),
        ),
    ],
)
def test_intenciones_explicitas(texto, esperadas):
    """Identifica las combinaciones de servicios sin depender del modelo."""
    assert graph._intenciones_explicitas(texto) == esperadas


def test_agente_cristian_usa_cliente_a2a(monkeypatch):
    """El nodo no importa al agente: lo consulta por HTTP/A2A."""
    llamada = {}

    async def consulta(url, texto, context_id):
        llamada.update(url=url, texto=texto, context_id=context_id)
        return "Propuesta A2A"

    monkeypatch.setattr(graph, "consultar_agente", consulta)
    respuesta = asyncio.run(
        graph._consultar_agente(
            graph.RUTA_CRISTIAN,
            "Necesito un portal web",
            {"configurable": {"thread_id": "hilo-prueba"}},
        )
    )

    assert llamada["url"] == graph.URL_AGENTES[graph.RUTA_CRISTIAN]
    assert llamada["context_id"] == "hilo-prueba"
    assert respuesta["resultados"] == [(graph.RUTA_CRISTIAN, "Propuesta A2A")]
