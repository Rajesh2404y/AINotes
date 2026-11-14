/**
 * Learning Materials and Activity History Controller.
 * Manages server-side pagination (10, 20, 50 records per page),
 * live debounced search, category filtering (All/Docs/Summaries/Quizzes/Translations),
 * smooth non-flickering detail modal inspection, and authenticated record deletion.
 */

// State Management
let currentActivities = [];
let currentPage = 1;
let perPage = 10;
let currentFilter = "all";
let searchQuery = "";
let totalItems = 0;
let totalPages = 0;
let hasPrevious = false;
let hasNext = false;

let isFetchingHistory = false;
let isModalLoading = false;
let itemPendingDeletion = null;
let lastActiveViewButton = null;
let searchDebounceTimer = null;

document.addEventListener("DOMContentLoaded", async () => {
    if (typeof authManager !== "undefined" && !authManager.isAuthenticated()) {
        return; // Guarded by navigation.js
    }

    setupDelegatedEvents();
    bindFilterAndSearchEvents();
    setupModalLifecycle();
    await loadHistory(1);
});

/**
 * Configures detail modal lifecycle listeners for accessibility and smooth focus restoration.
 */
function setupModalLifecycle() {
    const modalEl = document.getElementById("historyDetailModal");
    if (modalEl) {
        modalEl.addEventListener("hidden.bs.modal", () => {
            isModalLoading = false;
            // Restore keyboard focus smoothly without triggering page scroll jumps
            if (lastActiveViewButton && typeof lastActiveViewButton.focus === "function") {
                try {
                    lastActiveViewButton.focus({ preventScroll: true });
                } catch (e) {
                    lastActiveViewButton.focus();
                }
            }
            lastActiveViewButton = null;
        });
    }
}

/**
 * Attaches delegated event listeners on the document to avoid fragile inline handlers.
 */
function setupDelegatedEvents() {
    document.addEventListener("click", async (event) => {
        // 1. Delegated View Action
        const viewButton = event.target.closest("[data-action='view']");
        if (viewButton) {
            event.preventDefault();
            if (isModalLoading) return; // Prevent duplicate rapid requests

            const rawId = viewButton.dataset.id;
            const type = viewButton.dataset.type;

            if (!rawId || !type) {
                console.error("Missing record ID or type on view trigger.");
                return;
            }

            const cleanId = parseInt(String(rawId).replace(/^[a-z]+-/, ""), 10);
            lastActiveViewButton = viewButton;
            await handleViewHistory(type, cleanId);
            return;
        }

        // 2. Delegated Delete Action
        const deleteButton = event.target.closest("[data-action='delete']");
        if (deleteButton) {
            event.preventDefault();
            const rawId = deleteButton.dataset.id;
            const type = deleteButton.dataset.type;

            if (!rawId || !type) {
                console.error("Missing record ID or type on delete trigger.");
                return;
            }

            const cleanId = parseInt(String(rawId).replace(/^[a-z]+-/, ""), 10);
            openDeleteConfirmation(type, cleanId);
            return;
        }

        // 3. Delegated Pagination Page Navigation
        const pageBtn = event.target.closest("[data-page]");
        if (pageBtn) {
            event.preventDefault();
            const targetPage = parseInt(pageBtn.dataset.page, 10);
            if (!isNaN(targetPage) && targetPage >= 1 && targetPage <= totalPages && targetPage !== currentPage) {
                await loadHistory(targetPage);
            }
            return;
        }
    });

    // Modal Confirm Delete Button
    const confirmDeleteBtn = document.getElementById("btn-confirm-delete");
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", async () => {
            if (itemPendingDeletion) {
                await executeDelete(itemPendingDeletion.type, itemPendingDeletion.id);
            }
        });
    }

    // Per-Page Selector Change
    const perPageSelect = document.getElementById("history-per-page");
    if (perPageSelect) {
        perPageSelect.addEventListener("change", async (e) => {
            const newPerPage = parseInt(e.target.value, 10);
            if ([10, 20, 50].includes(newPerPage)) {
                perPage = newPerPage;
                currentPage = 1;
                await loadHistory(1);
            }
        });
    }
}

/**
 * Binds category filter buttons and debounced search input.
 */
function bindFilterAndSearchEvents() {
    // 1. Category Filter Tabs
    const filterTabs = document.querySelectorAll(".history-filter-btn");
    filterTabs.forEach(btn => {
        btn.addEventListener("click", async () => {
            if (btn.classList.contains("active")) return;
            filterTabs.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentFilter = btn.dataset.filter || "all";
            currentPage = 1;
            await loadHistory(1);
        });
    });

    // 2. Debounced Search Input (300ms)
    const searchInput = document.getElementById("history-search-input");
    if (searchInput) {
        searchInput.addEventListener("input", () => {
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(async () => {
                searchQuery = searchInput.value.trim();
                currentPage = 1;
                await loadHistory(1);
            }, 300);
        });
    }
}

/**
 * Loads paginated activity records from server-side database API.
 */
async function loadHistory(page = 1) {
    if (isFetchingHistory) return;
    isFetchingHistory = true;

    const listContainer = document.getElementById("history-items-container");
    const countBadge = document.getElementById("history-count-badge");
    const paginationContainer = document.getElementById("history-pagination-container");

    // Display smooth loading skeleton placeholder
    if (listContainer) {
        listContainer.innerHTML = `
            <div class="text-center py-5 text-muted">
                <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                <span>Retrieving page ${page} records from server...</span>
            </div>
        `;
    }

    try {
        const queryParams = new URLSearchParams({
            page: page,
            per_page: perPage,
            type: currentFilter,
            search: searchQuery
        });

        const res = await apiClient.get(`/history?${queryParams.toString()}`);

        if (res && res.success && Array.isArray(res.data)) {
            currentActivities = res.data;
            const pagination = res.pagination || {};
            currentPage = pagination.current_page || page;
            perPage = pagination.per_page || perPage;
            totalItems = pagination.total_items || 0;
            totalPages = pagination.total_pages || 0;
            hasPrevious = !!pagination.has_previous;
            hasNext = !!pagination.has_next;
        } else {
            currentActivities = [];
            totalItems = 0;
            totalPages = 0;
            hasPrevious = false;
            hasNext = false;
        }
    } catch (err) {
        console.warn("Failed to load activities from API, displaying empty history state:", err);
        currentActivities = [];
        totalItems = 0;
        totalPages = 0;
        hasPrevious = false;
        hasNext = false;
    } finally {
        isFetchingHistory = false;
    }

    // Update Header Count Badge
    if (countBadge) {
        countBadge.textContent = `${totalItems} items`;
    }

    // Render Cards and Pagination
    renderHistoryCards();
    renderPaginationControls();
}

/**
 * Renders the history items list onto the page.
 */
function renderHistoryCards() {
    const listContainer = document.getElementById("history-items-container");
    if (!listContainer) return;

    if (currentActivities.length === 0) {
        const isFiltering = currentFilter !== "all" || searchQuery.length > 0;
        listContainer.innerHTML = `
            <div class="empty-state text-center py-5 border rounded-4 p-4 bg-body">
                <div class="empty-state-icon mb-3 text-muted">
                    <i class="bi ${isFiltering ? 'bi-search' : 'bi-folder2-open'} fs-1 opacity-50"></i>
                </div>
                <h6 class="fw-bold mb-1">${isFiltering ? 'No Matching Records' : 'No Materials Found'}</h6>
                <p class="text-muted small mb-3">
                    ${isFiltering 
                        ? 'No activity records match your current filter or search criteria.' 
                        : 'You haven\'t uploaded or generated any study materials yet.'}
                </p>
                ${isFiltering ? `
                    <button type="button" class="btn btn-outline-primary btn-sm rounded-pill px-3" onclick="resetFilters()">
                        <i class="bi bi-arrow-counterclockwise me-1"></i> Reset Filters
                    </button>
                ` : `
                    <a href="upload.html" class="btn btn-primary btn-sm rounded-pill px-3">
                        <i class="bi bi-cloud-arrow-up me-1"></i> Upload New Document
                    </a>
                `}
            </div>
        `;
        return;
    }

    const typeMeta = {
        document: { label: "Document", badge: "bg-primary-subtle text-primary border-primary-subtle", icon: "bi-file-earmark-text" },
        summary: { label: "Summary", badge: "bg-success-subtle text-success border-success-subtle", icon: "bi-card-text" },
        quiz: { label: "Quiz", badge: "bg-warning-subtle text-warning border-warning-subtle", icon: "bi-patch-check" },
        translation: { label: "Translation", badge: "bg-info-subtle text-info border-info-subtle", icon: "bi-translate" }
    };

    listContainer.innerHTML = currentActivities.map(item => {
        const meta = typeMeta[item.type] || { label: "Item", badge: "bg-secondary-subtle text-secondary", icon: "bi-circle" };
        const formattedDate = formatDateTime(item.timestamp, null, "Recently");
        const numericId = item.raw_id || parseInt(String(item.id).replace(/^[a-z]+-/, ""), 10) || 0;

        return `
            <div class="card mb-3 p-3 shadow-xs history-card border rounded-4" id="card-${item.type}-${numericId}">
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                    <div class="d-flex align-items-center gap-3 overflow-hidden">
                        <div class="p-3 ${meta.badge} rounded-3 flex-shrink-0">
                            <i class="bi ${meta.icon} fs-4"></i>
                        </div>
                        <div class="overflow-hidden">
                            <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                                <span class="badge ${meta.badge} border">${meta.label}</span>
                                <span class="text-muted small">${formattedDate}</span>
                            </div>
                            <h6 class="fw-bold mb-0 text-truncate" style="max-width: 420px;">${escapeHtml(item.title || 'Untitled Material')}</h6>
                            <span class="text-muted small text-truncate d-block" style="max-width: 420px;">${escapeHtml(item.details || '')}</span>
                        </div>
                    </div>
                    <div class="d-flex align-items-center gap-2 flex-shrink-0">
                        <button type="button" class="btn btn-outline-secondary btn-sm rounded-pill px-3" data-action="view" data-type="${item.type}" data-id="${numericId}">
                            <i class="bi bi-eye me-1"></i> View
                        </button>
                        <button type="button" class="btn btn-outline-danger btn-sm rounded-pill px-2" data-action="delete" data-type="${item.type}" data-id="${numericId}" title="Delete Record">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

/**
 * Renders server-side pagination controls (Previous, numbers, Next, range).
 */
function renderPaginationControls() {
    const paginationContainer = document.getElementById("history-pagination-container");
    const rangeSpan = document.getElementById("history-showing-range");
    const navList = document.getElementById("history-pagination-nav");

    if (!paginationContainer || !rangeSpan || !navList) return;

    if (totalItems === 0) {
        paginationContainer.style.display = "none";
        return;
    }

    paginationContainer.style.display = "flex";

    // 1. Calculate showing range
    const startIdx = (currentPage - 1) * perPage + 1;
    const endIdx = Math.min(currentPage * perPage, totalItems);
    rangeSpan.textContent = `Showing ${startIdx}\u2013${endIdx} of ${totalItems} records`;

    // 2. Build pagination navigation buttons
    let navHtml = "";

    // Previous Button
    navHtml += `
        <li class="page-item ${!hasPrevious ? 'disabled' : ''}">
            <button class="page-link" data-page="${currentPage - 1}" aria-label="Previous" ${!hasPrevious ? 'tabindex="-1"' : ''}>
                <i class="bi bi-chevron-left"></i> Previous
            </button>
        </li>
    `;

    // Numeric Page Buttons with smart windowing
    const maxVisibleButtons = 5;
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + maxVisibleButtons - 1);

    if (endPage - startPage + 1 < maxVisibleButtons) {
        startPage = Math.max(1, endPage - maxVisibleButtons + 1);
    }

    if (startPage > 1) {
        navHtml += `
            <li class="page-item"><button class="page-link" data-page="1">1</button></li>
        `;
        if (startPage > 2) {
            navHtml += `<li class="page-item disabled"><span class="page-link border-0">\u2026</span></li>`;
        }
    }

    for (let p = startPage; p <= endPage; p++) {
        navHtml += `
            <li class="page-item ${p === currentPage ? 'active' : ''}">
                <button class="page-link" data-page="${p}">${p}</button>
            </li>
        `;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            navHtml += `<li class="page-item disabled"><span class="page-link border-0">\u2026</span></li>`;
        }
        navHtml += `
            <li class="page-item"><button class="page-link" data-page="${totalPages}">${totalPages}</button></li>
        `;
    }

    // Next Button
    navHtml += `
        <li class="page-item ${!hasNext ? 'disabled' : ''}">
            <button class="page-link" data-page="${currentPage + 1}" aria-label="Next" ${!hasNext ? 'tabindex="-1"' : ''}>
                Next <i class="bi bi-chevron-right"></i>
            </button>
        </li>
    `;

    navList.innerHTML = navHtml;
}

/**
 * Resets category filters and search to initial state.
 */
window.resetFilters = async function() {
    currentFilter = "all";
    searchQuery = "";
    currentPage = 1;

    const searchInput = document.getElementById("history-search-input");
    if (searchInput) searchInput.value = "";

    const filterTabs = document.querySelectorAll(".history-filter-btn");
    filterTabs.forEach(b => {
        if (b.dataset.filter === "all") b.classList.add("active");
        else b.classList.remove("active");
    });

    await loadHistory(1);
};

/**
 * Handles viewing detailed records in a rich modal with stable geometry (no flickering).
 */
async function handleViewHistory(type, id) {
    const modalEl = document.getElementById("historyDetailModal");
    const modalTitleText = document.getElementById("historyModalTitleText");
    const modalIcon = document.getElementById("historyModalIcon");
    const modalBody = document.getElementById("historyModalBody");
    const actionContainer = document.getElementById("historyModalActionContainer");

    if (!modalEl || !modalBody) return;

    isModalLoading = true;

    // Set initial loading state with stable 380px min-height to eliminate dialog jump / blinking
    modalBody.innerHTML = `
        <div class="d-flex flex-column align-items-center justify-content-center" style="min-height: 340px;">
            <div class="spinner-border text-primary mb-3" role="status" style="width: 2.5rem; height: 2.5rem;"></div>
            <h6 class="fw-semibold text-body mb-1">Loading Record Details</h6>
            <span class="text-muted small">Retrieving ${type} #${id} from archive...</span>
        </div>
    `;

    if (actionContainer) actionContainer.innerHTML = "";
    if (modalTitleText) modalTitleText.textContent = `${type.toUpperCase()} #${id}`;
    if (modalIcon) modalIcon.innerHTML = `<i class="bi bi-hourglass-split text-primary fs-4"></i>`;

    const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    bsModal.show();

    try {
        if (type === "document") {
            if (modalTitleText) modalTitleText.textContent = `Document Details #${id}`;
            if (modalIcon) modalIcon.innerHTML = `<i class="bi bi-file-earmark-text text-primary fs-4"></i>`;

            const res = await apiClient.get(`/documents/${id}`);
            const doc = res.document || res.data;

            modalBody.innerHTML = `
                <div class="mb-3">
                    <div class="row g-2 mb-3">
                        <div class="col-sm-6">
                            <span class="text-muted small d-block">Filename</span>
                            <span class="fw-bold text-body">${escapeHtml(doc.original_filename || "Document")}</span>
                        </div>
                        <div class="col-sm-6">
                            <span class="text-muted small d-block">File Type</span>
                            <span class="badge bg-primary-subtle text-primary border">${(doc.file_type || "pdf").toUpperCase()}</span>
                        </div>
                        <div class="col-sm-6">
                            <span class="text-muted small d-block">Uploaded At</span>
                            <span class="text-body">${formatDateTime(doc.created_at, null, "N/A")}</span>
                        </div>
                        <div class="col-sm-6">
                            <span class="text-muted small d-block">Extraction Status</span>
                            <span class="badge ${doc.processing_status === 'completed' ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning'} border">
                                ${(doc.processing_status || "completed").toUpperCase()}
                            </span>
                        </div>
                    </div>

                    <h6 class="fw-bold mb-2">Extracted Content Preview</h6>
                    <div class="p-3 rounded bg-body-tertiary border overflow-auto" style="max-height: 280px; font-family: monospace; font-size: 0.88rem; white-space: pre-wrap;">${escapeHtml(doc.extracted_text || doc.cleaned_text || "No extracted content available.")}</div>
                </div>
            `;
            if (actionContainer) {
                actionContainer.innerHTML = `<a href="summary.html" class="btn btn-primary rounded-pill px-3">Generate Summary</a>`;
            }

        } else if (type === "summary") {
            if (modalTitleText) modalTitleText.textContent = `AI Summary Details #${id}`;
            if (modalIcon) modalIcon.innerHTML = `<i class="bi bi-card-text text-success fs-4"></i>`;

            const res = await apiClient.get(`/summaries/${id}`);
            const sum = res.data || res.summary;

            modalBody.innerHTML = `
                <div class="mb-3">
                    <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3 border-bottom pb-2">
                        <div>
                            <span class="badge bg-success-subtle text-success border me-2">${(sum.summary_type || "text").toUpperCase()} SUMMARY</span>
                            <span class="text-muted small">Doc #${sum.document_id}</span>
                        </div>
                        <span class="text-muted small">${formatDateTime(sum.created_at, null, "")}</span>
                    </div>

                    <h6 class="fw-bold mb-2">Generated Summary</h6>
                    <div class="p-3 rounded bg-body-tertiary border mb-3 text-body" style="line-height: 1.6;">
                        ${escapeHtml(sum.summary_text || "")}
                    </div>

                    ${Array.isArray(sum.key_takeaways) && sum.key_takeaways.length > 0 ? `
                        <h6 class="fw-bold mb-2 text-primary"><i class="bi bi-check2-circle me-1"></i> Key Takeaways</h6>
                        <ul class="list-unstyled mb-3">
                            ${sum.key_takeaways.map(t => `<li class="mb-1 d-flex align-items-start gap-2"><i class="bi bi-dot text-primary fs-5 mt-n1"></i><span>${escapeHtml(t)}</span></li>`).join("")}
                        </ul>
                    ` : ""}

                    ${Array.isArray(sum.definitions) && sum.definitions.length > 0 ? `
                        <h6 class="fw-bold mb-2 text-primary"><i class="bi bi-book me-1"></i> Definitions</h6>
                        <div class="list-group list-group-flush border rounded-3 mb-3">
                            ${sum.definitions.map(d => `
                                <div class="list-group-item bg-body-tertiary py-2">
                                    <strong class="text-primary">${escapeHtml(typeof d === 'object' ? d.term : '')}</strong>
                                    <p class="mb-0 small text-secondary">${escapeHtml(typeof d === 'object' ? d.definition : d)}</p>
                                </div>
                            `).join("")}
                        </div>
                    ` : ""}

                    ${Array.isArray(sum.keywords) && sum.keywords.length > 0 ? `
                        <h6 class="fw-bold mb-2 text-primary"><i class="bi bi-tags me-1"></i> Keywords</h6>
                        <div class="d-flex flex-wrap gap-2">
                            ${sum.keywords.map(kw => `<span class="badge bg-body-secondary text-body border">#${escapeHtml(kw)}</span>`).join("")}
                        </div>
                    ` : ""}
                </div>
            `;
            if (actionContainer) {
                actionContainer.innerHTML = `<a href="translate.html" class="btn btn-primary rounded-pill px-3">Translate Summary</a>`;
            }

        } else if (type === "quiz") {
            if (modalTitleText) modalTitleText.textContent = `Quiz Assessment Results #${id}`;
            if (modalIcon) modalIcon.innerHTML = `<i class="bi bi-patch-check text-warning fs-4"></i>`;

            const res = await apiClient.get(`/quizzes/attempts/${id}`);
            const att = res.data;

            const percentage = Math.round(att.percentage || 0);
            const responses = att.responses || [];

            modalBody.innerHTML = `
                <div class="mb-3">
                    <div class="p-3 rounded-4 bg-body-tertiary border mb-3 text-center">
                        <div class="display-5 fw-bold text-primary mb-1">${percentage}%</div>
                        <p class="text-muted small mb-0">Score: <strong class="text-body">${att.score}</strong> / ${att.total_questions} questions correct (${percentage >= 80 ? 'Mastery' : percentage >= 50 ? 'Proficient' : 'Needs Review'})</p>
                        <span class="text-muted small d-block mt-1">Completed: ${formatDateTime(att.completed_at, null, "Recently")}</span>
                    </div>

                    <h6 class="fw-bold mb-3">Question Review & Explanations</h6>
                    <div class="d-flex flex-column gap-3">
                        ${responses.map((r, idx) => `
                            <div class="card p-3 border-start border-4 ${r.is_correct ? 'border-success' : 'border-danger'} bg-body shadow-xs">
                                <div class="d-flex align-items-start gap-2 mb-2">
                                    <i class="bi ${r.is_correct ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'} fs-5 mt-n1"></i>
                                    <div>
                                        <span class="fw-bold text-body">Question ${idx + 1}:</span> ${escapeHtml(r.question_text || '')}
                                    </div>
                                </div>
                                <div class="small ms-4">
                                    <div><span class="text-muted">Your Answer:</span> <strong class="${r.is_correct ? 'text-success' : 'text-danger'}">${escapeHtml(r.selected_answer || 'None')}</strong></div>
                                    ${!r.is_correct ? `<div><span class="text-muted">Correct Answer:</span> <strong class="text-success">${escapeHtml(r.correct_answer || '')}</strong></div>` : ''}
                                    ${r.explanation ? `<div class="mt-2 p-2 rounded bg-body-secondary text-body small"><strong>Explanation:</strong> ${escapeHtml(r.explanation)}</div>` : ''}
                                </div>
                            </div>
                        `).join("")}
                    </div>
                </div>
            `;
            if (actionContainer) {
                actionContainer.innerHTML = `<a href="quiz-config.html" class="btn btn-primary rounded-pill px-3">Retake Quiz</a>`;
            }

        } else if (type === "translation") {
            if (modalTitleText) modalTitleText.textContent = `Translation Record #${id}`;
            if (modalIcon) modalIcon.innerHTML = `<i class="bi bi-translate text-info fs-4"></i>`;

            const res = await apiClient.get(`/translations/${id}`);
            const tr = res.data;

            modalBody.innerHTML = `
                <div class="mb-3">
                    <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3 border-bottom pb-2">
                        <div>
                            <span class="badge bg-secondary-subtle text-secondary border me-1">${(tr.source_language || 'EN').toUpperCase()}</span>
                            <i class="bi bi-arrow-right mx-1 text-muted"></i>
                            <span class="badge bg-info-subtle text-info border">${(tr.target_language || '').toUpperCase()}</span>
                        </div>
                        <span class="text-muted small">${formatDateTime(tr.created_at, null, "")}</span>
                    </div>

                    <div class="row g-3">
                        <div class="col-md-6">
                            <h6 class="fw-bold mb-2">Original Content</h6>
                            <div class="p-3 rounded bg-body-tertiary border overflow-auto text-body" style="max-height: 250px; font-size: 0.9rem;">
                                ${escapeHtml(tr.original_text || '')}
                            </div>
                        </div>
                        <div class="col-md-6">
                            <h6 class="fw-bold mb-2 text-info">Translated Content (${(tr.target_language || '').toUpperCase()})</h6>
                            <div class="p-3 rounded bg-info-subtle border border-info-subtle overflow-auto text-body" style="max-height: 250px; font-size: 0.9rem;">
                                ${escapeHtml(tr.translated_text || '')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            if (actionContainer) {
                actionContainer.innerHTML = `<a href="translate.html" class="btn btn-primary rounded-pill px-3">Open Translator</a>`;
            }
        }
    } catch (err) {
        console.error("Failed to load item details:", err);
        modalBody.innerHTML = `
            <div class="d-flex flex-column align-items-center justify-content-center p-4 text-center" style="min-height: 320px;">
                <i class="bi bi-exclamation-triangle-fill text-danger fs-1 mb-2"></i>
                <h6 class="fw-bold text-danger mb-1">Failed to Load Details</h6>
                <p class="text-muted small mb-3">${escapeHtml(err.message || "Record could not be retrieved from the database.")}</p>
                <button type="button" class="btn btn-outline-primary btn-sm rounded-pill px-3" onclick="handleViewHistory('${type}', ${id})">
                    <i class="bi bi-arrow-clockwise me-1"></i> Try Again
                </button>
            </div>
        `;
    } finally {
        isModalLoading = false;
    }
}

/**
 * Opens delete confirmation dialog.
 */
function openDeleteConfirmation(type, id) {
    itemPendingDeletion = { type, id };
    const modalEl = document.getElementById("historyDeleteModal");
    const detailsEl = document.getElementById("historyDeleteModalDetails");

    if (detailsEl) {
        detailsEl.textContent = `You are about to delete ${type.toUpperCase()} #${id}. This cannot be undone.`;
    }

    if (modalEl) {
        const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
        bsModal.show();
    }
}

/**
 * Sends authenticated DELETE request to backend, smoothly updates current page.
 */
async function executeDelete(type, id) {
    const confirmBtn = document.getElementById("btn-confirm-delete");
    const origHtml = confirmBtn?.innerHTML;

    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>Deleting...`;
    }

    try {
        let endpoint = "";
        if (type === "document") endpoint = `/documents/${id}`;
        else if (type === "summary") endpoint = `/summaries/${id}`;
        else if (type === "quiz") endpoint = `/quizzes/attempts/${id}`;
        else if (type === "translation") endpoint = `/translations/${id}`;

        const res = await apiClient.delete(endpoint);
        if (res && res.status === "success") {
            // Close delete confirmation modal
            const modalEl = document.getElementById("historyDeleteModal");
            if (modalEl) {
                const bsModal = bootstrap.Modal.getInstance(modalEl);
                if (bsModal) bsModal.hide();
            }

            // If the current page had only 1 item and we're past page 1, step back
            if (currentActivities.length === 1 && currentPage > 1) {
                currentPage -= 1;
            }

            // Re-fetch current page from server to synchronize counts and items
            await loadHistory(currentPage);
            showAlert("history-alert", `${type.toUpperCase()} #${id} has been permanently deleted.`, "success");
        } else {
            throw new Error(res?.message || "Deletion failed on server.");
        }
    } catch (err) {
        console.error("Deletion error:", err);
        showAlert("history-alert", `Failed to delete record: ${err.message || "Unknown error"}`, "danger");
    } finally {
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = origHtml;
        }
        itemPendingDeletion = null;
    }
}

function showAlert(containerId, message, type = "info") {
    const alertBox = document.getElementById(containerId);
    if (!alertBox) return;

    alertBox.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show rounded-3 p-3 shadow-xs" role="alert">
            <div class="d-flex align-items-center gap-2">
                <i class="bi ${type === 'success' ? 'bi-check-circle-fill' : type === 'danger' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill'} fs-5"></i>
                <div>${escapeHtml(message)}</div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    setTimeout(() => {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alertBox.querySelector(".alert"));
        if (bsAlert) bsAlert.close();
    }, 5000);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/[&<>'"]/g, tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    }[tag] || tag));
}
