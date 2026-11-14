/**
 * Dashboard Controller.
 * Fetches real database metrics from /api/dashboard endpoints,
 * renders KPI cards, displays 3 Chart.js visualizations with theme awareness,
 * manages 4 explicit widget states (Loading, Success, Empty, Error with Retry),
 * and renders recent activity feeds and Phase 9 adaptive learning insights.
 */

let quizChartInstance = null;
let weeklyChartInstance = null;
let categoryChartInstance = null;
let isLoadingDashboard = false;

document.addEventListener("DOMContentLoaded", async () => {
    if (typeof authManager !== "undefined" && !authManager.isAuthenticated()) {
        return; // Guarded by navigation.js
    }

    try {
        await loadDashboardData();
    } catch (err) {
        console.error("Dashboard initialization error:", err);
    }

    // Re-render chart colors when theme toggles
    window.addEventListener("themeChanged", () => {
        if (window.lastPerformanceData) {
            renderCharts(window.lastPerformanceData);
        }
    });
});

/**
 * Shows loading state for KPIs and activities feed.
 */
function showDashboardLoadingState() {
    const activityContainer = document.getElementById("recent-activities-list");
    if (activityContainer) {
        activityContainer.innerHTML = `
            <div class="text-center py-5 text-muted">
                <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                <span>Loading activity history...</span>
            </div>
        `;
    }
}

/**
 * Displays an error banner with a Retry button when fetching dashboard data fails.
 */
function showDashboardErrorState(errorMessage) {
    const activityContainer = document.getElementById("recent-activities-list");
    if (activityContainer) {
        activityContainer.innerHTML = `
            <div class="p-4 text-center">
                <div class="text-danger mb-2">
                    <i class="bi bi-exclamation-triangle-fill fs-2"></i>
                </div>
                <h6 class="fw-bold mb-1 text-danger">Unable to Load Activities</h6>
                <p class="text-muted small mb-3">${escapeHtml(errorMessage || "Failed to communicate with server.")}</p>
                <button type="button" class="btn btn-outline-danger btn-sm rounded-pill px-3" onclick="loadDashboardData()">
                    <i class="bi bi-arrow-clockwise me-1"></i> Retry
                </button>
            </div>
        `;
    }
}

/**
 * Loads all dashboard data concurrently from the backend with error recovery.
 */
async function loadDashboardData() {
    if (isLoadingDashboard) return;
    isLoadingDashboard = true;

    showDashboardLoadingState();

    try {
        // Parallel requests to backend APIs
        const [statsRes, activitiesRes, perfRes, learningRes, diffRes] = await Promise.allSettled([
            apiClient.get("/dashboard/stats"),
            apiClient.get("/dashboard/activities?limit=8"),
            apiClient.get("/dashboard/performance"),
            apiClient.get("/learning/overview"),
            apiClient.get("/learning/adaptive-difficulty"),
        ]);

        // 1. KPIs
        if (statsRes.status === "fulfilled" && statsRes.value && statsRes.value.status === "success") {
            populateKPIs(statsRes.value.stats);
        } else {
            console.warn("KPI stats fallback triggered:", statsRes.reason);
            populateKPIs({
                total_documents: 0,
                summaries_generated: 0,
                quizzes_attempted: 0,
                average_quiz_score: 0,
                translations_completed: 0,
                study_streak_days: 0
            });
        }

        // 2. Activities Timeline (Handles success, empty, or error)
        if (activitiesRes.status === "fulfilled" && activitiesRes.value && activitiesRes.value.status === "success") {
            populateActivities(activitiesRes.value.activities || []);
        } else {
            const errReason = activitiesRes.reason ? (activitiesRes.reason.message || String(activitiesRes.reason)) : "Failed to load recent activity.";
            showDashboardErrorState(errReason);
        }

        // 3. Performance Visualizations
        if (perfRes.status === "fulfilled" && perfRes.value && perfRes.value.status === "success") {
            window.lastPerformanceData = perfRes.value.performance;
            renderCharts(perfRes.value.performance);
        } else {
            renderEmptyCharts();
        }

        // 4. Learning Overview Insights
        if (learningRes.status === "fulfilled" && learningRes.value && learningRes.value.status === "success") {
            populateLearningInsights(learningRes.value.data);
        }

        // 5. Recommended Adaptive Difficulty
        if (diffRes.status === "fulfilled" && diffRes.value && diffRes.value.status === "success") {
            const diffEl = document.getElementById("insight-difficulty");
            if (diffEl && diffRes.value.data && diffRes.value.data.recommended_difficulty) {
                diffEl.textContent = diffRes.value.data.recommended_difficulty.toUpperCase();
            }
        }

    } catch (err) {
        console.error("Critical error loading dashboard data:", err);
        showDashboardErrorState(err.message || "An unexpected error occurred.");
    } finally {
        isLoadingDashboard = false;
    }
}

/**
 * Populates Phase 9 Adaptive Learning Insights.
 */
function populateLearningInsights(overview) {
    if (!overview) return;

    // Recommended Next Action
    const action = overview.recommended_next_action || {};
    const titleEl = document.getElementById("next-action-title");
    const descEl = document.getElementById("next-action-desc");
    const btnEl = document.getElementById("next-action-btn");

    if (titleEl) titleEl.textContent = action.title || "Continue Learning";
    if (descEl) descEl.textContent = action.description || "Take a quiz or read notes.";
    if (btnEl) {
        if (action.action_type === "review_weak_topic") {
            btnEl.href = "summary.html";
            btnEl.textContent = "Review Notes";
        } else {
            btnEl.href = "quiz-config.html";
            btnEl.textContent = "Practice Quiz";
        }
    }

    // Weak Topics Badges
    const weakContainer = document.getElementById("weak-topics-badges");
    if (weakContainer) {
        const weak = overview.weak_topics || [];
        if (weak.length > 0) {
            weakContainer.innerHTML = weak.map(t => 
                `<span class="badge bg-danger-subtle text-danger border border-danger-subtle py-1 px-2 rounded-pill small">${escapeHtml(t)}</span>`
            ).join(" ");
        } else {
            weakContainer.innerHTML = `<span class="text-muted small">No weak topics detected</span>`;
        }
    }

    // Strong Topics Badges
    const strongContainer = document.getElementById("strong-topics-badges");
    if (strongContainer) {
        const strong = overview.strong_topics || [];
        if (strong.length > 0) {
            strongContainer.innerHTML = strong.map(t => 
                `<span class="badge bg-success-subtle text-success border border-success-subtle py-1 px-2 rounded-pill small">${escapeHtml(t)}</span>`
            ).join(" ");
        } else {
            strongContainer.innerHTML = `<span class="text-muted small">Complete more quizzes to evaluate</span>`;
        }
    }
}

/**
 * Updates KPI stat cards on the dashboard with real synchronized data.
 */
function populateKPIs(stats) {
    if (!stats) return;

    const elDocs = document.getElementById("kpi-docs");
    const elSummaries = document.getElementById("kpi-summaries");
    const elQuizzes = document.getElementById("kpi-quizzes");
    const elAvgScore = document.getElementById("kpi-avg-score");
    const elTranslations = document.getElementById("kpi-translations");
    const elStreak = document.getElementById("kpi-streak");

    const docs = stats.total_documents ?? 0;
    const summaries = stats.summaries_generated ?? stats.total_summaries ?? 0;
    const quizzes = stats.quizzes_attempted ?? stats.total_quizzes_completed ?? 0;
    const avgScore = Math.round(stats.average_quiz_score ?? 0);
    const translations = stats.translations_completed ?? stats.total_translations ?? 0;
    const streak = stats.study_streak_days ?? (stats.learning_activities > 0 ? 1 : 0);

    if (elDocs) elDocs.textContent = docs;
    if (elSummaries) elSummaries.textContent = summaries;
    if (elQuizzes) elQuizzes.textContent = quizzes;
    if (elAvgScore) elAvgScore.textContent = `${avgScore}%`;
    if (elTranslations) elTranslations.textContent = translations;
    if (elStreak) elStreak.textContent = `${streak}d`;
}

/**
 * Renders recent activities list or explicit empty state placeholder.
 */
function populateActivities(activities) {
    const container = document.getElementById("recent-activities-list");
    if (!container) return;

    if (!activities || activities.length === 0) {
        container.innerHTML = `
            <div class="empty-state text-center py-5 px-3">
                <div class="empty-state-icon mb-3 text-muted">
                    <i class="bi bi-clock-history fs-1 opacity-50"></i>
                </div>
                <h6 class="fw-bold mb-1">No Recent Activity</h6>
                <p class="text-muted small mb-3">Upload your first document or take a quiz to start tracking your learning progress.</p>
                <a href="upload.html" class="btn btn-primary btn-sm rounded-pill px-3">
                    <i class="bi bi-cloud-arrow-up me-1"></i> Upload Document
                </a>
            </div>
        `;
        return;
    }

    const typeMeta = {
        document: { icon: "bi-file-earmark-text", color: "text-primary", bg: "bg-primary-subtle" },
        summary: { icon: "bi-card-text", color: "text-success", bg: "bg-success-subtle" },
        quiz: { icon: "bi-patch-check", color: "text-warning", bg: "bg-warning-subtle" },
        translation: { icon: "bi-translate", color: "text-info", bg: "bg-info-subtle" }
    };

    const rowsHtml = activities.map(item => {
        const meta = typeMeta[item.type] || { icon: "bi-circle", color: "text-secondary", bg: "bg-secondary-subtle" };
        const timeAgo = formatTimeAgo(item.timestamp);
        const destLink = item.link || "history.html";

        return `
            <div class="d-flex align-items-center justify-content-between p-3 border-bottom activity-item">
                <div class="d-flex align-items-center gap-3 overflow-hidden">
                    <div class="activity-icon ${meta.bg} ${meta.color} rounded-3 p-2 flex-shrink-0">
                        <i class="bi ${meta.icon} fs-5"></i>
                    </div>
                    <div class="overflow-hidden">
                        <h6 class="mb-0 fw-semibold text-truncate" style="max-width: 280px;">${escapeHtml(item.title || 'Untitled Activity')}</h6>
                        <span class="text-muted small text-truncate d-block" style="max-width: 280px;">${escapeHtml(item.details || item.type_label || item.type)}</span>
                    </div>
                </div>
                <div class="text-end flex-shrink-0 ms-2">
                    <span class="text-muted small d-block" title="${formatDateTime(item.timestamp, null, '')}">${timeAgo}</span>
                    <a href="${destLink}" class="small text-decoration-none text-primary fw-medium">View</a>
                </div>
            </div>
        `;
    }).join("");

    container.innerHTML = `<div class="activity-feed">${rowsHtml}</div>`;
}

/**
 * Renders the 3 Chart.js graphs with theme responsiveness and cleanup.
 */
function renderCharts(perf) {
    if (typeof Chart === "undefined") {
        console.warn("Chart.js is not loaded.");
        return;
    }

    const isDark = document.documentElement.getAttribute("data-bs-theme") === "dark";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
    const textColor = isDark ? "#cbd5e1" : "#64748b";

    // 1. Quiz Performance Line Chart
    const quizCanvas = document.getElementById("quizPerformanceChart");
    if (quizCanvas) {
        const quizCtx = quizCanvas.getContext("2d");
        if (quizChartInstance) {
            quizChartInstance.destroy();
            quizChartInstance = null;
        }

        const dates = (perf.quiz_trends && perf.quiz_trends.dates && perf.quiz_trends.dates.length > 0)
            ? perf.quiz_trends.dates
            : (perf.labels && perf.labels.length > 0 ? perf.labels : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Today"]);

        const scores = (perf.quiz_trends && perf.quiz_trends.scores && perf.quiz_trends.scores.length > 0)
            ? perf.quiz_trends.scores
            : (perf.percentages && perf.percentages.length > 0 ? perf.percentages : [0, 0, 0, 0, 0, 0, 0]);

        quizChartInstance = new Chart(quizCtx, {
            type: "line",
            data: {
                labels: dates,
                datasets: [{
                    label: "Quiz Score (%)",
                    data: scores,
                    borderColor: "#6366f1",
                    backgroundColor: isDark ? "rgba(99, 102, 241, 0.2)" : "rgba(99, 102, 241, 0.12)",
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: "#6366f1",
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `Score: ${ctx.parsed.y}%`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: textColor, font: { family: "'Inter', sans-serif" } }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: gridColor },
                        ticks: {
                            color: textColor,
                            stepSize: 20,
                            font: { family: "'Inter', sans-serif" },
                            callback: (val) => `${val}%`
                        }
                    }
                }
            }
        });
    }

    // 2. Weekly Activity Bar Chart
    const weeklyCanvas = document.getElementById("weeklyActivityChart");
    if (weeklyCanvas) {
        const weeklyCtx = weeklyCanvas.getContext("2d");
        if (weeklyChartInstance) {
            weeklyChartInstance.destroy();
            weeklyChartInstance = null;
        }

        const weekly = perf.weekly_activity || {};
        const labels = weekly.labels || ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        const docCounts = weekly.documents || [0, 0, 0, 0, 0, 0, 0];
        const summaryCounts = weekly.summaries || [0, 0, 0, 0, 0, 0, 0];
        const quizCounts = weekly.quizzes || [0, 0, 0, 0, 0, 0, 0];
        const transCounts = weekly.translations || [0, 0, 0, 0, 0, 0, 0];

        weeklyChartInstance = new Chart(weeklyCtx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    { label: "Documents", data: docCounts, backgroundColor: "#6366f1", borderRadius: 4 },
                    { label: "Summaries", data: summaryCounts, backgroundColor: "#10b981", borderRadius: 4 },
                    { label: "Quizzes", data: quizCounts, backgroundColor: "#f59e0b", borderRadius: 4 },
                    { label: "Translations", data: transCounts, backgroundColor: "#06b6d4", borderRadius: 4 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                        labels: { color: textColor, boxWidth: 12, padding: 12, font: { family: "'Inter', sans-serif" } }
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: { display: false },
                        ticks: { color: textColor, font: { family: "'Inter', sans-serif" } }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: { color: textColor, stepSize: 1, font: { family: "'Inter', sans-serif" } }
                    }
                }
            }
        });
    }

    // 3. Activity Distribution Doughnut Chart
    const catCanvas = document.getElementById("categoryDistributionChart");
    if (catCanvas) {
        const catCtx = catCanvas.getContext("2d");
        if (categoryChartInstance) {
            categoryChartInstance.destroy();
            categoryChartInstance = null;
        }

        let catCounts = [0, 0, 0, 0];
        if (perf.category_distribution && Array.isArray(perf.category_distribution.counts)) {
            catCounts = perf.category_distribution.counts;
        } else if (perf.distribution) {
            catCounts = [
                perf.distribution.documents || 0,
                perf.distribution.summaries || 0,
                perf.distribution.quizzes || 0,
                perf.distribution.translations || 0
            ];
        }

        const hasAnyData = catCounts.some(c => c > 0);
        const displayData = hasAnyData ? catCounts : [1, 1, 1, 1]; // subtle baseline placeholder if empty
        const colors = hasAnyData
            ? ["#6366f1", "#10b981", "#f59e0b", "#06b6d4"]
            : (isDark ? ["#27354f", "#1e293b", "#334155", "#1e293b"] : ["#e2e8f0", "#f1f5f9", "#cbd5e1", "#e2e8f0"]);

        categoryChartInstance = new Chart(catCtx, {
            type: "doughnut",
            data: {
                labels: ["Documents", "Summaries", "Quizzes", "Translations"],
                datasets: [{
                    data: displayData,
                    backgroundColor: colors,
                    hoverOffset: 4,
                    borderWidth: isDark ? 2 : 1,
                    borderColor: isDark ? "#151d30" : "#ffffff"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: textColor, boxWidth: 12, padding: 12, font: { family: "'Inter', sans-serif" } }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => hasAnyData ? `${ctx.label}: ${ctx.raw}` : "No activities yet"
                        }
                    }
                },
                cutout: "70%"
            }
        });
    }
}

function renderEmptyCharts() {
    renderCharts({
        quiz_trends: { dates: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], scores: [0, 0, 0, 0, 0, 0, 0] },
        weekly_activity: { labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], documents: [0,0,0,0,0,0,0], summaries: [0,0,0,0,0,0,0], quizzes: [0,0,0,0,0,0,0], translations: [0,0,0,0,0,0,0] },
        category_distribution: { labels: ["Documents", "Summaries", "Quizzes", "Translations"], counts: [0,0,0,0] }
    });
}

function formatTimeAgo(isoString) {
    if (typeof window !== "undefined" && window.DateUtils && typeof window.DateUtils.formatTimeAgo === "function") {
        return window.DateUtils.formatTimeAgo(isoString);
    }
    if (!isoString) return "Recently";
    try {
        const date = typeof parseUtcDate === "function" ? parseUtcDate(isoString) : new Date(isoString);
        if (!date) return "Recently";
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 2) return "Just now";
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays === 1) return "Yesterday";
        if (diffDays < 7) return `${diffDays}d ago`;
        return typeof formatDisplayDate === "function" ? formatDisplayDate(date) : date.toISOString().slice(0, 10);
    } catch {
        return "Recently";
    }
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
