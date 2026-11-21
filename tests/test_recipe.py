import pytest
from pydantic import ValidationError

from app.recipe import Recipe


def test_recipe_accepts_schema_org_fields_and_emits_aliases():
    recipe = Recipe.model_validate({
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": "Soup",
        "recipeIngredient": ["1 cup water"],
        "recipeInstructions": [{"@type": "HowToStep", "text": "Boil water."}],
        "prepTime": "PT10M",
        "recipeYield": "4 servings",
    })

    assert recipe.to_schema_json()["@type"] == "Recipe"
    assert recipe.to_schema_json()["recipeInstructions"][0]["text"] == "Boil water."
    assert recipe.to_schema_json()["recipeYield"] == "4 servings"


def test_recipe_normalizes_single_instruction_string():
    recipe = Recipe.model_validate({
        "name": "Toast",
        "recipeIngredient": ["Bread"],
        "recipeInstructions": "Toast the bread.",
    })

    assert recipe.recipe_instructions == ["Toast the bread."]


@pytest.mark.parametrize("duration", ["30 minutes", "PT", "P1DT"])
def test_recipe_rejects_invalid_duration(duration):
    with pytest.raises(ValidationError):
        Recipe.model_validate({
            "name": "Soup",
            "recipeIngredient": ["water"],
            "recipeInstructions": ["Boil."],
            "prepTime": duration,
        })


def test_recipe_requires_ingredients_and_instructions():
    with pytest.raises(ValidationError):
        Recipe.model_validate({"name": "Incomplete"})


def test_recipe_rejects_non_schema_context():
    with pytest.raises(ValidationError):
        Recipe.model_validate({
            "@context": "https://example.com",
            "name": "Soup",
            "recipeIngredient": ["water"],
            "recipeInstructions": ["Boil."],
        })


def test_recipe_rejects_non_how_to_step_instruction_type():
    with pytest.raises(ValidationError):
        Recipe.model_validate({
            "name": "Soup",
            "recipeIngredient": ["water"],
            "recipeInstructions": [{"@type": "Thing", "text": "Boil."}],
        })
