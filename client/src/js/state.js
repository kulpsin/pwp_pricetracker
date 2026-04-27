import { setApiKey as _setApiKey, setUserUuid as _setUserUuid, setUserEmail as _setUserEmail } from "./auth.js";

/**
 * Application state store for the current view and UI flags.
 */

/** @type {string} Current active view name. */
export let currentView = "products";
/** @type {string|null} The hruid of the currently selected product. */
export let currentProduct = null;
/** @type {boolean} Whether the add-product form is open. */
export let showAddProductForm = false;
/** @type {boolean} Whether the add-price form is open. */
export let showAddPriceForm = false;
/** @type {string} Product list filter: "all" or "mine". */
export let productListView = "all";

/**
 * Returns a snapshot of the current application state.
 * @returns {{currentView: string, currentProduct: string|null, showAddProductForm: boolean, showAddPriceForm: boolean, productListView: string}}
 */
export function getState() {
    return {
        currentView,
        currentProduct,
        showAddProductForm,
        showAddPriceForm,
        productListView,
    };
}

/**
 * Partially updates the application state with the provided properties.
 * @param {{currentView?: string, currentProduct?: string, showAddProductForm?: boolean, showAddPriceForm?: boolean, productListView?: string}} partial - The state properties to update.
 */
export function setState(partial) {
    if (partial.currentView !== undefined) { currentView = partial.currentView; }
    if (partial.currentProduct !== undefined) { currentProduct = partial.currentProduct; }
    if (partial.showAddProductForm !== undefined) { showAddProductForm = partial.showAddProductForm; }
    if (partial.showAddPriceForm !== undefined) { showAddPriceForm = partial.showAddPriceForm; }
    if (partial.productListView !== undefined) { productListView = partial.productListView; }
}

/**
 * Loads the API key and user UUID from localStorage into the auth store.
 */
export function loadStateFromStorage() {
    const storedKey = localStorage.getItem("apiKey");
    const storedUuid = localStorage.getItem("userUuid");
    const storedEmail = localStorage.getItem("userEmail");
    const storedView = localStorage.getItem("productListView");
    if (storedKey) { _setApiKey(storedKey); }
    if (storedUuid) { _setUserUuid(storedUuid); }
    if (storedEmail) { _setUserEmail(storedEmail); }
    if (storedView && (storedView === "all" || storedView === "mine")) { productListView = storedView; }
}

/**
 * Clears the API key and user UUID from localStorage.
 */
export function clearStateFromStorage() {
    localStorage.removeItem("apiKey");
    localStorage.removeItem("userUuid");
    localStorage.removeItem("userEmail");
}
