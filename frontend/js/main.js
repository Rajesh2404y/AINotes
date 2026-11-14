/**
 * Main Frontend Application Script.
 * Initializes common UI interactions, password toggles, and live API status pings.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize API Health Check if indicator element is present
    const healthBadge = document.getElementById("api-status-badge");
    const dbBadge = document.getElementById("db-status-badge");

    if (healthBadge) {
        verifyBackendConnectivity(healthBadge, dbBadge);
    }

    // 2. Initialize Password Visibility Toggles
    initPasswordToggles();
});

/**
 * Pings the Flask backend /api/health endpoint and updates the status indicator.
 */
async function verifyBackendConnectivity(healthBadge, dbBadge) {
    healthBadge.className = "badge bg-warning-subtle text-warning border border-warning-subtle px-3 py-2";
    healthBadge.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Connecting...';

    try {
        const data = await apiClient.checkHealth();
        if (data.status === "success") {
            healthBadge.className = "badge bg-success-subtle text-success border border-success-subtle px-3 py-2";
            healthBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> API: Online';

            if (dbBadge) {
                if (data.database === "connected") {
                    dbBadge.className = "badge bg-success-subtle text-success border border-success-subtle px-3 py-2";
                    dbBadge.innerHTML = '<i class="bi bi-database-check me-1"></i> DB: Connected';
                } else {
                    dbBadge.className = "badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-2";
                    dbBadge.innerHTML = '<i class="bi bi-database-x me-1"></i> DB: Disconnected';
                }
            }
        } else {
            throw new Error(data.message || "Unhealthy status");
        }
    } catch (err) {
        healthBadge.className = "badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-2";
        healthBadge.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-1"></i> API: Offline';

        if (dbBadge) {
            dbBadge.className = "badge bg-secondary-subtle text-secondary border border-secondary-subtle px-3 py-2";
            dbBadge.innerHTML = '<i class="bi bi-dash-circle me-1"></i> DB: Unknown';
        }
        console.warn("Backend API is currently offline. Start Flask server on http://127.0.0.1:5000");
    }
}

/**
 * Adds click handlers to all buttons with data-toggle-password attribute.
 */
function initPasswordToggles() {
    const toggleButtons = document.querySelectorAll("[data-toggle-password]");
    toggleButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-toggle-password");
            const input = document.getElementById(targetId);
            if (!input) return;

            const icon = btn.querySelector("i");
            if (input.type === "password") {
                input.type = "text";
                if (icon) {
                    icon.classList.remove("bi-eye");
                    icon.classList.add("bi-eye-slash");
                }
            } else {
                input.type = "password";
                if (icon) {
                    icon.classList.remove("bi-eye-slash");
                    icon.classList.add("bi-eye");
                }
            }
        });
    });
}

/**
 * Displays an alert message in a specified target container.
 */
function showAlert(containerId, message, type = "danger") {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show d-flex align-items-center gap-2" role="alert">
            <i class="bi bi-${type === 'danger' ? 'exclamation-octagon-fill' : 'check-circle-fill'}"></i>
            <div>${message}</div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}

