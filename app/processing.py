import base64
import io
from collections.abc import Sequence

import pymupdf
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_IMAGE_DIMENSION = 4096
PDF_RENDER_SCALE = 1.5


class UploadProcessingError(ValueError):
    pass


def _image_data_url(image: Image.Image) -> str:
    image = ImageOps.exif_transpose(image)
    image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def image_upload_to_data_urls(contents: bytes) -> list[str]:
    try:
        with Image.open(io.BytesIO(contents)) as image:
            image.load()
            return [_image_data_url(image.copy())]
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise UploadProcessingError("The uploaded file is not a readable image.") from error


def pdf_upload_to_data_urls(contents: bytes, max_pages: int) -> list[str]:
    try:
        with pymupdf.open(stream=contents, filetype="pdf") as document:
            if document.is_encrypted:
                raise UploadProcessingError("Password-protected PDFs are not supported.")
            if document.page_count == 0:
                raise UploadProcessingError("The PDF contains no pages.")
            if document.page_count > max_pages:
                raise UploadProcessingError(f"PDFs may contain at most {max_pages} pages.")

            urls = []
            matrix = pymupdf.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE)
            for page in document:
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
                    urls.append(_image_data_url(image))
            return urls
    except UploadProcessingError:
        raise
    except (pymupdf.FileDataError, RuntimeError, ValueError) as error:
        raise UploadProcessingError("The uploaded PDF could not be read.") from error


def upload_to_data_urls(
    filename: str,
    content_type: str | None,
    contents: bytes,
    max_pages: int,
) -> Sequence[str]:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if content_type == "application/pdf" or extension == "pdf":
        return pdf_upload_to_data_urls(contents, max_pages)
    if (content_type or "").startswith("image/") or extension in {
        "jpg", "jpeg", "png", "webp", "gif", "bmp", "tif", "tiff",
    }:
        return image_upload_to_data_urls(contents)
    raise UploadProcessingError("Upload an image or a PDF document.")
