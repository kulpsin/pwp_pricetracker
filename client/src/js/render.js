/* eslint-disable no-console */
import { isAuthenticated, getUserUuid, showCredentialsModal } from "./auth.js";
import { getState, setState } from "./state.js";
import { navigateToProducts, navigateToProduct } from "./navigation.js";
import { listUserProducts, listProducts, getProduct, createProduct, deleteProduct, createPrice, deletePrice, listPrices, enqueuePriceUpdate } from "./api.js";
import { formatPrice, formatTimestamp, truncateUrl, getTrendArrow, getTrendColor, getLatestPrice } from "./utils.js";
import { renderPriceChart } from "./graph.js";

const workspace = document.getElementById("workspace");

/**
 * Renders a loading spinner into the workspace element.
 */
export function renderLoading() {
    workspace.innerHTML = "";
    const spinner = document.createElement("div");
    spinner.className = "loading";
    spinner.textContent = "Loading...";
    workspace.appendChild(spinner);
}

/**
 * Renders an empty state message when the user has no products.
 */
export function renderNoProducts() {
    workspace.innerHTML = "";

    const empty = document.createElement("div");
    empty.className = "empty-state";

    const title = document.createElement("h2");
    title.textContent = "No products yet";
    empty.appendChild(title);

    const note = document.createElement("p");
    note.textContent = "Add your first product to start tracking prices.";
    empty.appendChild(note);

    workspace.appendChild(empty);

    if (isAuthenticated()) {
        const addBtn = document.createElement("button");
        addBtn.className = "btn btn-primary";
        addBtn.textContent = "+ Add Product";
        addBtn.addEventListener("click", () => {
            setState({ showAddProductForm: true });
            renderWorkspace();
        });
        workspace.appendChild(addBtn);
    }
}

/**
 * Renders the product list view with cards showing name, price, and trend.
 * @param {Array<object>} products - The list of product objects.
 * @param {object} pricesMap - A map of hruid to price arrays.
 * @param {boolean} loading - Whether data is still being fetched.
 */
export function renderProductList(products, pricesMap, loading) {
    workspace.innerHTML = "";

    const header = document.createElement("div");
    header.className = "list-header";

    const title = document.createElement("h2");
    title.textContent = "Products";
    header.appendChild(title);

    if (isAuthenticated()) {
        const addBtn = document.createElement("button");
        addBtn.className = "btn btn-primary";
        addBtn.textContent = "+ Add Product";
        addBtn.addEventListener("click", () => {
            const state = getState();
            setState({ showAddProductForm: !state.showAddProductForm });
            renderWorkspace();
        });
        header.appendChild(addBtn);

        const exportBtn = document.createElement("button");
        exportBtn.className = "btn";
        exportBtn.textContent = "Export Credentials";
        exportBtn.addEventListener("click", showCredentialsModal);
        header.appendChild(exportBtn);
    }

    workspace.appendChild(header);

    if (loading) {
        renderLoading();
        return;
    }

    if (!products || products.length === 0) {
        renderNoProducts();
        return;
    }

    const list = document.createElement("div");
    list.className = "product-list";

    for (let i = 0; i < products.length; i++) {
        const product = products[i];
        const prices = pricesMap[product.hruid] || [];
        const latest = getLatestPrice(prices);
        const trend = getTrendArrow(prices);
        const trendColor = getTrendColor(prices);

        const card = document.createElement("div");
        card.className = "product-card";

        const cardTop = document.createElement("div");
        cardTop.className = "product-card-top";

        const nameDiv = document.createElement("div");
        nameDiv.className = "product-name";

        const nameLink = document.createElement("a");
        nameLink.href = "#";
        nameLink.textContent = product.name;
        nameLink.addEventListener("click", (e) => {
            e.preventDefault();
            navigateToProduct(product.hruid);
        });
        nameDiv.appendChild(nameLink);

        const statusBadge = document.createElement("span");
        statusBadge.className = "status-badge " + (product.active ? "active" : "inactive");
        statusBadge.textContent = product.active ? "active" : "inactive";
        nameDiv.appendChild(statusBadge);

        cardTop.appendChild(nameDiv);

           if (latest) {
            const priceDiv = document.createElement("div");
            priceDiv.className = "product-price";

            const priceSpan = document.createElement("span");
            priceSpan.textContent = formatPrice(latest.price);
            priceDiv.appendChild(priceSpan);

            const trendSpan = document.createElement("span");
            trendSpan.className = "trend-arrow";
            trendSpan.style.color = trendColor;
            trendSpan.textContent = trend;
            priceDiv.appendChild(trendSpan);

            cardTop.appendChild(priceDiv);
        }

        card.appendChild(cardTop);

        if (product.url) {
            const urlDiv = document.createElement("a");
            urlDiv.href = product.url;
            urlDiv.target = "_blank";
            urlDiv.rel = "noopener";
            urlDiv.className = "product-url";
            urlDiv.textContent = truncateUrl(product.url, 60);
            card.appendChild(urlDiv);
        }

        if (isAuthenticated()) {
            const deleteBtn = document.createElement("button");
            deleteBtn.className = "btn btn-danger";
            deleteBtn.textContent = "Delete";
            deleteBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                if (!confirm("Delete \"" + product.name + "\"?")) { return; }
                deleteProduct(product.hruid).then(() => {
                    navigateToProducts();
                }).catch((err) => {
                    alert("Error deleting product: " + err.message);
                });
            });
            card.appendChild(deleteBtn);
        }

        list.appendChild(card);
    }

    workspace.appendChild(list);
}

/**
 * Renders the inline form for adding a new product.
 */
export function renderAddProductForm() {
    const form = document.createElement("div");
    form.className = "inline-form";

    const title = document.createElement("h3");
    title.textContent = "Add Product";
    form.appendChild(title);

    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.placeholder = "Product name";
    nameInput.id = "form-product-name";
    form.appendChild(nameInput);

    const urlInput = document.createElement("input");
    urlInput.type = "url";
    urlInput.placeholder = "Product URL (e.g. https://...)";
    urlInput.id = "form-product-url";
    form.appendChild(urlInput);

    const notesInput = document.createElement("input");
    notesInput.type = "text";
    notesInput.placeholder = "Notes (optional)";
    notesInput.id = "form-product-notes";
    form.appendChild(notesInput);

    const submitBtn = document.createElement("button");
    submitBtn.className = "btn btn-primary";
    submitBtn.textContent = "Add Product";
    submitBtn.addEventListener("click", () => {
        const name = nameInput.value.trim();
        const url = urlInput.value.trim();
        const notes = notesInput.value.trim();

        if (!name || !url) {
            alert("Name and URL are required.");
            return;
        }

        const data = { name: name, url: url };
        if (notes) { data.notes = notes; }

        createProduct(data).then(() => {
            setState({ showAddProductForm: false });
            navigateToProducts();
        }).catch((err) => {
            alert("Error creating product: " + err.message);
        });
    });
    form.appendChild(submitBtn);

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn btn-secondary";
    cancelBtn.textContent = "Cancel";
    cancelBtn.addEventListener("click", () => {
        setState({ showAddProductForm: false });
        renderWorkspace();
    });
    form.appendChild(cancelBtn);

    workspace.appendChild(form);
}

/**
 * Renders the product detail view with price history table.
 * @param {Array<object>} prices - The list of price entries.
 * @param {boolean} loading - Whether data is still being fetched.
 * @param {object|null} product - The product object, or null while loading.
 */
export function renderProductDetail(prices, loading, product) {
    workspace.innerHTML = "";

    const backBtn = document.createElement("button");
    backBtn.className = "btn btn-secondary";
    backBtn.textContent = "\u2190 Back to Products";
    backBtn.addEventListener("click", navigateToProducts);
    workspace.appendChild(backBtn);

    const detail = document.createElement("div");
    detail.className = "product-detail";

    const name = document.createElement("h2");
    name.textContent = product ? product.name : "Loading...";
    detail.appendChild(name);

    const info = document.createElement("div");
    info.className = "product-info";

    if (product && product.url) {
        const urlLink = document.createElement("a");
        urlLink.href = product.url;
        urlLink.target = "_blank";
        urlLink.rel = "noopener";
        urlLink.textContent = product.url;
        info.appendChild(urlLink);
    }

    if (product) {
        const hruidDiv = document.createElement("div");
        hruidDiv.className = "product-hruid";
        hruidDiv.textContent = "HRUID: " + product.hruid;
        info.appendChild(hruidDiv);

        const statusBadge = document.createElement("span");
        statusBadge.className = "status-badge " + (product.active ? "active" : "inactive");
        statusBadge.textContent = product.active ? "Active" : "Inactive";
        info.appendChild(statusBadge);
    }

    detail.appendChild(info);
    workspace.appendChild(detail);

    if (isAuthenticated() && product) {
        const actions = document.createElement("div");
        actions.className = "product-actions";

        const addPriceBtn = document.createElement("button");
        addPriceBtn.className = "btn btn-primary";
        addPriceBtn.textContent = "+ Add Price";
        addPriceBtn.addEventListener("click", () => {
            const state = getState();
            setState({ showAddPriceForm: !state.showAddPriceForm });
            renderWorkspace();
        });
        actions.appendChild(addPriceBtn);

        const enqueueBtn = document.createElement("button");
        enqueueBtn.className = "btn btn-secondary";
        enqueueBtn.textContent = "Enqueue Price Update";
        enqueueBtn.addEventListener("click", () => {
            if (!confirm("Enqueue a price update for \"" + product.name + "\"?")) { return; }
            enqueuePriceUpdate(product.hruid).then(() => {
                alert("Price update job enqueued successfully.");
            }).catch((err) => {
                alert("Error enqueuing price update: " + err.message);
            });
        });
        actions.appendChild(enqueueBtn);

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "btn btn-danger";
        deleteBtn.textContent = "Delete Product";
        deleteBtn.addEventListener("click", () => {
            if (!confirm("Delete \"" + product.name + "\"?")) { return; }
            deleteProduct(product.hruid).then(() => {
                navigateToProducts();
            }).catch((err) => {
                alert("Error deleting product: " + err.message);
            });
        });
        actions.appendChild(deleteBtn);

        workspace.appendChild(actions);
    }

    if (loading) {
        renderLoading();
        return;
    }

    if (prices && prices.length >= 2) {
        const chartContainer = document.createElement("div");
        chartContainer.className = "chart-container";

        const chartTitle = document.createElement("h3");
        chartTitle.textContent = "Price History";
        chartContainer.appendChild(chartTitle);

        const canvas = document.createElement("canvas");
        chartContainer.appendChild(canvas);

        workspace.appendChild(chartContainer);

        renderPriceChart(canvas, prices);
    }

    const pricesTitle = document.createElement("h3");
    pricesTitle.textContent = "Price History";
    workspace.appendChild(pricesTitle);

    if (!prices || prices.length === 0) {
        const noPrices = document.createElement("p");
        noPrices.textContent = "No prices recorded yet.";
        workspace.appendChild(noPrices);
    } else {
        const sorted = prices.slice().sort((a, b) => {
            return new Date(b.timestamp) - new Date(a.timestamp);
        });
        const table = document.createElement("table");
        table.className = "price-table";

        const thead = document.createElement("thead");
        const headRow = document.createElement("tr");
        const th1 = document.createElement("th");
        th1.textContent = "Timestamp";
        const th2 = document.createElement("th");
        th2.textContent = "Value";
        headRow.appendChild(th1);
        headRow.appendChild(th2);
        if (isAuthenticated()) {
            const th3 = document.createElement("th");
            th3.textContent = "";
            headRow.appendChild(th3);
        }
        thead.appendChild(headRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        for (let i = 0; i < sorted.length; i++) {
            const p = sorted[i];
            const row = document.createElement("tr");

            const tsCell = document.createElement("td");
            tsCell.textContent = formatTimestamp(p.timestamp);
            row.appendChild(tsCell);

            const valCell = document.createElement("td");
            valCell.textContent = formatPrice(p.price);
            row.appendChild(valCell);

            if (isAuthenticated()) {
                const delCell = document.createElement("td");
                const delBtn = document.createElement("button");
                delBtn.className = "btn btn-danger btn-small";
                delBtn.textContent = "Delete";
                delBtn.addEventListener("click", () => {
                    if (!confirm("Delete this price entry?")) { return; }
                    deletePrice(product.hruid, p.timestamp).then(() => {
                        renderWorkspace();
                    }).catch((err) => {
                        alert("Error deleting price: " + err.message);
                    });
                });
                delCell.appendChild(delBtn);
                row.appendChild(delCell);
            }

            tbody.appendChild(row);
        }
        table.appendChild(tbody);
        workspace.appendChild(table);
    }

    const state = getState();
    if (state.showAddPriceForm && product) {
        renderAddPriceForm(product.hruid);
    }
}

/**
 * Renders the inline form for adding a new price entry.
 * @param {string} hruid - The product's human-readable UID.
 */
export function renderAddPriceForm(hruid) {
    const form = document.createElement("div");
    form.className = "inline-form";

    const title = document.createElement("h3");
    title.textContent = "Add Price";
    form.appendChild(title);

    const valueInput = document.createElement("input");
    valueInput.type = "number";
    valueInput.step = "0.01";
    valueInput.placeholder = "Price value";
    valueInput.id = "form-price-value";
    form.appendChild(valueInput);

    const tsInput = document.createElement("input");
    tsInput.type = "datetime-local";
    tsInput.id = "form-price-timestamp";
    form.appendChild(tsInput);

    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    tsInput.value = now.toISOString().slice(0, 16);

    const submitBtn = document.createElement("button");
    submitBtn.className = "btn btn-primary";
    submitBtn.textContent = "Add Price";
    submitBtn.addEventListener("click", () => {
        const value = parseFloat(valueInput.value);
        const timestamp = tsInput.value;

        if (isNaN(value) || !timestamp) {
            alert("Price value and timestamp are required.");
            return;
        }

        createPrice(hruid, { value: value, timestamp: timestamp }).then(() => {
            setState({ showAddPriceForm: false });
            renderWorkspace();
        }).catch((err) => {
            alert("Error adding price: " + err.message);
        });
    });
    form.appendChild(submitBtn);

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn btn-secondary";
    cancelBtn.textContent = "Cancel";
    cancelBtn.addEventListener("click", () => {
        setState({ showAddPriceForm: false });
        renderWorkspace();
    });
    form.appendChild(cancelBtn);

    workspace.appendChild(form);
}

/**
 * Main render function that dispatches to the appropriate view renderer
 * based on the current state. Fetches data asynchronously before rendering.
 * @returns {Promise<void>}
 */
export async function renderWorkspace() {
    const { currentView, currentProduct, showAddProductForm } = getState();

    if (currentView === "productDetail") {
        if (!currentProduct) {
            navigateToProducts();
            return;
        }

        let prices = [];
        let product = null;
        let loading = true;

        try {
            const results = await Promise.all([
                getProduct(currentProduct),
                listPrices(currentProduct),
            ]);
            product = results[0];
            prices = results[1];
            loading = false;
        } catch (err) {
            loading = false;
        }

        renderProductDetail(prices, loading, product);
        return;
    }

    // Default: product list view
    let products = [];
    const pricesMap = {};
    let loading = true;

    try {
        if (isAuthenticated()) {
            const productsData = await listUserProducts(getUserUuid());
            products = productsData;
        } else {
            const productsData = await listProducts();
            products = productsData;
        }

        if (products.length > 0) {
            const pricePromises = [];
            for (let i = 0; i < products.length; i++) {
                pricePromises.push(
                    listPrices(products[i].hruid).then((prices) => {
                        return { hruid: products[i].hruid, prices: prices };
                    }).catch(() => {
                        return { hruid: products[i].hruid, prices: [] };
                    })
                );
            }
            const priceResults = await Promise.all(pricePromises);
            for (let j = 0; j < priceResults.length; j++) {
                pricesMap[priceResults[j].hruid] = priceResults[j].prices;
            }
        }
        loading = false;
    } catch (err) {
        console.error("Error loading products:", err);
        loading = false;
    }

    renderProductList(products, pricesMap, loading);

    if (showAddProductForm && isAuthenticated()) {
        renderAddProductForm();
    }
}
