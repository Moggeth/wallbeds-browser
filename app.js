const state = {
  products: [],
  categories: [],
  selectedCategory: "All",
  query: "",
};

const productsEl = document.querySelector("#products");
const filtersEl = document.querySelector("#categoryFilters");
const searchEl = document.querySelector("#search");
const resultCountEl = document.querySelector("#resultCount");

const normalise = (value) => String(value || "").toLowerCase();

const escapeHtml = (value) =>
  String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

function searchableText(product) {
  const attributes = product.attributes
    .map((attribute) => `${attribute.name} ${attribute.values.join(" ")}`)
    .join(" ");
  return normalise(`${product.name} ${product.summary} ${product.categories.join(" ")} ${attributes}`);
}

function filteredProducts() {
  return state.products.filter((product) => {
    const matchesCategory =
      state.selectedCategory === "All" || product.categories.includes(state.selectedCategory);
    const matchesQuery = !state.query || searchableText(product).includes(normalise(state.query));
    return matchesCategory && matchesQuery;
  });
}

function renderFilters() {
  const categories = ["All", ...state.categories];
  filtersEl.innerHTML = categories
    .map(
      (category) => `
        <button class="chip" type="button" aria-pressed="${category === state.selectedCategory}" data-category="${escapeHtml(category)}">
          ${escapeHtml(category)}
        </button>
      `
    )
    .join("");
}

function renderMeta(product) {
  const rows = [];
  if (product.categories.length) {
    rows.push(["Category", product.categories.join(", ")]);
  }
  for (const attribute of product.attributes) {
    rows.push([attribute.name, attribute.values.join(", ")]);
  }
  if (!rows.length) return "";
  return `
    <dl class="meta-list">
      ${rows
        .map(
          ([label, value]) => `
            <div>
              <dt>${escapeHtml(label)}</dt>
              <dd>${escapeHtml(value)}</dd>
            </div>
          `
        )
        .join("")}
    </dl>
  `;
}

function renderProducts() {
  const products = filteredProducts();
  resultCountEl.textContent = `${products.length} of ${state.products.length} products shown`;

  if (!products.length) {
    productsEl.innerHTML = `<p class="empty">No products match that search.</p>`;
    return;
  }

  productsEl.innerHTML = products
    .map((product) => {
      const image = product.image?.src || "";
      const brochure = (product.sourceLinks || []).find((link) => /brochure/i.test(link.label));
      const brochureLink = brochure
        ? `<a class="secondary-link" href="${escapeHtml(brochure.url)}" rel="noopener">Open brochure</a>`
        : `<a class="secondary-link" href="tel:1300663660">Call 1300 663 660</a>`;
      return `
        <article class="product-card">
          <img class="product-image" src="${escapeHtml(image)}" alt="${escapeHtml(product.image?.alt || product.name)}" loading="lazy">
          <div class="product-body">
            <div class="product-top">
              <h2 class="product-title">${escapeHtml(product.name)}</h2>
              <div class="price-row">
                <span class="price">${escapeHtml(product.price || "Check price")}</span>
                <span class="stock">${escapeHtml(product.stockText || "Check availability")}</span>
              </div>
            </div>
            ${product.summary ? `<p class="summary">${escapeHtml(product.summary)}</p>` : ""}
            ${renderMeta(product)}
            <div class="actions">
              <a class="primary-link" href="${escapeHtml(product.url)}" rel="noopener">View official product</a>
              ${brochureLink}
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

function bindEvents() {
  filtersEl.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-category]");
    if (!button) return;
    state.selectedCategory = button.dataset.category;
    renderFilters();
    renderProducts();
  });

  searchEl.addEventListener("input", () => {
    state.query = searchEl.value.trim();
    renderProducts();
  });
}

async function init() {
  const response = await fetch("data/products.json");
  if (!response.ok) throw new Error("Unable to load product data");
  const data = await response.json();
  state.products = data.products || [];
  state.categories = data.categories || [];
  renderFilters();
  renderProducts();
  bindEvents();
}

init().catch(() => {
  productsEl.innerHTML = `<p class="empty">Product data could not be loaded.</p>`;
});
