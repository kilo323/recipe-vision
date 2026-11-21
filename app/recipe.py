import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_DURATION_PATTERN = re.compile(
    r"^P(?=\d|T\d)(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?=\d)(?:\d+H)?(?:\d+M)?(?:\d+S)?)?$"
)


class HowToStep(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = Field(default="HowToStep", alias="@type")
    text: str = Field(min_length=1)
    name: str | None = None

    @field_validator("type")
    @classmethod
    def how_to_step_type_only(cls, value: str) -> str:
        if value != "HowToStep":
            raise ValueError('@type must be "HowToStep"')
        return value


class Recipe(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    context: str = Field(default="https://schema.org", alias="@context")
    type: str = Field(default="Recipe", alias="@type")
    name: str = Field(min_length=1)
    description: str | None = None
    recipe_ingredient: list[str] = Field(min_length=1, alias="recipeIngredient")
    recipe_instructions: list[HowToStep | str] = Field(min_length=1, alias="recipeInstructions")
    recipe_yield: str | list[str] | None = Field(default=None, alias="recipeYield")
    prep_time: str | None = Field(default=None, alias="prepTime")
    cook_time: str | None = Field(default=None, alias="cookTime")
    total_time: str | None = Field(default=None, alias="totalTime")
    recipe_category: str | list[str] | None = Field(default=None, alias="recipeCategory")
    recipe_cuisine: str | list[str] | None = Field(default=None, alias="recipeCuisine")
    keywords: str | list[str] | None = None

    @field_validator("context")
    @classmethod
    def schema_context_only(cls, value: str) -> str:
        if value != "https://schema.org":
            raise ValueError('@context must be "https://schema.org"')
        return value

    @field_validator("type")
    @classmethod
    def recipe_type_only(cls, value: str) -> str:
        if value != "Recipe":
            raise ValueError('@type must be "Recipe"')
        return value

    @field_validator("prep_time", "cook_time", "total_time")
    @classmethod
    def validate_duration(cls, value: str | None) -> str | None:
        if value is not None and not _DURATION_PATTERN.fullmatch(value):
            raise ValueError("must be an ISO 8601 duration, such as PT30M")
        return value

    @model_validator(mode="before")
    @classmethod
    def normalize_instructions(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result = dict(value)
        instructions = result.get("recipeInstructions")
        if isinstance(instructions, str):
            result["recipeInstructions"] = [instructions]
        return result

    def to_schema_json(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)
