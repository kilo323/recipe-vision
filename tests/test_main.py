import io

from fastapi.testclient import TestClient
from PIL import Image

from app import main
from app.recipe import Recipe


def test_upload_endpoint_returns_validated_recipe(monkeypatch):
    seen = {}

    async def fake_extract_recipe(image_urls):
        seen["image_urls"] = image_urls
        return Recipe(
            name="Tomato soup",
            recipeIngredient=["Tomatoes"],
            recipeInstructions=["Cook the tomatoes."],
        )

    monkeypatch.setattr(main, "extract_recipe", fake_extract_recipe)
    image = io.BytesIO()
    Image.new("RGB", (4, 3), "white").save(image, format="PNG")

    response = TestClient(main.app).post(
        "/api/recipes",
        files={"file": ("recipe.png", image.getvalue(), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["@type"] == "Recipe"
    assert response.json()["name"] == "Tomato soup"
    assert seen["image_urls"][0].startswith("data:image/png;base64,")


def test_upload_endpoint_rejects_unsupported_file():
    response = TestClient(main.app).post(
        "/api/recipes",
        files={"file": ("notes.txt", b"not a recipe image", "text/plain")},
    )

    assert response.status_code == 422
    assert "image or a PDF" in response.json()["detail"]


def test_mealie_import_requires_configuration(monkeypatch):
    monkeypatch.delenv("MEALIE_URL", raising=False)
    monkeypatch.delenv("MEALIE_API_TOKEN", raising=False)

    response = TestClient(main.app).post(
        "/api/mealie/import",
        json={
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Soup",
            "recipeIngredient": ["water"],
            "recipeInstructions": [{"@type": "HowToStep", "text": "Boil."}],
        },
    )

    assert response.status_code == 503
    assert "MEALIE_URL" in response.json()["detail"]
