import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.llm import LLMConfigurationError, LLMResponseError, extract_recipe
from app.processing import UploadProcessingError, upload_to_data_urls


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
