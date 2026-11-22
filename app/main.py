import json
import os
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import ValidationError

from app.llm import LLMConfigurationError, LLMResponseError, extract_recipe
from app.processing import UploadProcessingError, upload_to_data_urls
from app.recipe import Recipe


MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "10"))

app = FastAPI(title="Recipe Vision", version="1.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024)},
    )


@app.post("/api/recipes")
async def create_recipe(file: UploadFile = File(...)) -> JSONResponse:
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Files must be {MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller.",
        )

    try:
        image_urls = upload_to_data_urls(
            filename=file.filename or "",
            content_type=file.content_type,
            contents=contents,
            max_pages=MAX_PDF_PAGES,
        )
        recipe = await extract_recipe(list(image_urls))
    except UploadProcessingError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        await file.close()

    return JSONResponse(content=recipe.to_schema_json())


@app.post("/api/mealie/import")
async def import_recipe_into_mealie(recipe_data: dict[str, Any]) -> JSONResponse:
    mealie_url = os.getenv("MEALIE_URL", "").strip().rstrip("/")
    mealie_token = os.getenv("MEALIE_API_TOKEN", "").strip()
    if not mealie_url or not mealie_token:
        raise HTTPException(
            status_code=503,
            detail="Mealie is not configured. Set MEALIE_URL and MEALIE_API_TOKEN.",
        )

    try:
        recipe = Recipe.model_validate(recipe_data)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=f"Invalid recipe JSON: {error}") from error

    json_string = json.dumps(recipe.to_schema_json(), ensure_ascii=False)
    headers = {"Authorization": f"Bearer {mealie_token}"}
    payload = {
        "data": json_string,
        "includeTags": True,
        "includeCategories": True,
        "url": None,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            create_response = await client.post(
                f"{mealie_url}/api/recipes/create/html-or-json",
                headers=headers,
                json=payload,
            )
            create_response.raise_for_status()
            slug = create_response.json()
            if not isinstance(slug, str) or not slug:
                raise LLMResponseError("Mealie did not return a recipe slug.")

            user_response = await client.get(
                f"{mealie_url}/api/users/self",
                headers=headers,
            )
            user_response.raise_for_status()
            group_slug = user_response.json().get("groupSlug")
            if not group_slug:
                raise LLMResponseError("Mealie did not return a group slug.")
    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="The Mealie API timed out.") from error
    except httpx.HTTPStatusError as error:
        detail = "The Mealie API rejected the recipe."
        try:
            response_detail = error.response.json().get("detail")
            if response_detail:
                detail = str(response_detail)
        except (ValueError, AttributeError):
            pass
        raise HTTPException(status_code=502, detail=detail) from error
    except httpx.RequestError as error:
        raise HTTPException(status_code=502, detail="Could not communicate with Mealie.") from error
    except LLMResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    edit_url = f"{mealie_url}/g/{group_slug}/r/{slug}?edit=true"
    return JSONResponse(content={"slug": slug, "editUrl": edit_url})
