/**
 * Recommendations Controller.
 * Manages fetching, generating, and updating personalized learning recommendations.
 */

let activeStatusFilter = "";
let activePriorityFilter = "";

document.addEventListener("DOMContentLoaded", async () => {
    if (!authManager.isAuthenticated()) {
        return; // Guarded by navigation.js
    }

    setupEventListeners();
    await loadRecommendations();
});

function setupEventListeners() {
    const btnGenerate = document.getElementById("btn-generate-recs");
    if (btnGenerate) {
        btnGenerate.addEventListener("click", handleGenerateRecommendations);
    }

    // Status filter buttons
    const statusGroup = document.getElementById("filter-status-group");
    if (statusGroup) {
        statusGroup.querySelectorAll("button").forEach(btn => {
            btn.addEventListener("click", () => {
                statusGroup.querySelectorAll("button").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                activeStatusFilter = btn.getAttribute("data-status") || "";
                loadRecommendations();
            });
        });
    }

    // Priority filter dropdown
    const prioritySelect = document.getElementById("filter-priority");
    if (prioritySelect) {
        prioritySelect.addEventListener("change", (e) => {
            activePriorityFilter = e.target.value || "";
            loadRecommendations();
        });
    }
}

/**
 * Loads recommendations from API with active filters.
 */
async function loadRecommendations() {
    const container = document.getElementById("recommendations-container");
    if (!container) return;

    container.innerHTML = `
        <div class="col-12 text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <div class="text-muted small mt-2">Loading recommendations...</div>
        </div>
    `;

    try {
        let endpoint = `/recommendations?page=1&per_page=20`;
        if (activeStatusFilter) endpoint += `&status=${encodeURIComponent(activeStatusFilter)}`;
        if (activePriorityFilter) endpoint += `&priority=${encodeURIComponent(activePriorityFilter)}`;

        const res = await apiClient.get(endpoint);
        if (res.status === "success" && Array.isArray(res.data)) {
            renderRecommendations(res.data);
        } else {
            renderEmptyState("No recommendations found for the selected filters.");
        }
    } catch (err) {
        console.error("Error loading recommendations:", err);
        renderEmptyState("Failed to load recommendations. Please try again.");
    }
}

/**
 * Renders recommendation cards.
 */
function renderRecommendations(items) {
    const container = document.getElementById("recommendations-container");
    if (!container) return;

    if (!items || items.length === 0) {
        renderEmptyState("No active recommendations. Click 'Generate New Recommendations' to analyze your recent performance.");
        return;
    }

    const priorityBadges = {
        high: '<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1 rounded-pill"><i class="bi bi-exclamation-circle-fill me-1"></i>High Priority</span>',
        medium: '<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle px-2 py-1 rounded-pill"><i class="bi bi-star-fill me-1"></i>Medium Priority</span>',
        low: '<span class="badge bg-info-subtle text-info border border-info-subtle px-2 py-1 rounded-pill"><i class="bi bi-info-circle-fill me-1"></i>Enrichment</span>',
    };

    container.innerHTML = items.map(rec => {
        const pBadge = priorityBadges[rec.priority] || priorityBadges.medium;
        const isCompleted = rec.status === "completed";
        const isDismissed = rec.status === "dismissed";

        let targetUrl = "quiz-config.html";
        let targetText = "Practice Quiz";
        if (rec.recommendation_type.includes("summary") || rec.recommendation_type.includes("definitions")) {
            targetUrl = "summary.html";
            targetText = "Review Notes";
        } else if (rec.recommendation_type === "continue_path") {
            targetUrl = "learning-paths.html";
            targetText = "View Path";
        }

        return `
            <div class="col-md-6 col-xl-4">
                <div class="card h-100 border shadow-xs rounded-4 p-3 d-flex flex-column justify-content-between">
                    <div>
                        <div class="d-flex align-items-center justify-content-between gap-2 mb-2">
                            ${pBadge}
                            <span class="badge bg-body-secondary text-body border px-2 py-1 rounded-pill small">${escapeHtml(rec.topic)}</span>
                        </div>
                        <h6 class="fw-bold mb-2 text-primary">${escapeHtml(rec.title)}</h6>
                        <p class="text-secondary small mb-2">${escapeHtml(rec.description || "")}</p>
                        
                        <!-- Transparent Evidence Reason Box -->
                        <div class="rec-reason-box p-2 rounded-3 mb-3">
                            <div class="small fw-semibold text-muted d-flex align-items-center gap-1 mb-1" style="font-size: 0.75rem;">
                                <i class="bi bi-lightbulb-fill text-warning"></i> Why this was recommended:
                            </div>
                            <div class="rec-reason-text">
                                ${escapeHtml(rec.reason)}
                            </div>
                        </div>

                        ${rec.suggested_action ? `
                            <div class="small text-muted mb-3">
                                <strong>Suggested:</strong> ${escapeHtml(rec.suggested_action)}
                            </div>
                        ` : ""}
                    </div>

                    <div class="border-top pt-3 d-flex align-items-center justify-content-between">
                        ${isCompleted ? `
                            <span class="badge bg-success-subtle text-success py-2 px-3 rounded-pill small"><i class="bi bi-check-circle-fill me-1"></i>Completed</span>
                        ` : isDismissed ? `
                            <span class="badge bg-secondary-subtle text-secondary py-2 px-3 rounded-pill small">Dismissed</span>
                        ` : `
                            <div class="d-flex align-items-center gap-1">
                                <a href="${targetUrl}" class="btn btn-sm btn-primary rounded-pill px-3">
                                    ${targetText} <i class="bi bi-box-arrow-up-right ms-1"></i>
                                </a>
                                <button class="btn btn-sm btn-outline-success rounded-pill px-2" onclick="handleUpdateStatus(${rec.id}, 'completed')" title="Mark as Done">
                                    <i class="bi bi-check-lg"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary rounded-pill px-2" onclick="handleUpdateStatus(${rec.id}, 'dismissed')" title="Dismiss">
                                    <i class="bi bi-x-lg"></i>
                                </button>
                            </div>
                        `}
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function renderEmptyState(message) {
    const container = document.getElementById("recommendations-container");
    if (!container) return;
    container.innerHTML = `
        <div class="col-12 text-center py-5">
            <div class="stat-icon-wrapper bg-light text-muted mx-auto mb-3" style="width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                <i class="bi bi-lightbulb fs-3"></i>
            </div>
            <h6 class="fw-bold text-muted">${escapeHtml(message)}</h6>
        </div>
    `;
}

/**
 * Handles generating recommendations on demand.
 */
async function handleGenerateRecommendations() {
    const btn = document.getElementById("btn-generate-recs");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>Analyzing...`;
    }

    try {
        const res = await apiClient.post("/recommendations/generate", {});
        if (res.status === "success") {
            await loadRecommendations();
        }
    } catch (err) {
        console.error("Error generating recommendations:", err);
        alert(err.message || "Failed to generate recommendations.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="bi bi-arrow-repeat"></i> Generate New Recommendations`;
        }
    }
}

/**
 * Updates status of a recommendation.
 */
async function handleUpdateStatus(recId, newStatus) {
    try {
        const res = await apiClient.patch(`/recommendations/${recId}`, { status: newStatus });
        if (res.status === "success") {
            await loadRecommendations();
        }
    } catch (err) {
        console.error("Failed to update status:", err);
        alert(err.message || "Could not update recommendation status.");
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

