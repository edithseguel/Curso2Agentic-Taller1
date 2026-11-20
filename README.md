# Curso2Agentic-Taller1

Sistema de cotizaciones TI basado en agentes A2A. Un coordinador recibe cada
consulta y la deriva al agente especializado:

- **Edith:** outsourcing de personal TI.
- **Cristian:** desarrollo de software.
- **Rodrigo:** minería y análisis de datos.

Además expone una API FastAPI con Swagger y una colección Bruno para probarla.

## Requisitos y configuración

Se requiere Python 3.12 o superior. Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y completa al menos `GOOGLE_API_KEY`, `MODELO`, `vhorahom` y las
tarifas `vh_perf_*`. No subas `.env`: contiene secretos y está ignorado por Git.

`.env.example` documenta todas las variables que usa el código: clave y modelo
de Gemini, tarifas, URL de cada agente y URL del coordinador.

## Correr el coordinador en local

Abre cuatro terminales en la raíz del proyecto, activa el entorno virtual en
cada una con `source .venv/bin/activate` y levanta los tres agentes:

```bash
uvicorn src.agente_Edith_outsourcing_ti.server:app --port 8001
```

```bash
uvicorn src.agente_Cristian_desarrollo_ti.server:app --port 8002
```

```bash
uvicorn src.agente_Rodrigo_mineria_de_datos.server:app --port 8003
```

En la cuarta terminal puedes consultar el coordinador directamente:

```bash
python main.py coordinador "Necesito cotizar dos desarrolladores Python por seis meses"
```

Para ver los saltos:

```bash
python main.py coordinador "Necesito cotizar una aplicación web" --saltos
```

El servidor A2A del coordinador, si lo necesitas, se levanta así:

```bash
uvicorn src.coordinador.server:app --port 8004
```

## Levantar la API

Con los tres agentes activos, inicia la API:

```bash
uvicorn api.app:app --reload --port 8000
```

Abre Swagger en <http://localhost:8000/docs>. Prueba una consulta con:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"cliente-123","texto":"Necesito dos desarrolladores Python por seis meses."}'
```

La colección está en `bruno/`. Selecciona el entorno `Local` y modifica
`base_url` para alternar entre el servidor local y Heroku.

## Pruebas

Ejecuta las pruebas automatizadas con:

```bash
python -m pytest
```

También puedes comprobar que la API está disponible:

```bash
curl http://localhost:8000/health
```

## Despliegue en Heroku

Heroku asigna un único puerto por aplicación. Por eso debes desplegar **cuatro
aplicaciones**: una por agente y una para la API. Instala e inicia sesión en
Heroku CLI antes de ejecutar:

```bash
heroku login
heroku create cotizaciones-edith-tu-identificador
heroku create cotizaciones-cristian-tu-identificador
heroku create cotizaciones-rodrigo-tu-identificador
heroku create cotizaciones-api-tu-identificador
```

Configura las variables de Gemini y tarifas en cada aplicación que use modelo:

```bash
heroku config:set GOOGLE_API_KEY="tu-clave" MODELO="gemini-3.5-flash-lite" vhorahom="1" vh_perf_prog="1" vh_perf_progfs="1" vh_perf_dba="1" vh_perf_prognet="1" vh_perf_qa="1" vh_perf_analis="1" -a cotizaciones-edith-tu-identificador
heroku config:set GOOGLE_API_KEY="tu-clave" MODELO="gemini-3.5-flash-lite" vhorahom="1" -a cotizaciones-cristian-tu-identificador
heroku config:set GOOGLE_API_KEY="tu-clave" MODELO="gemini-3.5-flash-lite" vhorahom="1" -a cotizaciones-rodrigo-tu-identificador
```

Indica qué módulo debe iniciar cada aplicación y publica el mismo repositorio
en cada remoto:

```bash
heroku config:set APP_MODULE=src.agente_Edith_outsourcing_ti.server -a cotizaciones-edith-tu-identificador
heroku config:set APP_MODULE=src.agente_Cristian_desarrollo_ti.server -a cotizaciones-cristian-tu-identificador
heroku config:set APP_MODULE=src.agente_Rodrigo_mineria_de_datos.server -a cotizaciones-rodrigo-tu-identificador
heroku config:set APP_MODULE=api.app -a cotizaciones-api-tu-identificador
git push https://git.heroku.com/cotizaciones-edith-tu-identificador.git main
git push https://git.heroku.com/cotizaciones-cristian-tu-identificador.git main
git push https://git.heroku.com/cotizaciones-rodrigo-tu-identificador.git main
git push https://git.heroku.com/cotizaciones-api-tu-identificador.git main
```

Finalmente conecta la API con los tres agentes desplegados:

```bash
heroku config:set URL_OUTSOURCING=https://cotizaciones-edith-tu-identificador.herokuapp.com URL_DESARROLLO=https://cotizaciones-cristian-tu-identificador.herokuapp.com URL_MINERIA=https://cotizaciones-rodrigo-tu-identificador.herokuapp.com -a cotizaciones-api-tu-identificador
```

Visita `https://cotizaciones-api-tu-identificador.herokuapp.com/docs`.

## Conectar Telegram

Actualmente `POST /telegram` confirma la recepción con `{"ok": true}`, pero
todavía no procesa ni responde mensajes. Para dejar el webhook preparado,
después de desplegar la API en una URL pública HTTPS, crea un bot con
[@BotFather](https://t.me/BotFather) y ejecuta:

```bash
curl -X POST "https://api.telegram.org/botTU_TOKEN_DE_BOT/setWebhook" \
  -d "url=https://cotizaciones-api-tu-identificador.herokuapp.com/telegram"
```

Comprueba el webhook con:

```bash
curl "https://api.telegram.org/botTU_TOKEN_DE_BOT/getWebhookInfo"
```

No guardes el token del bot en Git. La lógica para leer y responder mensajes se
incorporará en la siguiente parte del proyecto.
