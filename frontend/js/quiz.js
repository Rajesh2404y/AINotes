/**
 * Interactive Quiz Controller.
 * Manages Quiz Configuration, Real-time Test Execution, Answer Preservation,
 * and Server-side Grading Handoff.
 */

document.addEventListener("DOMContentLoaded", async () => {
    // Verify Authentication
    if (typeof checkAuth === "function" && !checkAuth()) {
        return;
    }

    // --- 1. QUIZ CONFIGURATION SCREEN (quiz-config.html) ---
    const configForm = document.getElementById("quiz-config-form");
    if (configForm) {
        await initQuizConfig();
        return;
    }

    // --- 2. INTERACTIVE QUIZ RUNNER (quiz.html) ---
    const quizRunner = document.getElementById("quiz-runner-container");
    if (quizRunner) {
        await initQuizRunner();
    }
});

/**
 * Initializes the Quiz Configuration screen with dynamic documents and summaries.
 */
async function initQuizConfig() {
    const docSelect = document.getElementById("sourceDocument");
    const summarySelect = document.getElementById("sourceSummary");
    const configForm = document.getElementById("quiz-config-form");
    const submitBtn = configForm?.querySelector('button[type="submit"]');

    const activeDocId = sessionStorage.getItem("active_document_id");
    const activeSummaryId = sessionStorage.getItem("active_summary_id");

    // Populate Documents
    try {
        const docRes = await apiClient.get("/documents?limit=50");
        const docs = docRes.documents || docRes.data?.documents || docRes.data || [];
        if (docSelect) {
            docSelect.innerHTML = '<option value="">-- Choose a Study Document --</option>';
            docs.forEach(doc => {
                const opt = document.createElement("option");
                opt.value = doc.id;
                opt.textContent = `${doc.title || doc.original_filename} (${doc.total_words || 0} words)`;
                if (activeDocId && String(doc.id) === String(activeDocId)) {
                    opt.selected = true;
                }
                docSelect.appendChild(opt);
            });
        }
    } catch (err) {
        console.warn("Could not fetch documents for quiz config:", err);
    }

    // Populate Summaries
    try {
        const sumRes = await apiClient.get("/summaries?per_page=50");
        const summaries = sumRes.summaries || sumRes.data?.summaries || sumRes.data || [];
        if (summarySelect) {
            summarySelect.innerHTML = '<option value="">-- Optional: Select a Specific Summary --</option>';
            summaries.forEach(s => {
                const opt = document.createElement("option");
                opt.value = s.id;
                opt.textContent = `Summary #${s.id} (${s.summary_type?.toUpperCase()}) - Doc #${s.document_id}`;
                if (activeSummaryId && String(s.id) === String(activeSummaryId)) {
                    opt.selected = true;
                }
                summarySelect.appendChild(opt);
            });
        }
    } catch (err) {
        console.warn("Could not fetch summaries for quiz config:", err);
    }

    // Form Submission
    if (configForm) {
        configForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const docId = docSelect?.value ? parseInt(docSelect.value, 10) : null;
            const sumId = summarySelect?.value ? parseInt(summarySelect.value, 10) : null;

            if (!docId && !sumId) {
                showAlert("config-alert", "Please select at least a source document or summary notes.", "warning");
                return;
            }

            const formatVal = document.querySelector('input[name="quizFormat"]:checked')?.value || "mixed";
            const diffVal = document.querySelector('input[name="quizDifficulty"]:checked')?.value || "Medium";
            const countVal = parseInt(document.getElementById("questionCount")?.value || "5", 10);
            const enableTimer = document.getElementById("enableTimer")?.checked ?? true;

            const questionTypes = formatVal === "mixed" ? ["mcq", "true_false", "one_word", "fill_blank"] : [formatVal];

            const origHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Generating Quiz Questions...';

            try {
                const res = await apiClient.post("/quizzes/generate", {
                    document_id: docId,
                    summary_id: sumId,
                    question_types: questionTypes,
                    difficulty: diffVal.toLowerCase(),
                    total_questions: countVal
                });

                const quiz = res.data;
                sessionStorage.setItem("active_quiz_id", quiz.id);
                sessionStorage.setItem("active_quiz_timed", enableTimer ? "true" : "false");
                sessionStorage.setItem("active_quiz_difficulty", diffVal);

                window.location.href = `quiz.html?quiz_id=${quiz.id}`;
            } catch (err) {
                console.error("Quiz generation error:", err);
                showAlert("config-alert", err.message || "Failed to generate quiz. Please ensure the document has sufficient text.", "danger");
                submitBtn.disabled = false;
                submitBtn.innerHTML = origHtml;
            }
        });
    }
}

/**
 * Initializes the Interactive Stepper for taking the quiz.
 */
async function initQuizRunner() {
    const urlParams = new URLSearchParams(window.location.search);
    const quizId = urlParams.get("quiz_id") || sessionStorage.getItem("active_quiz_id");

    if (!quizId) {
        alert("No active quiz session found. Redirecting to configuration.");
        window.location.href = "quiz-config.html";
        return;
    }

    let quizData = null;
    try {
        const res = await apiClient.get(`/quizzes/${quizId}`);
        quizData = res.data;
    } catch (err) {
        console.error("Failed to load quiz data:", err);
        alert("Could not load quiz questions: " + (err.message || "Unknown error"));
        window.location.href = "quiz-config.html";
        return;
    }

    const questions = quizData.questions || [];
    if (questions.length === 0) {
        alert("This quiz has no questions available.");
        window.location.href = "quiz-config.html";
        return;
    }

    let currentIndex = 0;
    const userAnswers = {}; // Mapping question_id -> answer_string
    const flaggedQuestions = new Set();
    const isTimed = sessionStorage.getItem("active_quiz_timed") !== "false";
    let secondsLeft = isTimed ? questions.length * 60 : 0;
    let timerInterval = null;

    // Timer setup
    if (isTimed) {
        const timerEl = document.getElementById("quiz-timer-display");
        timerInterval = setInterval(() => {
            if (secondsLeft <= 0) {
                clearInterval(timerInterval);
                alert("Time is up! Submitting your answers automatically.");
                executeQuizSubmission();
                return;
            }
            secondsLeft--;
            const mins = Math.floor(secondsLeft / 60);
            const secs = secondsLeft % 60;
            if (timerEl) {
                timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            }
        }, 1000);
    } else {
        const timerWrapper = document.getElementById("quiz-timer-display")?.parentElement;
        if (timerWrapper) timerWrapper.classList.add("d-none");
    }

    renderCurrentQuestion();

    function renderCurrentQuestion() {
        const q = questions[currentIndex];
        const titleEl = document.getElementById("quiz-question-title");
        const numberEl = document.getElementById("quiz-question-num");
        const totalEl = document.getElementById("quiz-question-total");
        const progressBar = document.getElementById("quiz-progress-bar");
        const optionsContainer = document.getElementById("quiz-options-container");
        const flagBtn = document.getElementById("btn-flag-question");
        const prevBtn = document.getElementById("btn-prev-question");
        const nextBtn = document.getElementById("btn-next-question");
        const submitBtn = document.getElementById("btn-submit-quiz");

        if (numberEl) numberEl.textContent = currentIndex + 1;
        if (totalEl) totalEl.textContent = questions.length;
        if (titleEl) titleEl.textContent = q.question_text;

        const progressPercent = Math.round(((currentIndex + 1) / questions.length) * 100);
        if (progressBar) progressBar.style.width = `${progressPercent}%`;

        if (flagBtn) {
            flagBtn.innerHTML = flaggedQuestions.has(currentIndex)
                ? '<i class="bi bi-flag-fill text-warning me-1"></i> Flagged'
                : '<i class="bi bi-flag me-1"></i> Flag for Review';
        }

        if (prevBtn) prevBtn.disabled = (currentIndex === 0);
        if (nextBtn) {
            if (currentIndex === questions.length - 1) {
                nextBtn.classList.add("d-none");
                if (submitBtn) submitBtn.classList.remove("d-none");
            } else {
                nextBtn.classList.remove("d-none");
                if (submitBtn) submitBtn.classList.add("d-none");
            }
        }

        // Render Question Inputs according to question_type
        if (optionsContainer) {
            optionsContainer.innerHTML = "";
            const currentAnswer = userAnswers[q.id];

            if (q.question_type === "mcq") {
                const options = q.options || [];
                options.forEach((optText, optIdx) => {
                    const isSelected = currentAnswer === optText;
                    const optEl = document.createElement("div");
                    optEl.className = `option-card card p-3 mb-3 cursor-pointer ${isSelected ? 'selected' : ''}`;
                    optEl.setAttribute("role", "button");
                    optEl.setAttribute("tabindex", "0");
                    optEl.setAttribute("data-value", optText);
                    optEl.setAttribute("aria-pressed", isSelected ? "true" : "false");
                    optEl.setAttribute("aria-label", `Option ${String.fromCharCode(65 + optIdx)}: ${optText}`);

                    optEl.innerHTML = `
                        <div class="d-flex align-items-center gap-3">
                            <div class="option-indicator ${isSelected ? 'selected' : ''}">
                                ${String.fromCharCode(65 + optIdx)}
                            </div>
                            <div class="option-text">${escapeHtml(optText)}</div>
                        </div>
                    `;

                    const handleSelect = () => {
                        userAnswers[q.id] = optText;
                        // In-place class update without destroying DOM or flickering
                        optionsContainer.querySelectorAll(".option-card").forEach(card => {
                            const selected = card.getAttribute("data-value") === optText;
                            card.classList.toggle("selected", selected);
                            card.setAttribute("aria-pressed", selected ? "true" : "false");
                            const ind = card.querySelector(".option-indicator");
                            if (ind) ind.classList.toggle("selected", selected);
                        });
                    };

                    optEl.addEventListener("click", handleSelect);
                    optEl.addEventListener("keydown", (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            handleSelect();
                        }
                    });
                    optionsContainer.appendChild(optEl);
                });

            } else if (q.question_type === "true_false") {
                ["True", "False"].forEach(choice => {
                    const isSelected = (currentAnswer || "").toLowerCase() === choice.toLowerCase();
                    const optEl = document.createElement("div");
                    optEl.className = `option-card card p-3 mb-3 cursor-pointer ${isSelected ? 'selected' : ''}`;
                    optEl.setAttribute("role", "button");
                    optEl.setAttribute("tabindex", "0");
                    optEl.setAttribute("data-value", choice);
                    optEl.setAttribute("aria-pressed", isSelected ? "true" : "false");
                    optEl.setAttribute("aria-label", `Choice: ${choice}`);

                    optEl.innerHTML = `
                        <div class="d-flex align-items-center gap-3">
                            <div class="option-indicator ${isSelected ? 'selected' : ''}">
                                <i class="bi bi-${choice === 'True' ? 'check-lg' : 'x-lg'}"></i>
                            </div>
                            <div class="option-text fs-5">${choice}</div>
                        </div>
                    `;

                    const handleSelect = () => {
                        userAnswers[q.id] = choice;
                        // In-place class update without destroying DOM or flickering
                        optionsContainer.querySelectorAll(".option-card").forEach(card => {
                            const selected = card.getAttribute("data-value") === choice;
                            card.classList.toggle("selected", selected);
                            card.setAttribute("aria-pressed", selected ? "true" : "false");
                            const ind = card.querySelector(".option-indicator");
                            if (ind) ind.classList.toggle("selected", selected);
                        });
                    };

                    optEl.addEventListener("click", handleSelect);
                    optEl.addEventListener("keydown", (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            handleSelect();
                        }
                    });
                    optionsContainer.appendChild(optEl);
                });

            } else if (q.question_type === "one_word" || q.question_type === "fill_blank") {
                const inputWrapper = document.createElement("div");
                inputWrapper.className = "card p-4 border shadow-xs quiz-input-card";
                inputWrapper.innerHTML = `
                    <label for="free-text-input" class="form-label small fw-bold text-muted mb-2">
                        <i class="bi bi-pencil-square me-1"></i> Type your response below:
                    </label>
                    <input type="text" id="free-text-input" class="form-control form-control-lg quiz-text-input" placeholder="Type answer here..." value="${escapeHtml(currentAnswer || '')}" autocomplete="off">
                    <span class="text-muted small mt-2 d-block">Answers are automatically evaluated with punctuation and casing normalization.</span>
                `;
                optionsContainer.appendChild(inputWrapper);

                const textInput = inputWrapper.querySelector("#free-text-input");
                textInput.addEventListener("input", (e) => {
                    userAnswers[q.id] = e.target.value.trim();
                });
                textInput.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        if (currentIndex < questions.length - 1) {
                            currentIndex++;
                            renderCurrentQuestion();
                        } else {
                            document.getElementById("btn-submit-quiz")?.click();
                        }
                    }
                });
            }
        }
    }

    // Step handlers
    document.getElementById("btn-prev-question")?.addEventListener("click", () => {
        if (currentIndex > 0) {
            currentIndex--;
            renderCurrentQuestion();
        }
    });

    document.getElementById("btn-next-question")?.addEventListener("click", () => {
        if (currentIndex < questions.length - 1) {
            currentIndex++;
            renderCurrentQuestion();
        }
    });

    document.getElementById("btn-flag-question")?.addEventListener("click", () => {
        if (flaggedQuestions.has(currentIndex)) {
            flaggedQuestions.delete(currentIndex);
        } else {
            flaggedQuestions.add(currentIndex);
        }
        renderCurrentQuestion();
    });

    // Confirmation & Submit
    document.getElementById("btn-submit-quiz")?.addEventListener("click", () => {
        const answeredCount = Object.keys(userAnswers).filter(k => userAnswers[k] && userAnswers[k].trim()).length;
        const totalCount = questions.length;

        const modalEl = document.getElementById("confirmSubmitModal");
        if (modalEl && typeof bootstrap !== "undefined") {
            const modalBody = modalEl.querySelector(".modal-body");
            if (modalBody) {
                modalBody.innerHTML = `
                    <i class="bi bi-patch-question text-primary fs-1 d-block mb-3"></i>
                    <h6 class="fw-bold">Ready to complete your test?</h6>
                    <p class="text-muted small mb-2">You answered <strong>${answeredCount}</strong> of <strong>${totalCount}</strong> questions.</p>
                    ${answeredCount < totalCount ? '<div class="alert alert-warning py-1 small">You have unanswered questions. Are you sure you want to proceed?</div>' : ''}
                `;
            }
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        } else {
            executeQuizSubmission();
        }
    });

    document.getElementById("btn-confirm-submit")?.addEventListener("click", () => {
        executeQuizSubmission();
    });

    async function executeQuizSubmission() {
        if (timerInterval) clearInterval(timerInterval);

        const payloadResponses = questions.map(q => ({
            question_id: q.id,
            answer: userAnswers[q.id] || ""
        }));

        try {
            const res = await apiClient.post(`/quizzes/${quizId}/submit`, {
                responses: payloadResponses
            });

            const attemptData = res.data;
            sessionStorage.setItem("active_attempt_id", attemptData.attempt_id);
            window.location.href = `quiz-results.html?attempt_id=${attemptData.attempt_id}`;

        } catch (err) {
            console.error("Submission grading error:", err);
            alert("Submission error: " + (err.message || "Failed to submit quiz."));
        }
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
