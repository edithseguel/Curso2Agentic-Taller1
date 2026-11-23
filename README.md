# Curso2Agentic-Taller1

Sistema de cotizaciones TI basado en agentes A2A. Un coordinador recibe cada
consulta y la deriva al agente especializado:

- **Edith:** outsourcing de personal TI.
- **Cristian:** desarrollo de software.
- **Rodrigo:** minería y análisis de datos.

Además expone una API FastAPI con interfaz web, Swagger y una colección Bruno
para probarla. El coordinador consulta los tres especialistas mediante Agent
Cards y A2A HTTP; por eso los agentes deben estar activos antes de cotizar.

## Requisitos y configuración

Se requiere Python 3.12 o superior. Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y completa `GOOGLE_API_KEY`, `MODELO` y un
`TOKEN_ACCESO_CHAT` aleatorio. Las horas y tarifas base
de cotización están definidas en los archivos `conocimiento.py` de cada
agente. No subas `.env`: contiene secretos y está ignorado por Git.

`.env.example` documenta todas las variables que usa el código: clave y modelo
de Gemini, tarifas, URL de cada agente y URL del coordinador.

`TOKEN_ACCESO_CHAT` se valida exclusivamente en el servidor para proteger
`POST /chat`. No se debe guardar en el repositorio, en capturas ni en el código
frontend. La interfaz web lo solicita para la sesión actual y lo envía en el
header `X-Token-Acceso`.

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
  -H "X-Token-Acceso: $TOKEN_ACCESO_CHAT" \
  -d '{"user_id":"cliente-123","texto":"Necesito dos desarrolladores Python por seis meses."}'
```

Una solicitud sin token o con token incorrecto devuelve `401`. Si el servidor
no tiene configurado `TOKEN_ACCESO_CHAT`, devuelve `503` y no abre el chat.
Si un agente A2A o el proveedor falla, el endpoint devuelve `502` con un
mensaje seguro en una sola línea.

La colección está en `bruno/`. Selecciona el entorno `Local` y modifica
`base_url` para alternar entre el servidor local y Heroku.

## Pruebas

Ejecuta las pruebas automatizadas con:

```bash
python -m pytest
```

Las pruebas cubren acceso autorizado/rechazado, ausencia de configuración,
enrutamiento de uno/tres servicios y la delegación A2A HTTP.

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
heroku config:set GOOGLE_API_KEY="tu-clave" MODELO="gemini-3.5-flash-lite" -a cotizaciones-edith-tu-identificador
heroku config:set GOOGLE_API_KEY="tu-clave" MODELO="gemini-3.5-flash-lite" -a cotizaciones-cristian-tu-identificador
heroku config:set GOOGLE_API_KEY="tu-clave" MODELO="gemini-3.5-flash-lite" -a cotizaciones-rodrigo-tu-identificador
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
heroku config:set URL_OUTSOURCING=https://cotizaciones-edith-tu-identificador.herokuapp.com URL_DESARROLLO=https://cotizaciones-cristian-tu-identificador.herokuapp.com URL_MINERIA=https://cotizaciones-rodrigo-tu-identificador.herokuapp.com TOKEN_ACCESO_CHAT="TOKEN_LARGO_ALEATORIO" -a cotizaciones-api-tu-identificador
```

Visita `https://cotizaciones-api-tu-identificador.herokuapp.com/docs`.

## Conectar Telegram

La API recibe los mensajes en `POST /telegram`, valida el secreto del webhook,
los deriva al coordinador usando el `chat_id` como memoria de conversación y
responde con la API HTTP de Telegram. No se usa ninguna librería de bot.
Para limitar quién puede usar el bot, configura opcionalmente
`TELEGRAM_ALLOWED_CHAT_IDS` con los identificadores autorizados separados por
coma; un chat no incluido recibe `403`.

1. Crea el bot con [@BotFather](https://t.me/BotFather), mediante `/newbot`,
   y copia el token. Elige también un secreto difícil de adivinar.

2. Configura las credenciales en la aplicación de API de Heroku:

```bash
heroku config:set TELEGRAM_TOKEN="TU_TOKEN_DE_BOT" TELEGRAM_SECRET="TU_SECRETO" -a cotizaciones-api-tu-identificador
```

3. Guarda y publica los cambios tanto en GitHub como en Heroku:

```bash
git add api/app.py scripts .env.example README.md
git commit -m "conectar webhook de Telegram"
git push origin main
git push https://git.heroku.com/cotizaciones-api-tu-identificador.git main
```

4. Registra el webhook y comprueba su estado. Ejecuta estos comandos desde la
   raíz, con las credenciales disponibles en tu entorno local:

```bash
PUBLIC_URL="https://cotizaciones-api-tu-identificador.herokuapp.com" python scripts/set_webhook.py
PUBLIC_URL="https://cotizaciones-api-tu-identificador.herokuapp.com" python scripts/webhook_info.py
```

5. Escribe al bot los seis mensajes del *prompt 2*. Revisa que cada consulta
   siguió su ruta correcta en los logs:

```bash
heroku logs --tail -a cotizaciones-api-tu-identificador
```

Si el bot no responde, verifica que el webhook apunte a
`https://.../telegram`, que el secreto sea idéntico en Heroku y en Telegram,
y que el token sea correcto.

Para probar antes de desplegar, abre un túnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

Usa la URL HTTPS que entrega Cloudflare como `PUBLIC_URL` al ejecutar los
scripts. No guardes el token ni el secreto en Git.
# Curso2Agentic-Taller1
