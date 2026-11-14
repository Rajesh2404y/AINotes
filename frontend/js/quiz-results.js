/**
 * Quiz Results and Detailed Review Controller.
 * Visualizes user test performance, computes accuracy metrics,
 * and renders question-by-question explanations with answer highlights.
 */

document.addEventListener("DOMContentLoaded", async () => {
    // Verify Authentication
    if (typeof checkAuth === "function" && !checkAuth()) {
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const attemptId = urlParams.get("attempt_id") || sessionStorage.getItem("active_attempt_id");

    if (!attemptId) {
        // Fallback demo message if accessed without an attempt
        renderEmptyState();
        return;
    }

    try {
        const res = await apiClient.get(`/quizzes/attempts/${attemptId}`);
        const attemptData = res.data;
        renderResults(attemptData);
    } catch (err) {
        console.error("Failed to load attempt details:", err);
        const breakdownList = document.getElementById("results-breakdown-list");
        if (breakdownList) {
            breakdownList.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i> Failed to load assessment results: ${escapeHtml(err.message)}
                </div>
            `;
        }
    }
});

function renderEmptyState() {
    const scorePercent = document.getElementById("results-score-percent");
    if (scorePercent) scorePercent.textContent = "--";
    const breakdownList = document.getElementById("results-breakdown-list");
    if (breakdownList) {
        breakdownList.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="bi bi-patch-question fs-1 d-block mb-3"></i>
                <h6>No Quiz Attempt Selected</h6>
                <p class="small">Take a quiz first to view your scores and answer breakdown.</p>
                <a href="quiz-config.html" class="btn btn-primary btn-sm rounded-pill px-3">Start a Quiz</a>
            </div>
        `;
    }
}

function renderResults(data) {
    const scorePercent = document.getElementById("results-score-percent");
    const correctCountEl = document.getElementById("results-correct-count");
    const totalCountEl = document.getElementById("results-total-count");
    const timeSpentEl = document.getElementById("results-time-spent");
    const performanceRatingEl = document.getElementById("results-rating");
    const breakdownList = document.getElementById("results-breakdown-list");

    const percentage = Math.round(data.percentage || 0);
    const score = data.score || 0;
    const total = data.total_questions || 0;

    if (scorePercent) scorePercent.textContent = `${percentage}%`;
    if (correctCountEl) correctCountEl.textContent = score;
    if (totalCountEl) totalCountEl.textContent = total;

    if (timeSpentEl) {
        timeSpentEl.textContent = "Evaluated by AI Engine";
    }

    if (performanceRatingEl) {
        if (percentage >= 80) {
            performanceRatingEl.innerHTML = '<span class="badge bg-success-subtle text-success px-3 py-2 rounded-pill"><i class="bi bi-trophy-fill me-1"></i> Excellent Mastery!</span>';
        } else if (percentage >= 50) {
            performanceRatingEl.innerHTML = '<span class="badge bg-warning-subtle text-warning px-3 py-2 rounded-pill"><i class="bi bi-star-fill me-1"></i> Good Effort, Review Concepts</span>';
        } else {
            performanceRatingEl.innerHTML = '<span class="badge bg-danger-subtle text-danger px-3 py-2 rounded-pill"><i class="bi bi-book me-1"></i> Needs Additional Study</span>';
        }
    }

    // Question breakdown
    const responses = data.responses || [];
    if (breakdownList && responses.length > 0) {
        breakdownList.innerHTML = responses.map((item, idx) => {
            const isCorrect = item.is_correct;
            const statusBorder = isCorrect ? "border-success" : "border-danger";
            const icon = isCorrect
                ? '<i class="bi bi-check-circle-fill text-success fs-5"></i>'
                : '<i class="bi bi-x-circle-fill text-danger fs-5"></i>';

            return `
                <div class="card p-4 mb-3 border-start border-4 ${statusBorder} shadow-sm">
                    <div class="d-flex align-items-start gap-3">
                        <div class="mt-1">${icon}</div>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="fw-bold mb-0">Question ${idx + 1}: ${escapeHtml(item.question_text || '')}</h6>
                                <span class="badge bg-secondary-subtle text-secondary small">${(item.question_type || 'MCQ').toUpperCase()}</span>
                            </div>
                            
                            <div class="small mb-2">
                                <span class="text-muted">Your Answer:</span>
                                <span class="fw-bold ${isCorrect ? 'text-success' : 'text-danger'}">
                                    ${escapeHtml(item.selected_answer || 'No answer submitted')}
                                </span>
                            </div>

                            ${!isCorrect ? `
                                <div class="small mb-2">
                                    <span class="text-muted">Correct Answer:</span>
                                    <span class="fw-bold text-success">${escapeHtml(item.correct_answer || '')}</span>
                                </div>
                            ` : ''}

                            ${item.explanation ? `
                                <div class="p-2 rounded bg-body-secondary border text-body small mt-2">
                                    <strong class="text-primary"><i class="bi bi-info-circle me-1"></i> Explanation:</strong>
                                    <span class="d-block mt-1">${escapeHtml(item.explanation)}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
