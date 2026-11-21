import json
import os
from typing import Any

import httpx

from app.recipe import Recipe


SYSTEM_PROMPT = """You extract recipes from images and PDF pages.
Return exactly one JSON object and no markdown or surrounding text. It must be
valid JSON-LD using the schema.org Recipe type, with "@context":
"https://schema.org" and "@type": "Recipe". Include "name",
"recipeIngredient" (an array of strings), and "recipeInstructions" (an array
of HowToStep objects with "@type": "HowToStep" and "text"). Include only
details visible or clearly stated in the source; never invent missing amounts,
times, yields, or ingredients. When the source states a yield or serving amount,
include it as "recipeYield" using that exact property name, never "yield".
Preserve units and wording faithfully. Use ISO 8601 durations (for example
"PT20M") for prepTime, cookTime, and totalTime when the source gives enough
information. If no recipe can be reliably read, return
{"error":"No readable recipe found"}."""

USER_PROMPT = "Extract the recipe in this document as specified. Return JSON only."


class LLMConfigurationError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


def _settings() -> tuple[str, str, str | None]:
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:8000/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "qwen3-vl")
    api_key = os.getenv("OPENAI_API_KEY")
    if not base_url or not model:
        raise LLMConfigurationError("OPENAI_BASE_URL and OPENAI_MODEL must be configured.")
    return base_url, model, api_key


async def extract_recipe(image_urls: list[str]) -> Recipe:
    base_url, model, api_key = _settings()
    content: list[dict[str, Any]] = [{"type": "text", "text": USER_PROMPT}]
    content.extend(
        {"type": "image_url", "image_url": {"url": url}}
        for url in image_urls
    )
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
    except httpx.TimeoutException as error:
        raise LLMResponseError("The vision model timed out. Please try again.") from error
    except httpx.HTTPStatusError as error:
        raise LLMResponseError(
            f"The vision model returned HTTP {error.response.status_code}."
        ) from error
    except (httpx.RequestError, json.JSONDecodeError) as error:
        raise LLMResponseError("Could not communicate with the vision model.") from error

    try:
        result = body["choices"][0]["message"]["content"]
        if isinstance(result, list):
            result = "".join(
                part.get("text", "") for part in result if isinstance(part, dict)
            )
        if not isinstance(result, str):
            raise TypeError("Model content was not text.")
        data = json.loads(result)
        if isinstance(data, dict) and "error" in data:
            raise LLMResponseError(data["error"])
        return Recipe.model_validate(data)
    except LLMResponseError:
        raise
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as error:
        raise LLMResponseError(
            "The vision model response was not valid Recipe JSON. Please try again."
        ) from error
