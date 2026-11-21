import io

import pymupdf
from PIL import Image
import pytest

from app.processing import (
    UploadProcessingError,
    image_upload_to_data_urls,
    pdf_upload_to_data_urls,
    upload_to_data_urls,
)


def test_image_is_converted_to_vision_data_url():
    output = io.BytesIO()
    Image.new("RGB", (4, 3), "white").save(output, format="JPEG")

    result = image_upload_to_data_urls(output.getvalue())

    assert len(result) == 1
    assert result[0].startswith("data:image/png;base64,")


def test_pdf_pages_are_converted_and_page_limit_is_enforced():
    document = pymupdf.open()
    document.new_page()
    document.new_page()
    content = document.tobytes()
    document.close()

    assert len(pdf_upload_to_data_urls(content, max_pages=2)) == 2
    with pytest.raises(UploadProcessingError, match="at most 1 pages"):
        pdf_upload_to_data_urls(content, max_pages=1)


def test_unsupported_upload_type_is_rejected():
    with pytest.raises(UploadProcessingError, match="image or a PDF"):
        upload_to_data_urls("notes.txt", "text/plain", b"text", max_pages=2)
