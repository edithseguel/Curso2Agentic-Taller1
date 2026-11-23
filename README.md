# Curso2Agentic-Taller1 · Cotizaciones TI

Sistema de cotizaciones TI basado en agentes A2A. El coordinador FastAPI recibe
una consulta desde la UI web o Telegram, valida el acceso y deriva la solicitud
por HTTP/A2A al o los especialistas correspondientes.

- **Cristian:** desarrollo de software.
- **Edith:** outsourcing de personal TI.
- **Rodrigo:** minería y análisis de datos.

## Integrantes y aportes

| Integrante | Aporte principal |
| --- | --- |
| Edith Seguel | Agente de Outsourcing, catálogo y cálculo de perfiles, canal Telegram. |
| Cristian Rioseco | Agente de Desarrollo TI, herramientas de planificación y cotización. |
| Rodrigo Salas | Agente de Minería de Datos, planificación y cotización analítica. |
| Grupo 2 | Coordinador A2A, UI FastAPI, pruebas, documentación y despliegue. |

## Arquitectura

La aplicación coordinadora usa Agent Cards y A2A HTTP para comunicarse con tres
aplicaciones independientes:

| Componente | Repositorio |
| --- | --- |
| Coordinador y UI | Este repositorio. |
| Agente Edith | <https://github.com/edithseguel/Curso2Agentic-Agente-Edith> |
| Agente Cristian | <https://github.com/edithseguel/Curso2Agentic-Agente-Cristian> |
| Agente Rodrigo | <https://github.com/edithseguel/Curso2Agentic-Agente-Rodrigo> |

El coordinador conserva las cifras, unidades y plazos de cada agente y entrega
las propuestas en secciones separadas. Las cotizaciones son referenciales y
requieren validación humana.

## Requisitos y configuración local

Se requiere Python 3.12, acceso a internet para Gemini y una clave propia de
Google. Desde la raíz:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

En `.env` configura, sin publicar valores reales:

```env
GOOGLE_API_KEY=tu_clave_de_gemini
MODELO=gemini-3.5-flash-lite
TOKEN_ACCESO_CHAT=token_largo_y_aleatorio
URL_EDITH_OUTSOURCING_TI=http://127.0.0.1:8001
URL_CRISTIAN_DESARROLLO_TI=http://127.0.0.1:8002
URL_RODRIGO_MINERIA_DE_DATOS=http://127.0.0.1:8003
```

Genera el token con:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

No subas `.env`, tokens, claves, cookies ni sesiones. `.env.example` contiene
solo nombres de variables y valores ficticios.

## Ejecución local reproducible

Abre cuatro terminales en la raíz, activa el entorno virtual en cada una y
levanta los tres agentes:

```bash
uvicorn src.agente_Edith_outsourcing_ti.server:app --port 8001
uvicorn src.agente_Cristian_desarrollo_ti.server:app --port 8002
uvicorn src.agente_Rodrigo_mineria_de_datos.server:app --port 8003
```

En una cuarta terminal inicia la UI/API:

```bash
uvicorn api.app:app --port 8000
```

Abre <http://127.0.0.1:8000/>. Ingresa el valor de `TOKEN_ACCESO_CHAT` y realiza
una consulta. Para detener cualquier componente utiliza `Ctrl+C`.

También puedes inspeccionar los saltos del coordinador:

```bash
python main.py coordinador "Necesito un portal web, 2 analistas QA por 3 meses y un análisis de incidentes" --saltos
```

## Pruebas de API y seguridad

Swagger está disponible en <http://127.0.0.1:8000/docs>. Ejemplo autorizado:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Token-Acceso: $TOKEN_ACCESO_CHAT" \
  -d '{"user_id":"cliente-prueba","texto":"Necesito un portal web para proveedores durante 3 meses."}'
```

Prueba de rechazo, sin mostrar ni enviar el token:

```bash
curl -i -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"cliente-prueba","texto":"Necesito un portal web."}'
```

El primer caso retorna `200`; el segundo retorna `401`. Si no se configuró
`TOKEN_ACCESO_CHAT`, la API retorna `503`. Si no es posible contactar un
agente A2A o el proveedor, la API retorna `502` con un mensaje seguro.

Ejecuta las pruebas automatizadas:

```bash
python -m pytest
```

## Publicación opcional en Heroku

Heroku utiliza un puerto por aplicación. Publica el coordinador y los tres
agentes como aplicaciones separadas. Cada agente se despliega desde su propio
repositorio GitHub y debe tener estas variables:

| Agente | Variables requeridas |
| --- | --- |
| Edith | `GOOGLE_API_KEY`, `MODELO`, `URL_EDITH_OUTSOURCING_TI` |
| Cristian | `GOOGLE_API_KEY`, `MODELO`, `URL_CRISTIAN_DESARROLLO_TI` |
| Rodrigo | `GOOGLE_API_KEY`, `MODELO`, `URL_RODRIGO_MINERIA_DE_DATOS` |

En cada repositorio de agente, Heroku ejecuta el `Procfile` incluido. Después
de desplegar, verifica su Agent Card:

```text
https://NOMBRE-DE-LA-APP.herokuapp.com/.well-known/agent-card.json
```

En la aplicación coordinadora configura las URL base públicas de los tres
agentes, sin agregar rutas como `/docs` ni `/.well-known/agent-card.json`:

```env
URL_EDITH_OUTSOURCING_TI=https://APP-EDITH.herokuapp.com
URL_CRISTIAN_DESARROLLO_TI=https://APP-CRISTIAN.herokuapp.com
URL_RODRIGO_MINERIA_DE_DATOS=https://APP-RODRIGO.herokuapp.com
TOKEN_ACCESO_CHAT=token_largo_y_aleatorio
GOOGLE_API_KEY=tu_clave_de_gemini
MODELO=gemini-3.5-flash-lite
```

Guarda las variables y reinicia la aplicación coordinadora. Si en los logs
aparece `127.0.0.1:8001`, `8002` o `8003`, falta configurar la URL pública del
agente respectivo en el coordinador.

## Telegram

Telegram es un canal complementario. Configura en la aplicación coordinadora:

```env
TELEGRAM_TOKEN=token_del_bot
TELEGRAM_SECRET=secreto_largo_aleatorio
TELEGRAM_ALLOWED_CHAT_IDS=123456789,987654321
PUBLIC_URL=https://NOMBRE-COORDINADOR.herokuapp.com
```

`TELEGRAM_ALLOWED_CHAT_IDS` contiene solo identificadores numéricos de cuentas
autorizadas, separados por coma. Una lista vacía permite cualquier chat que
llegue con el secreto del webhook; para pruebas controladas se debe definir al
menos un ID autorizado.

Con las mismas variables en el entorno local, registra y revisa el webhook:

```bash
python scripts/set_webhook.py
python scripts/webhook_info.py
```

Prueba autorizada: envía desde un `chat_id` incluido una solicitud de
cotización y verifica la respuesta del bot junto a un `POST /telegram 200` en
los logs. Prueba rechazada: usa una cuenta no incluida y verifica el `403`.
No incluyas tokens, secretos, IDs completos ni correos en las capturas.

## Límites y dependencias externas

Gemini, Telegram y Heroku requieren conexión, cuentas y credenciales propias.
Las propuestas son referenciales; los supuestos, alcance definitivo y
aprobación requieren validación humana. El evaluador puede utilizar sus propias
credenciales o solicitar acceso de prueba mediante un canal privado.
