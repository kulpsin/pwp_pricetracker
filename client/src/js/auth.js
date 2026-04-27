/* eslint-disable no-console */
import { BASE } from "./config.js";
import { clearStateFromStorage } from "./state.js";
import { navigateToProducts } from "./navigation.js";
import { lookupUserByEmail } from "./api.js";
import { showToast } from "./toast.js";

/** @type {string|null} The current user's API key. */
let apiKey = localStorage.getItem("apiKey") || null;
/** @type {string|null} The current user's UUID. */
let userUuid = localStorage.getItem("userUuid") || null;
/** @type {string|null} The current user's email. */
let userEmail = localStorage.getItem("userEmail") || null;

/**
 * Returns the current API key.
 * @returns {string|null} The API key or null if not set.
 */
export function getApiKey() {
    return apiKey;
}

/**
 * Sets the API key in memory and persists it to localStorage.
 * @param {string} key - The API key to set.
 */
export function setApiKey(key) {
    apiKey = key;
    localStorage.setItem("apiKey", key);
}

/**
 * Returns the current user's UUID.
 * @returns {string|null} The user UUID or null if not set.
 */
export function getUserUuid() {
    return userUuid;
}

/**
 * Sets the user UUID in memory and persists it to localStorage.
 * @param {string} uuid - The user UUID to set.
 */
export function setUserUuid(uuid) {
    userUuid = uuid;
    localStorage.setItem("userUuid", uuid);
}

/**
 * Returns the current user's email.
 * @returns {string|null} The user email or null if not set.
 */
export function getUserEmail() {
    return userEmail;
}

/**
 * Sets the user email in memory and persists it to localStorage.
 * @param {string} email - The email to set.
 */
export function setUserEmail(email) {
    userEmail = email;
    localStorage.setItem("userEmail", email);
}

/**
 * Checks whether the user is authenticated (has both API key and UUID).
 * @returns {boolean} True if both apiKey and userUuid are non-null.
 */
export function isAuthenticated() {
    return apiKey !== null && userUuid !== null;
}

/**
 * Displays the authentication overlay on the page.
 */
export function showAuthOverlay() {
    document.getElementById("auth-overlay").style.display = "flex";
}

/**
 * Hides the authentication overlay on the page.
 */
export function hideAuthOverlay() {
    document.getElementById("auth-overlay").style.display = "none";
}

/**
 * Shows the authentication overlay to the user.
 */
export function renderAuthUI() {
    showAuthOverlay();
}

/**
 * Sets a button to a loading state by disabling it and updating its text.
 * @param {string} buttonId - The DOM id of the button element.
 * @param {boolean} loading - Whether the button should appear as loading.
 */
export function setLoading(buttonId, loading) {
    const btn = document.getElementById(buttonId);
    if (!btn) { return; }
    btn.disabled = loading;
    if (loading) {
        btn.textContent = "Loading...";
    } else if (btn.textContent === "Loading...") {
        if (buttonId === "auth-submit-key") {
            btn.textContent = "Continue";
        } else if (buttonId === "auth-create-user") {
            btn.textContent = "Create & Continue";
        }
    }
}

/**
 * Handles authentication with an existing API key and email lookup.
 * Validates input, looks up the user by email, and sets auth state on success.
 */
export async function handleExistingKey() {
    const emailInput = document.getElementById("auth-email-input");
    const email = emailInput.value.trim();
    const keyInput = document.getElementById("api-key-input");
    const key = keyInput.value.trim();
    if (!email) {
        showToast("Please enter your email address.", "error");
        return;
    }
    if (!key) {
        showToast("Please enter an API key.", "error");
        return;
    }
    setLoading("auth-submit-key", true);
    try {
        setApiKey(key);
        const result = await lookupUserByEmail(email);
        if (result && result.length > 0) {
            setUserUuid(result[0].uuid);
            hideAuthOverlay();
            navigateToProducts();
        } else {
            showToast("No user found with that email, or invalid API key.", "error");
            setApiKey(null);
            setUserUuid(null);
            clearStateFromStorage();
        }
    } catch (e) {
        const msg = e.message || "";
        if (msg.includes("HTTP 403")) {
            showToast("Invalid API key or insufficient permissions.", "error");
        } else if (msg.includes("HTTP 401")) {
            showToast("Authentication failed. Check your email and API key.", "error");
        } else {
            showToast("Error authenticating: " + msg, "error");
        }
        setApiKey(null);
        setUserUuid(null);
        clearStateFromStorage();
        console.error(e);
    } finally {
        setLoading("auth-submit-key", false);
    }
}

/**
 * Handles creation of a new user account via the API.
 * Captures the API key from the response headers and sets auth state.
 */
export async function handleCreateUser() {
    const emailInput = document.getElementById("create-email");
    const email = emailInput.value.trim();
    if (!email) {
        showToast("Please enter an email address.", "error");
        return;
    }

    setLoading("auth-create-user", true);
    try {
        const result = await createUserWithKeyCapture(email);
        if (result && result.apiKey) {
            showCredentialsModal();
        } else {
            showToast("User created but no API key received. Check console.", "error");
            console.error("No X-Api-Key header in response", result);
        }
    } catch (e) {
        showToast("Error creating user: " + e.message, "error");
        console.error(e);
    } finally {
        setLoading("auth-create-user", false);
    }
}

/**
 * Handles anonymous (unauthenticated) session entry.
 * Clears stored credentials and navigates to the products view.
 */
export function handleAnonymous() {
    apiKey = null;
    localStorage.removeItem("apiKey");
    hideAuthOverlay();
    navigateToProducts();
}

/**
 * Creates a new user via the API and captures the API key from response headers.
 * Sets the API key and user UUID in the auth store on success.
 * @param {string} email - The email address for the new user.
 * @returns {Promise<{[key: string]: any}>} The parsed response body along with location and apiKey fields.
 */
export async function createUserWithKeyCapture(email) {
    const body = { email };

    const headersObj = { "Content-Type": "application/json" };
    const bodyObj = JSON.stringify(body);

    const response = await fetch(BASE + "/api/users/", {
        method: "POST",
        body: bodyObj,
        headers: headersObj,
    });

    if (!response.ok) {
        const errText = await response.text();
        throw new Error("Failed to create user: " + response.status + " " + errText);
    }

    const apiKeyHeader = response.headers.get("X-Api-Key");
    const location = response.headers.get("Location");
    let data = {};
    try {
        const text = await response.text();
        if (text) { data = JSON.parse(text); }
    } catch { /* empty or invalid body is fine for success responses */ }

    if (apiKeyHeader) {
        setApiKey(apiKeyHeader);
    }

    if (location) {
        const uuidMatch = location.match(/\/api\/users\/([a-f0-9-]+)\//);
        if (uuidMatch && uuidMatch[1]) {
            setUserUuid(uuidMatch[1]);
        }
    }

    return { ...data, location, apiKey: apiKeyHeader };
}

/**
 * Shows the credentials modal, populating it with the current user's API key.
 */
export function showCredentialsModal() {
    const modal = document.getElementById("credentials-modal");
    if (!modal) { return; }

    const apiKeyInput = document.getElementById("cred-api-key");
    const copyFeedback = document.getElementById("cred-copy-feedback");

    if (apiKeyInput) { apiKeyInput.value = getApiKey() || "—"; }
    if (copyFeedback) { copyFeedback.style.display = "none"; }

    modal.style.display = "flex";
}

/**
 * Hides the credentials modal and navigates to the products page.
 */
export function dismissCredentialsModal() {
    hideCredentialsModal();
    hideAuthOverlay();
    navigateToProducts();
}

/**
 * Hides the credentials export modal.
 */
export function hideCredentialsModal() {
    const modal = document.getElementById("credentials-modal");
    if (!modal) { return; }
    modal.style.display = "none";
}

/**
 * Copies the value of a specific credential input to the clipboard.
 * @param {string} inputId - The DOM id of the input element to copy.
 */
export async function copyCredentialField(inputId) {
    const input = document.getElementById(inputId);
    if (!input) { return; }

    try {
        await navigator.clipboard.writeText(input.value);
        const btn = input.parentElement.querySelector(".cred-copy-btn");
        if (btn) {
            const originalText = btn.textContent;
            btn.textContent = "Copied!";
            setTimeout(() => { btn.textContent = originalText; }, 1500);
        }
    } catch {
        showToast("Failed to copy to clipboard.", "error");
    }
}

/**
 * Copies all credentials (email, API key, UUID) to the clipboard as a formatted block.
 */
export async function copyCredentials() {
    const email = getUserEmail() || "";
    const key = getApiKey() || "";
    const uuid = getUserUuid() || "";

    const text = "Email: " + email + "\nAPI Key: " + key + "\nUser UUID: " + uuid;

    try {
        await navigator.clipboard.writeText(text);
        const feedback = document.getElementById("cred-copy-feedback");
        if (feedback) {
            feedback.style.display = "inline";
            setTimeout(() => { feedback.style.display = "none"; }, 2000);
        }
    } catch {
        showToast("Failed to copy to clipboard.", "error");
    }
}

/**
 * Toggles the API key display between password (hidden) and text (visible).
 */
export function toggleApiKeyVisibility() {
    const apiKeyInput = document.getElementById("cred-api-key");
    const toggleBtn = document.getElementById("cred-toggle-visibility");
    if (!apiKeyInput) { return; }
    if (apiKeyInput.type === "password") {
        apiKeyInput.type = "text";
        if (toggleBtn) { toggleBtn.textContent = "Hide"; }
    } else {
        apiKeyInput.type = "password";
        if (toggleBtn) { toggleBtn.textContent = "Show"; }
    }
}
