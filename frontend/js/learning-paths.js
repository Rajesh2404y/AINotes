/**
 * Learning Paths Controller.
 * Manages creating, tracking, and verifying sequential adaptive learning pathways.
 */

document.addEventListener("DOMContentLoaded", async () => {
    if (!authManager.isAuthenticated()) {
        return; // Guarded by navigation.js
    }

    setupEventListeners();
    await loadLearningPaths();
});

function setupEventListeners() {
    const form = document.getElementById("create-path-form");
    if (form) {
        form.addEventListener("submit", handleCreatePath);
    }
}

/**
 * Loads all user learning paths from API.
 */
async function loadLearningPaths() {
    const container = document.getElementById("learning-paths-container");
    if (!container) return;

    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <div class="text-muted small mt-2">Loading learning pathways...</div>
        </div>
    `;

    try {
        const res = await apiClient.get("/learning-paths?page=1&per_page=20");
        if (res.status === "success" && Array.isArray(res.data)) {
            renderLearningPaths(res.data);
        } else {
            renderEmptyState();
        }
    } catch (err) {
        console.error("Error loading learning paths:", err);
        renderEmptyState();
    }
}

/**
 * Renders list of learning paths with sequential activity milestones.
 */
function renderLearningPaths(paths) {
    const container = document.getElementById("learning-paths-container");
    if (!container) return;

    if (!paths || paths.length === 0) {
        renderEmptyState();
        return;
    }

    const activityIcons = {
        summary_review: "bi-card-text text-primary",
        takeaways_study: "bi-list-check text-success",
        definitions_review: "bi-book-half text-info",
        quiz_practice: "bi-patch-question-fill text-warning",
    };

    container.innerHTML = paths.map(path => {
        const isCompleted = path.status === "completed" || path.progress_percentage >= 100;
        const isPaused = path.status === "paused";

        const statusBadge = isCompleted
            ? '<span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-1 rounded-pill">Completed</span>'
            : isPaused
            ? '<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-3 py-1 rounded-pill">Paused</span>'
            : '<span class="badge bg-primary-subtle text-primary border border-primary-subtle px-3 py-1 rounded-pill">In Progress</span>';

        const activitiesHtml = (path.activities || []).map(act => {
            const actDone = act.status === "completed";
            const iconClass = activityIcons[act.activity_type] || "bi-check2-circle text-muted";

            let actionUrl = "summary.html";
            let actionText = "Open Resource";
            if (act.activity_type === "quiz_practice") {
                actionUrl = "quiz-config.html";
                actionText = "Take Quiz";
            }

            return `
                <div class="p-3 bg-body rounded-3 border d-flex flex-wrap align-items-center justify-content-between gap-3 mb-2">
                    <div class="d-flex align-items-center gap-3">
                        <div class="fs-4 ${iconClass}">
                            <i class="bi ${iconClass}"></i>
                        </div>
                        <div>
                            <div class="d-flex align-items-center gap-2">
                                <span class="badge bg-light text-muted border rounded-circle" style="width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem;">${act.sequence_number}</span>
                                <h6 class="fw-semibold mb-0 ${actDone ? 'text-decoration-line-through text-muted' : ''}">${escapeHtml(act.activity_title)}</h6>
                            </div>
                            <span class="text-muted small" style="font-size: 0.75rem;">Stage: ${act.activity_type.replace('_', ' ').toUpperCase()}</span>
                        </div>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        ${actDone ? `
                            <span class="badge bg-success text-white px-3 py-2 rounded-pill small">
                                <i class="bi bi-check-circle-fill me-1"></i> Completed
                            </span>
                        ` : `
                            <a href="${actionUrl}" class="btn btn-sm btn-outline-primary rounded-pill px-3">
                                ${actionText} <i class="bi bi-arrow-right ms-1"></i>
                            </a>
                            <button class="btn btn-sm btn-success rounded-pill px-3" onclick="handleVerifyActivity(${path.id}, ${act.id})" title="Verify & Complete Milestone">
                                <i class="bi bi-check2"></i> Complete
                            </button>
                        `}
                    </div>
                </div>
            `;
        }).join("");

        return `
            <div class="card border shadow-sm rounded-4 p-4">
                <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 border-bottom pb-3 mb-3">
                    <div>
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="badge bg-body-secondary text-primary border rounded-pill px-3 py-1 small fw-bold">${escapeHtml(path.target_topic)}</span>
                            ${statusBadge}
                        </div>
                        <h5 class="fw-bold mb-0">${escapeHtml(path.title)}</h5>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        ${!isCompleted ? `
                            <button class="btn btn-sm ${isPaused ? 'btn-outline-success' : 'btn-outline-secondary'} rounded-pill px-3" onclick="handleTogglePause(${path.id}, '${isPaused ? 'in_progress' : 'paused'}')">
                                <i class="bi ${isPaused ? 'bi-play-fill' : 'bi-pause-fill'}"></i> ${isPaused ? 'Resume' : 'Pause'}
                            </button>
                        ` : ''}
                        <button class="btn btn-sm btn-outline-danger rounded-pill px-3" onclick="handleDeletePath(${path.id})" title="Delete Learning Path">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>

                <div class="mb-3">
                    <div class="d-flex align-items-center justify-content-between mb-1 small text-muted">
                        <span>Milestone Progress</span>
                        <span class="fw-bold text-primary">${Math.round(path.progress_percentage)}%</span>
                    </div>
                    <div class="progress rounded-pill" style="height: 10px;">
                        <div class="progress-bar ${isCompleted ? 'bg-success' : 'bg-primary'}" role="progressbar" style="width: ${path.progress_percentage}%" aria-valuenow="${path.progress_percentage}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                </div>

                <div class="mt-2">
                    <h6 class="small fw-bold text-uppercase text-muted mb-2">Curriculum Sequence:</h6>
                    ${activitiesHtml}
                </div>
            </div>
        `;
    }).join("");
}

function renderEmptyState() {
    const container = document.getElementById("learning-paths-container");
    if (!container) return;
    container.innerHTML = `
        <div class="card border-0 shadow-sm rounded-4 p-5 text-center">
            <div class="stat-icon-wrapper bg-light text-primary mx-auto mb-3" style="width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                <i class="bi bi-signpost-split-fill fs-2"></i>
            </div>
            <h5 class="fw-bold mb-1">No Active Learning Paths</h5>
            <p class="text-muted small mb-3">Create an adaptive curriculum path to target weak topics and master concepts step-by-step.</p>
            <button class="btn btn-primary rounded-pill px-4 mx-auto" data-bs-toggle="modal" data-bs-target="#createPathModal">
                <i class="bi bi-plus-lg me-1"></i> Create Your First Path
            </button>
        </div>
    `;
}

/**
 * Handles creation of new learning path.
 */
async function handleCreatePath(e) {
    e.preventDefault();
    const input = document.getElementById("path-topic-input");
    const submitBtn = document.getElementById("btn-submit-path");
    if (!input || !input.value.trim()) return;

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>Generating...`;

    try {
        const res = await apiClient.post("/learning-paths/generate", {
            topic: input.value.trim()
        });

        if (res.status === "success") {
            // Dismiss modal
            const modalEl = document.getElementById("createPathModal");
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            input.value = "";
            await loadLearningPaths();
        }
    } catch (err) {
        console.error("Failed to generate path:", err);
        alert(err.message || "Failed to create learning path.");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Generate Path";
    }
}

/**
 * Verifies and completes an activity milestone.
 */
async function handleVerifyActivity(pathId, actId) {
    try {
        const res = await apiClient.post(`/learning-paths/${pathId}/activities/${actId}/complete`, {});
        if (res.status === "success") {
            await loadLearningPaths();
        }
    } catch (err) {
        console.error("Verification failed:", err);
        alert(err.message || "Could not verify activity completion.");
    }
}

/**
 * Pauses or resumes a learning path.
 */
async function handleTogglePause(pathId, newStatus) {
    try {
        const res = await apiClient.patch(`/learning-paths/${pathId}`, { status: newStatus });
        if (res.status === "success") {
            await loadLearningPaths();
        }
    } catch (err) {
        console.error("Toggle pause failed:", err);
        alert(err.message || "Failed to update learning path status.");
    }
}

/**
 * Deletes a learning path.
 */
async function handleDeletePath(pathId) {
    if (!confirm("Are you sure you want to delete this learning path?")) return;

    try {
        const res = await apiClient.delete(`/learning-paths/${pathId}`);
        if (res.status === "success") {
            await loadLearningPaths();
        }
    } catch (err) {
        console.error("Delete failed:", err);
        alert(err.message || "Failed to delete learning path.");
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

