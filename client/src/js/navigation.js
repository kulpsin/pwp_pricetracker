import { setState } from "./state.js";
import { renderWorkspace } from "./render.js";

/**
 * Navigates to the products list view, clearing the current product selection.
 */
export function navigateToProducts() {
    setState({
        currentView: "products",
        currentProduct: null,
        showAddProductForm: false,
        showAddPriceForm: false,
    });
    renderWorkspace();
}

/**
 * Navigates to the detail view for a specific product.
 * @param {string} hruid - The product's human-readable UID.
 */
export function navigateToProduct(hruid) {
    setState({
        currentView: "productDetail",
        currentProduct: hruid,
        showAddProductForm: false,
        showAddPriceForm: false,
    });
    renderWorkspace();
}
