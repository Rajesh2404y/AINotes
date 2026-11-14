/**
 * Authentication and Session Management Script.
 * Coordinates user registration, login, logout, and navbar session state across all pages.
 */

const authManager = {
    /**
     * Retrieves active JWT token from secure local storage.
     */
    getToken() {
        return localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    },

    /**
     * Retrieves stored safe user profile details.
     */
    getUser() {
        const data = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_DATA);
        try {
            return data ? JSON.parse(data) : null;
        } catch (e) {
            return null;
        }
    },

    /**
     * Checks if a valid authenticated session exists.
     */
    isAuthenticated() {
        return Boolean(this.getToken());
    },

    /**
     * Saves user authentication session.
     */
    setSession(token, user) {
        localStorage.setItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN, token);
        localStorage.setItem(CONFIG.STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    },

    /**
     * Updates stored user profile in local storage.
     */
    updateStoredUser(user) {
        localStorage.setItem(CONFIG.STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    },

    /**
     * Clears all session keys from storage.
     */
    clearSession() {
        localStorage.removeItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_DATA);
    },

    /**
     * Dispatches user registration with client-side validation guard.
     */
    async register(formData) {
        return apiClient.post("/auth/register", formData);
    },

    /**
     * Dispatches login request and stores authentication session.
     */
    async login(email, password) {
        const response = await apiClient.post("/auth/login", { email, password });
        if (response.status === "success" && response.access_token) {
            this.setSession(response.access_token, response.user);
        }
        return response;
    },

    /**
     * Dispatches logout request and invalidates local session.
     */
    async logout() {
        try {
            if (this.isAuthenticated()) {
                await apiClient.post("/auth/logout");
            }
        } catch (err) {
            console.warn("Logout notification failed or token already expired:", err);
        } finally {
            this.clearSession();
            window.location.href = "login.html";
        }
    },

    /**
     * Fetches fresh user data from /api/auth/me
     */
    async fetchProfile() {
        if (!this.isAuthenticated()) return null;
        try {
            const res = await apiClient.get("/auth/me");
            if (res.status === "success" && res.user) {
                this.updateStoredUser(res.user);
                return res.user;
            }
        } catch (err) {
            console.error("Failed to fetch fresh user profile:", err);
        }
        return this.getUser();
    },

    /**
     * Protects internal pages (e.g., dashboard, upload, etc.).
     * Redirects to login.html if not authenticated.
     */
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = "login.html?redirect=" + encodeURIComponent(window.location.pathname.split("/").pop());
            return false;
        }
        return true;
    },

    /**
     * If user is already authenticated on login/register pages, redirect to dashboard.html.
     */
    redirectIfAuthenticated() {
        if (this.isAuthenticated()) {
            window.location.href = "dashboard.html";
        }
    },

    /**
     * Syncs top navigation bar based on active authentication state.
     */
    updateNavbar() {
        const navContainer = document.getElementById("navMenu");
        if (!navContainer) return;

        const navList = navContainer.querySelector(".navbar-nav");
        if (!navList) return;

        const user = this.getUser();

        if (this.isAuthenticated() && user) {
            navList.innerHTML = `
                <li class="nav-item"><a class="nav-link" href="dashboard.html"><i class="bi bi-grid-fill me-1"></i> Dashboard</a></li>
                <li class="nav-item"><a class="nav-link" href="index.html#features">Features</a></li>
                <li class="nav-item"><a class="nav-link" href="index.html#how-it-works">How It Works</a></li>
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle fw-semibold d-flex align-items-center gap-2" href="#" role="button" data-bs-toggle="dropdown">
                        <span class="user-avatar-sm">${(user.full_name || user.email).charAt(0).toUpperCase()}</span>
                        <span>${user.full_name || user.email}</span>
                    </a>
                    <ul class="dropdown-menu dropdown-menu-end shadow border-0">
                        <li><a class="dropdown-item" href="dashboard.html"><i class="bi bi-speedometer2 me-2"></i> Dashboard</a></li>
                        <li><a class="dropdown-item" href="profile.html"><i class="bi bi-person me-2"></i> My Profile</a></li>
                        <li><a class="dropdown-item" href="settings.html"><i class="bi bi-gear me-2"></i> Settings</a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><button id="btn-nav-logout" class="dropdown-item text-danger"><i class="bi bi-box-arrow-right me-2"></i> Sign Out</button></li>
                    </ul>
                </li>
            `;

            const logoutBtn = document.getElementById("btn-nav-logout");
            if (logoutBtn) {
                logoutBtn.addEventListener("click", () => this.logout());
            }
        }
    }
};

// Bind form listeners when DOM loads
document.addEventListener("DOMContentLoaded", () => {
    // 1. Update Navigation state
    authManager.updateNavbar();

    // 2. Check login/register page redirection
    const isAuthPage = window.location.pathname.endsWith("login.html") || window.location.pathname.endsWith("register.html");
    if (isAuthPage) {
        authManager.redirectIfAuthenticated();
    }

    // 3. Bind Registration Form Handler
    const registerForm = document.getElementById("register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", handleRegisterSubmit);
    }

    // 4. Bind Login Form Handler
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
        loginForm.addEventListener("submit", handleLoginSubmit);
    }

    // 5. Check URL parameters for alerts
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("registered")) {
        showAlert("alert-container", "Account created successfully! Please sign in with your credentials.", "success");
    }
    if (urlParams.has("session_expired")) {
        showAlert("alert-container", "Your session has expired. Please log in again to continue.", "warning");
    }
});

/**
 * Handles registration form submission.
 */
async function handleRegisterSubmit(e) {
    e.preventDefault();
    const alertBox = document.getElementById("alert-container");
    const submitBtn = document.getElementById("btn-submit");

    const fullName = document.getElementById("fullName").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (!fullName || !email || !password || !confirmPassword) {
        showAlert("alert-container", "All fields are required. Please fill in all fields.", "danger");
        return;
    }

    if (password !== confirmPassword) {
        showAlert("alert-container", "Passwords do not match. Please re-enter identical passwords.", "danger");
        return;
    }

    if (password.length < 8) {
        showAlert("alert-container", "Password must be at least 8 characters in length.", "danger");
        return;
    }

    // Submit state
    const originalBtnHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Creating Account...';

    try {
        const result = await authManager.register({
            full_name: fullName,
            email: email,
            password: password,
            confirm_password: confirmPassword
        });

        showAlert("alert-container", "Registration successful! Redirecting to login...", "success");
        setTimeout(() => {
            window.location.href = "login.html?registered=true";
        }, 1200);
    } catch (error) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnHtml;

        let errorMsg = error.message || "Registration failed.";
        if (error.data && error.data.errors) {
            const firstErrorKey = Object.keys(error.data.errors)[0];
            errorMsg = error.data.errors[firstErrorKey];
        }
        showAlert("alert-container", errorMsg, "danger");
    }
}

/**
 * Handles login form submission.
 */
async function handleLoginSubmit(e) {
    e.preventDefault();
    const submitBtn = document.getElementById("btn-submit");

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!email || !password) {
        showAlert("alert-container", "Please enter both email and password.", "danger");
        return;
    }

    const originalBtnHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Authenticating...';

    try {
        const result = await authManager.login(email, password);
        showAlert("alert-container", "Login successful! Redirecting to your dashboard...", "success");
        setTimeout(() => {
            const urlParams = new URLSearchParams(window.location.search);
            const redirectTarget = urlParams.get("redirect") || "dashboard.html";
            window.location.href = redirectTarget;
        }, 800);
    } catch (error) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnHtml;

        const errorMsg = (error.data && error.data.message) || error.message || "Invalid email or password.";
        showAlert("alert-container", errorMsg, "danger");
    }
}

/**
 * Helper to display dynamic dismissible alerts.
 */
function showAlert(containerId, message, type = "info") {
    const container = document.getElementById(containerId);
    if (!container) return;

    const iconMap = {
        success: "bi-check-circle-fill",
        danger: "bi-exclamation-triangle-fill",
        warning: "bi-exclamation-circle-fill",
        info: "bi-info-circle-fill"
    };

    container.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show d-flex align-items-center gap-2 shadow-sm" role="alert">
            <i class="bi ${iconMap[type] || 'bi-info-circle'} fs-5 flex-shrink-0"></i>
            <div>${message}</div>
            <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}
