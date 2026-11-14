/**
 * Reusable Fetch API Client.
 * Handles HTTP requests, JWT header attachment, JSON parsing, and unified error handling.
 */

const apiClient = {
    /**
     * Resolves the base URL using centralized configuration.
     */
    getBaseUrl() {
        if (typeof CONFIG !== "undefined" && CONFIG.API_BASE_URL) {
            return CONFIG.API_BASE_URL;
        }
        if (typeof API_BASE_URL !== "undefined" && API_BASE_URL) {
            return API_BASE_URL;
        }
        if (typeof window !== "undefined" && window.API_BASE_URL) {
            return window.API_BASE_URL;
        }
        return "http://127.0.0.1:5000/api";
    },

    /**
     * Property getter for baseUrl.
     */
    get baseUrl() {
        return this.getBaseUrl();
    },

    /**
     * Resolves the full URL for a given relative or absolute endpoint.
     */
    resolveUrl(endpoint) {
        if (!endpoint) return this.getBaseUrl();
        if (endpoint.startsWith("http://") || endpoint.startsWith("https://")) {
            return endpoint;
        }
        const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
        return `${this.getBaseUrl()}${cleanEndpoint}`;
    },

    /**
     * Builds request headers including JSON content-type and JWT authorization if available.
     */
    getHeaders(customHeaders = {}) {
        const headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            ...customHeaders
        };

        const token = (typeof authManager !== "undefined" && authManager && authManager.getToken)
            ? authManager.getToken()
            : (typeof getAuthToken === "function"
                ? getAuthToken()
                : localStorage.getItem("ainotes_jwt_token"));

        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        return headers;
    },

    /**
     * Core request dispatcher with network failure safety.
     */
    async request(endpoint, options = {}) {
        const url = this.resolveUrl(endpoint);
        const headers = this.getHeaders(options.headers);

        const fetchConfig = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, fetchConfig);
            let responseData;
            const contentType = response.headers.get("content-type");

            if (contentType && contentType.includes("application/json")) {
                responseData = await response.json();
            } else {
                responseData = { message: await response.text() };
            }

            if (!response.ok) {
                // Handle unauthorized / expired token
                if (response.status === 401 && !endpoint.includes("/auth/login")) {
                    console.warn("Session expired or token invalid. Clearing credentials.");
                    localStorage.removeItem("ainotes_jwt_token");
                    localStorage.removeItem("ainotes_user_info");
                    // If we are on a protected page, redirect
                    if (!window.location.pathname.endsWith("login.html") && 
                        !window.location.pathname.endsWith("register.html") &&
                        !window.location.pathname.endsWith("index.html")) {
                        window.location.href = "login.html?session_expired=true";
                    }
                }

                const error = new Error(responseData.message || responseData.error || `HTTP Error ${response.status}`);
                error.status = response.status;
                error.data = responseData;
                throw error;
            }

            return responseData;
        } catch (error) {
            if (error.name === "TypeError" && error.message.includes("fetch")) {
                console.error("Backend Server Unreachable:", url);
                const networkError = new Error("Cannot connect to backend server. Ensure the Flask API is running on port 5000.");
                networkError.status = 0;
                networkError.isNetworkError = true;
                throw networkError;
            }
            throw error;
        }
    },

    /**
     * GET Request shorthand.
     */
    async get(endpoint, customHeaders = {}) {
        return this.request(endpoint, {
            method: "GET",
            headers: customHeaders
        });
    },

    /**
     * POST Request shorthand.
     */
    async post(endpoint, data = {}, customHeaders = {}) {
        return this.request(endpoint, {
            method: "POST",
            headers: customHeaders,
            body: JSON.stringify(data)
        });
    },

    /**
     * PUT Request shorthand.
     */
    async put(endpoint, data = {}, customHeaders = {}) {
        return this.request(endpoint, {
            method: "PUT",
            headers: customHeaders,
            body: JSON.stringify(data)
        });
    },

    /**
     * PATCH Request shorthand.
     */
    async patch(endpoint, data = {}, customHeaders = {}) {
        return this.request(endpoint, {
            method: "PATCH",
            headers: customHeaders,
            body: JSON.stringify(data)
        });
    },

    /**
     * DELETE Request shorthand.
     */
    async delete(endpoint, customHeaders = {}) {
        return this.request(endpoint, {
            method: "DELETE",
            headers: customHeaders
        });
    }
};

// Global attachment
if (typeof window !== "undefined") {
    window.apiClient = apiClient;
}

// Module export support
if (typeof module !== "undefined" && module.exports) {
    module.exports = { apiClient };
}
