# Recipe Vision

A Docker-ready Python web app that extracts recipes from image or PDF uploads
using an OpenAI-compatible vision model, validates the response, and displays
and downloads it as schema.org Recipe JSON-LD.

## Run with Docker Compose

1. Copy `.env.example` to `.env`.
2. Set `OPENAI_BASE_URL` to your model server's OpenAI-compatible API base URL,
   `OPENAI_MODEL` to its vision model name, and `OPENAI_API_KEY` if required.
3. Start the app:

   ```sh
   docker compose up --build
   ```

4. Open <http://localhost:8000>.

The default base URL uses `host.docker.internal`, suitable for a model server
running on the Docker host. For a model server in another Compose service, use
that service name and port instead (for example,
`http://llm-server:8000/v1`). The server must accept OpenAI-compatible
`/chat/completions` requests with image URL content parts and JSON response
format. If it does not support `response_format`, update the provider's
configuration to support JSON mode or adapt `app/llm.py`.

## Run locally

Requires Python 3.12+:

```sh
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Set the same model environment variables before starting the server. The default
URL is `http://localhost:8000/v1`.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_BASE_URL` | `http://localhost:8000/v1` | OpenAI-compatible API base URL |
| `OPENAI_MODEL` | `qwen3-vl` | Vision model name |
| `OPENAI_API_KEY` | unset | Optional API key; sent as a bearer token when set |
| `MAX_UPLOAD_BYTES` | `15728640` | Maximum upload size in bytes (15 MiB) |
| `MAX_PDF_PAGES` | `10` | Maximum number of PDF pages sent to the model |
| `PORT` | `8000` | Host port published by Docker Compose |

Uploaded files are processed in memory and are not saved by the app. Image and
PDF pages are normalized to PNG before being sent to the configured model.
Model output is parsed and validated for a Recipe name, ingredients,
instructions, and valid ISO 8601 durations where provided. The app does not
persist uploads or extracted recipes.

## Tests

```sh
pip install -r requirements-dev.txt
pytest
```
