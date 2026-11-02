# Retail bot - StuartFairchild — Flask + Ollama + Docker Compose

A small local-first retail product-description generator. Enter a product name,
comma-separated keywords/product facts, a writing tone, and a customer segment.
The Flask app sends a constrained prompt to a local Ollama model and displays
the generated copy.

![App layout with results]("images/result.png")

## Requirements

- Docker Engine and the Docker Compose plugin
- At least 8 GB RAM is recommended for a comfortable experience with the
  default 3B model (model memory requirements vary by quantization and host)
- Internet access on first startup to download the Ollama image and model

## Start

```bash
cp .env.example .env
docker compose up -d --build
```

The first start downloads the configured model. This can take several minutes.
Open **http://localhost:5000** after the `model-init` service completes.

Check progress:

```bash
docker compose ps
docker compose logs -f ollama model-init web
```

The default model is `llama3.2:3b`. To use another model supported by Ollama,
edit `OLLAMA_MODEL` in `.env`, then run:

```bash
docker compose down
docker compose up -d
```

The Ollama model files persist in the `ollama_data` Docker volume. To remove
containers but keep the model, use `docker compose down`. To remove the model
volume too, use `docker compose down -v`.

## How it works

- `app.py`: validates inputs, applies simple customer-segment guidance, builds
  the LLM prompt, calls Ollama's `/api/generate` endpoint, and handles errors.
- `templates/index.html`: form and generated-description view.
- `static/style.css`: responsive styling.
- `docker-compose.yml`: runs Ollama, downloads the selected model once, and
  starts the Flask/Gunicorn web app.

The web app is exposed on port 5000 by default. Change `WEB_PORT` in `.env`
if that port is already in use.

## Useful commands

```bash
# Follow application logs
docker compose logs -f web

# Open a shell in the app container
docker compose exec web sh

# Check Ollama's downloaded models
docker compose exec ollama ollama list

# Generate from the Ollama container for troubleshooting
docker compose exec ollama ollama run llama3.2:3b
```

## Design notes and limitations

The customer-segment rules are intentionally transparent and deterministic:
they change the copy angle but do not make autonomous pricing, eligibility,
or customer decisions. The prompt explicitly discourages unsupported product
claims, but an LLM can still produce inaccuracies. A human should verify every
description before publication. Do not submit confidential customer data.

For production, add authentication, CSRF protection, rate limiting, structured
logging, prompt/output moderation, automated tests, and a review/approval
workflow. Consider grounding descriptions in a verified product catalog,
tracking model and prompt versions, and evaluating outputs for factuality,
accessibility, bias, and performance across customer groups.
