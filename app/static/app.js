const form = document.querySelector("#upload-form");
const input = document.querySelector("#recipe-file");
const fileLabel = document.querySelector("#file-label");
const submitButton = document.querySelector("#submit-button");
const status = document.querySelector("#status");
const resultSection = document.querySelector("#result-section");
const recipeView = document.querySelector("#recipe-view");
const jsonOutput = document.querySelector("#json-output");
const downloadButton = document.querySelector("#download-button");
const mealieButton = document.querySelector("#mealie-button");
const importStatus = document.querySelector("#import-status");
let currentRecipe = null;

input.addEventListener("change", () => {
  fileLabel.textContent = input.files[0]?.name || "Choose an image or PDF";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!input.files.length) return;

  submitButton.disabled = true;
  status.textContent = "Reading your recipe…";
  status.className = "status";
  resultSection.hidden = true;

  try {
    const body = new FormData();
    body.append("file", input.files[0]);
    const response = await fetch("/api/recipes", { method: "POST", body });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Recipe extraction failed.");

    currentRecipe = result;
    renderRecipe(result);
    jsonOutput.textContent = JSON.stringify(result, null, 2);
    resultSection.hidden = false;
    status.textContent = "Recipe extracted and validated.";
    status.classList.add("success");
  } catch (error) {
    status.textContent = error.message || "Something went wrong. Please try again.";
    status.classList.add("error");
  } finally {
    submitButton.disabled = false;
  }
});
function renderRecipe(recipe) {
  recipeView.replaceChildren();
  const title = createTextInput(recipe.name || "", "Recipe name");
  title.className = "preview-name";
  title.addEventListener("input", syncRecipeFromPreview);
  recipeView.append(title);

  const description = createTextArea(recipe.description || "", "Description");
  description.className = "preview-description";
  description.placeholder = "Add a description";
  description.addEventListener("input", syncRecipeFromPreview);
  recipeView.append(description);

  for (const [heading, key, tag] of [
    ["Ingredients", "recipeIngredient", "ul"],
    ["Instructions", "recipeInstructions", "ol"],
  ]) {
    const values = recipe[key] || [];
    const sectionTitle = document.createElement("h4");
    sectionTitle.textContent = heading;
    const list = document.createElement(tag);
    list.className = "preview-list";
    for (const value of values) {
      const item = document.createElement("li");
      const row = document.createElement("div");
      row.className = "preview-list-row";
      const text = createTextArea(
        typeof value === "string" ? value : value.text || "",
        heading === "Ingredients" ? "Ingredient" : "Instruction",
      );
      text.className = "preview-list-text";
      text.addEventListener("input", syncRecipeFromPreview);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "preview-remove";
      remove.textContent = "Remove";
      remove.addEventListener("click", () => {
        item.remove();
        syncRecipeFromPreview();
      });
      row.append(text, remove);
      item.append(row);
      list.append(item);
    }
    const add = document.createElement("button");
    add.type = "button";
    add.className = "preview-add secondary";
    add.textContent = heading === "Ingredients" ? "Add ingredient" : "Add instruction";
    add.addEventListener("click", () => {
      const item = document.createElement("li");
      const row = document.createElement("div");
      row.className = "preview-list-row";
      const text = createTextArea("", heading === "Ingredients" ? "Ingredient" : "Instruction");
      text.className = "preview-list-text";
      text.addEventListener("input", syncRecipeFromPreview);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "preview-remove";
      remove.textContent = "Remove";
      remove.addEventListener("click", () => {
        item.remove();
        syncRecipeFromPreview();
      });
      row.append(text, remove);
      item.append(row);
      list.append(item);
      text.focus();
      syncRecipeFromPreview();
    });
    recipeView.append(sectionTitle, list, add);
  }

  const meta = document.createElement("div");
  meta.className = "preview-meta";
  for (const [key, label, placeholder] of [
    ["recipeYield", "Yield", "4 servings"],
    ["prepTime", "Prep time", "PT20M"],
    ["cookTime", "Cook time", "PT30M"],
    ["totalTime", "Total time", "PT50M"],
  ]) {
    const field = document.createElement("label");
    field.textContent = `${label}`;
    const value = Array.isArray(recipe[key]) ? recipe[key].join(", ") : recipe[key] || "";
    const input = createTextInput(value, placeholder);
    input.dataset.recipeKey = key;
    input.placeholder = placeholder;
    input.addEventListener("input", syncRecipeFromPreview);
    field.append(input);
    meta.append(field);
  }
  recipeView.append(meta);
}

function createTextInput(value, ariaLabel) {
  const input = document.createElement("input");
  input.type = "text";
  input.value = value;
  input.setAttribute("aria-label", ariaLabel);
  return input;
}

function createTextArea(value, ariaLabel) {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.rows = 2;
  textarea.setAttribute("aria-label", ariaLabel);
  return textarea;
}

function syncRecipeFromPreview() {
  if (!currentRecipe) return null;
  const name = recipeView.querySelector(".preview-name")?.value.trim();
  const description = recipeView.querySelector(".preview-description")?.value.trim();
  const headings = [...recipeView.querySelectorAll("h4")];
  const ingredientsHeading = headings.find((heading) => heading.textContent === "Ingredients");
  const instructionsHeading = headings.find((heading) => heading.textContent === "Instructions");
  const ingredients = ingredientsHeading
    ? [...ingredientsHeading.nextElementSibling.querySelectorAll(".preview-list-text")]
      .map((input) => input.value.trim())
      .filter(Boolean)
    : [];
  const instructions = instructionsHeading
    ? [...instructionsHeading.nextElementSibling.querySelectorAll(".preview-list-text")]
      .map((input) => input.value.trim())
      .filter(Boolean)
      .map((text) => ({ "@type": "HowToStep", text }))
    : [];

  if (!name || !ingredients.length || !instructions.length) {
    importStatus.textContent = "Name, ingredients, and instructions are required.";
    importStatus.className = "status error";
    return null;
  }

  const updated = {
    ...currentRecipe,
    name,
    recipeIngredient: ingredients,
    recipeInstructions: instructions,
  };
  if (description) updated.description = description;
  else delete updated.description;

  for (const input of recipeView.querySelectorAll(".preview-meta input")) {
    const value = input.value.trim();
    if (value) updated[input.dataset.recipeKey] = value;
    else delete updated[input.dataset.recipeKey];
  }
  currentRecipe = updated;
  jsonOutput.textContent = JSON.stringify(updated, null, 2);
  importStatus.textContent = "";
  importStatus.className = "status";
  return updated;
}

downloadButton.addEventListener("click", () => {
  let recipe;
  try {
    recipe = syncRecipeFromPreview();
  } catch (error) {
    status.textContent = error.message;
    status.className = "status error";
    return;
  }
  if (!recipe) return;
  const blob = new Blob([`${JSON.stringify(recipe, null, 2)}\n`], {
    type: "application/ld+json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${(recipe.name || "recipe").replace(/[^a-z0-9_-]+/gi, "-")}.json`;
  link.click();
  URL.revokeObjectURL(url);
});

mealieButton.addEventListener("click", async () => {
  let recipe;
  try {
    recipe = syncRecipeFromPreview();
  } catch (error) {
    importStatus.textContent = error.message;
    importStatus.className = "status error";
    return;
  }
  if (!recipe) return;

  mealieButton.disabled = true;
  const mealieWindow = window.open("", "_blank");
  if (mealieWindow) mealieWindow.opener = null;
  importStatus.textContent = "Importing into Mealie…";
  importStatus.className = "status";
  try {
    const response = await fetch("/api/mealie/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(recipe),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Mealie import failed.");
    importStatus.textContent = "Imported into Mealie. Opening the recipe in edit mode…";
    importStatus.className = "status success";
    if (mealieWindow) {
      mealieWindow.location.href = result.editUrl;
    } else {
      window.location.href = result.editUrl;
    }
  } catch (error) {
    if (mealieWindow) mealieWindow.close();
    importStatus.textContent = error.message || "Could not import the recipe.";
    importStatus.className = "status error";
  } finally {
    mealieButton.disabled = false;
  }
});
