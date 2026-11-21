const form = document.querySelector("#upload-form");
const input = document.querySelector("#recipe-file");
const fileLabel = document.querySelector("#file-label");
const submitButton = document.querySelector("#submit-button");
const status = document.querySelector("#status");
const resultSection = document.querySelector("#result-section");
const recipeView = document.querySelector("#recipe-view");
const jsonOutput = document.querySelector("#json-output");
const downloadButton = document.querySelector("#download-button");
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
  const title = document.createElement("h3");
  title.textContent = recipe.name;
  recipeView.append(title);
  if (recipe.description) {
    const description = document.createElement("p");
    description.textContent = recipe.description;
    recipeView.append(description);
  }
  for (const [heading, key, tag] of [
    ["Ingredients", "recipeIngredient", "ul"],
    ["Instructions", "recipeInstructions", "ol"],
  ]) {
    const values = recipe[key] || [];
    const sectionTitle = document.createElement("h4");
    sectionTitle.textContent = heading;
    const list = document.createElement(tag);
    for (const value of values) {
      const item = document.createElement("li");
      item.textContent = typeof value === "string" ? value : value.text;
      list.append(item);
    }
    recipeView.append(sectionTitle, list);
  }
  const meta = ["recipeYield", "prepTime", "cookTime", "totalTime"]
    .filter((key) => recipe[key])
    .map((key) => `${key.replace("Time", " time").replace("recipeYield", "Yield")}: ${
      Array.isArray(recipe[key]) ? recipe[key].join(", ") : recipe[key]
    }`)
    .join(" · ");
  if (meta) {
    const details = document.createElement("p");
    details.className = "recipe-meta";
    details.textContent = meta;
    recipeView.append(details);
  }
}

downloadButton.addEventListener("click", () => {
  if (!currentRecipe) return;
  const blob = new Blob([`${JSON.stringify(currentRecipe, null, 2)}\n`], {
    type: "application/ld+json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${(currentRecipe.name || "recipe").replace(/[^a-z0-9_-]+/gi, "-")}.json`;
  link.click();
  URL.revokeObjectURL(url);
});
