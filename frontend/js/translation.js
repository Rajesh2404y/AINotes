/**
 * Multilingual Translation Interface Controller.
 * Manages bilingual split-screen view across 9 supported academic languages,
 * real backend API translation, character counters, clipboard copy, and file export.
 */

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Verify Authentication
    if (typeof checkAuth === "function" && !checkAuth()) {
        return;
    }

    const summarySelect = document.getElementById("summary-select");
    const sourceLangSelect = document.getElementById("source-lang-select");
    const targetLangSelect = document.getElementById("target-lang-select");
    const swapBtn = document.getElementById("btn-swap-languages");
    const sourceTextArea = document.getElementById("source-text");
    const targetTextArea = document.getElementById("target-text");
    const sourceCharCount = document.getElementById("source-char-count");
    const translateBtn = document.getElementById("btn-translate");
    const copyBtn = document.getElementById("btn-copy-translation");
    const exportPdfBtn = document.getElementById("btn-export-pdf");
    const exportTxtBtn = document.getElementById("btn-export-txt");
    const historyContainer = document.getElementById("translation-history-container");

    // Progress Feedback Elements
    const progressCard = document.getElementById("translation-progress-card");
    const progressStepText = document.getElementById("progress-step-text");
    const progressPercentageText = document.getElementById("progress-percentage-text");
    const progressBar = document.getElementById("translation-progress-bar");
    const progressChunkInfo = document.getElementById("progress-chunk-info");
    const progressPerfInfo = document.getElementById("progress-perf-info");

    let currentTranslationId = null;
    let summariesMap = {};

    function updateExportButtonsState() {
        const hasTrans = Boolean(currentTranslationId && targetTextArea && targetTextArea.value.trim());
        if (exportPdfBtn) exportPdfBtn.disabled = !hasTrans;
        if (exportTxtBtn) exportTxtBtn.disabled = !hasTrans;
        if (copyBtn) copyBtn.disabled = !hasTrans;
    }

    updateExportButtonsState();

    function setProgress(step, pct, chunkInfo, perfInfo, isDone = false) {
        if (!progressCard) return;
        progressCard.classList.remove("d-none");
        if (progressStepText) {
            progressStepText.innerHTML = isDone
                ? `<i class="bi bi-check-circle-fill text-success me-2"></i> ${step}`
                : `<span class="spinner-border spinner-border-sm me-2" role="status"></span> ${step}`;
        }
        if (progressPercentageText) progressPercentageText.textContent = `${pct}%`;
        if (progressBar) {
            progressBar.style.width = `${pct}%`;
            progressBar.setAttribute("aria-valuenow", pct);
            if (isDone) {
                progressBar.classList.remove("progress-bar-animated", "bg-primary");
                progressBar.classList.add("bg-success");
            } else {
                progressBar.classList.add("progress-bar-animated", "bg-primary");
                progressBar.classList.remove("bg-success");
            }
        }
        if (progressChunkInfo && chunkInfo) progressChunkInfo.textContent = chunkInfo;
        if (progressPerfInfo && perfInfo) progressPerfInfo.textContent = perfInfo;
    }

    function hideProgress(delayMs = 2500) {
        if (!progressCard) return;
        setTimeout(() => {
            progressCard.classList.add("d-none");
        }, delayMs);
    }

    // 2. Load Supported Languages
    await loadSupportedLanguages();

    // 3. Load Summaries for Selector
    await loadUserSummaries();

    // 4. Load Translation History
    await loadTranslationHistory();

    // Check handoff from Summary page
    const handoffText = sessionStorage.getItem("translate_handoff_text");
    const handoffSummaryId = sessionStorage.getItem("active_summary_id");
    if (handoffText && sourceTextArea) {
        sourceTextArea.value = handoffText;
        updateCharCount();
        sessionStorage.removeItem("translate_handoff_text");
    }
    if (handoffSummaryId && summarySelect) {
        summarySelect.value = handoffSummaryId;
    }

    async function loadSupportedLanguages() {
        try {
            const res = await apiClient.get("/translations/languages");
            const languages = res.data || [];
            if (sourceLangSelect && targetLangSelect) {
                sourceLangSelect.innerHTML = languages.map(l =>
                    `<option value="${l.code}" ${l.code === 'en' ? 'selected' : ''}>${l.name} (${l.native_name})</option>`
                ).join("");

                targetLangSelect.innerHTML = languages.map(l =>
                    `<option value="${l.code}" ${l.code === 'ta' ? 'selected' : ''}>${l.name} (${l.native_name})</option>`
                ).join("");
            }
        } catch (err) {
            console.warn("Failed to load supported languages from API, using defaults:", err);
            if (sourceLangSelect && targetLangSelect && typeof CONFIG !== "undefined") {
                sourceLangSelect.innerHTML = CONFIG.SUPPORTED_LANGUAGES.map(l => `<option value="${l.code}">${l.name}</option>`).join("");
                targetLangSelect.innerHTML = CONFIG.SUPPORTED_LANGUAGES.map(l => `<option value="${l.code}" ${l.code === 'ta' ? 'selected' : ''}>${l.name}</option>`).join("");
            }
        }
    }

    async function loadUserSummaries() {
        try {
            const res = await apiClient.get("/summaries?per_page=50");
            const summaries = res.data?.summaries || [];
            if (summarySelect) {
                summarySelect.innerHTML = '<option value="">-- Choose a Saved Summary to Translate --</option>';
                summaries.forEach(s => {
                    summariesMap[s.id] = s;
                    const opt = document.createElement("option");
                    opt.value = s.id;
                    opt.textContent = `Summary #${s.id} (${(s.summary_type || 'medium').toUpperCase()}) - ${s.summary_text.slice(0, 45)}...`;
                    summarySelect.appendChild(opt);
                });

                if (handoffSummaryId && summariesMap[handoffSummaryId]) {
                    summarySelect.value = handoffSummaryId;
                }
            }
        } catch (err) {
            console.warn("Failed to fetch user summaries:", err);
        }
    }

    // Summary selection change
    if (summarySelect) {
        summarySelect.addEventListener("change", (e) => {
            const sId = e.target.value;
            if (sId && summariesMap[sId]) {
                const s = summariesMap[sId];
                if (sourceTextArea) {
                    sourceTextArea.value = s.summary_text || "";
                    updateCharCount();
                }
            }
        });
    }

    // Swap languages
    if (swapBtn) {
        swapBtn.addEventListener("click", () => {
            const currentSource = sourceLangSelect.value;
            const currentTarget = targetLangSelect.value;
            sourceLangSelect.value = currentTarget;
            targetLangSelect.value = currentSource;

            const tempText = sourceTextArea.value;
            sourceTextArea.value = targetTextArea.value;
            targetTextArea.value = tempText;
            updateCharCount();
        });
    }

    // Character counter
    if (sourceTextArea) {
        sourceTextArea.addEventListener("input", updateCharCount);
    }

    function updateCharCount() {
        if (sourceCharCount && sourceTextArea) {
            sourceCharCount.textContent = `${sourceTextArea.value.length} characters`;
        }
    }

    // Translate Button Click Handler
    if (translateBtn) {
        translateBtn.addEventListener("click", async () => {
            const text = sourceTextArea?.value.trim();
            if (!text) {
                showAlert("translate-alert", "Please enter or select summary text to translate.", "warning");
                return;
            }

            const sourceLang = sourceLangSelect.value;
            const targetLang = targetLangSelect.value;

            if (sourceLang === targetLang) {
                showAlert("translate-alert", "Source and target languages cannot be identical.", "warning");
                return;
            }

            let summaryId = summarySelect?.value;

            // If user typed directly without selecting a summary, pick the first available or show warning
            if (!summaryId) {
                const availableSummaries = Object.keys(summariesMap);
                if (availableSummaries.length > 0) {
                    summaryId = availableSummaries[0];
                } else {
                    showAlert("translate-alert", "Please select a generated summary to translate from the dropdown.", "warning");
                    return;
                }
            }

            const origHtml = translateBtn.innerHTML;
            translateBtn.disabled = true;
            translateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Translating Notes...';

            setProgress("Checking translation cache...", 25, "Querying saved translations...", "Cache lookup");

            let progressTimer = null;
            let currentPct = 25;
            progressTimer = setInterval(() => {
                if (currentPct < 85) {
                    currentPct += 15;
                    if (currentPct <= 45) {
                        setProgress("Preparing document chunks...", currentPct, "Token-aware boundary analysis active", "Batch staging");
                    } else if (currentPct <= 70) {
                        setProgress("Neural translation in progress...", currentPct, "Translating text chunks concurrently", "Multi-backend MT");
                    } else {
                        setProgress("Reassembling & preserving terminology...", currentPct, "Preserving academic glossaries", "Unicode validation");
                    }
                }
            }, 350);

            try {
                const res = await apiClient.post("/translations/generate", {
                    summary_id: parseInt(summaryId, 10),
                    source_language: sourceLang,
                    target_language: targetLang
                });

                clearInterval(progressTimer);

                const translation = res.data;
                currentTranslationId = translation.id;
                if (targetTextArea) {
                    targetTextArea.value = translation.translated_text || "";
                }

                updateExportButtonsState();

                const isCached = Boolean(translation.is_cached);
                if (isCached) {
                    setProgress("Translation retrieved instantly from cache!", 100, "Cache hit (< 15 ms)", "Zero inference latency", true);
                    showAlert("translate-alert", `Retrieved existing translation #${translation.id} from cache (< 15 ms)!`, "info");
                } else {
                    const dur = (translation.processing_duration || 0).toFixed(2);
                    const speed = translation.metadata?.tokens_per_second ? `${translation.metadata.tokens_per_second} tokens/s` : "High-speed active";
                    setProgress("Translation completed successfully!", 100, `Completed in ${dur}s (${speed})`, "Ready to export", true);
                    showAlert("translate-alert", `Successfully translated into ${targetLang.toUpperCase()} in ${dur}s!`, "success");
                }

                hideProgress(3000);
                await loadTranslationHistory();

            } catch (err) {
                clearInterval(progressTimer);
                if (progressCard) progressCard.classList.add("d-none");
                console.error("Translation generation error:", err);
                showAlert("translate-alert", err.message || "Failed to generate translation.", "danger");
            } finally {
                translateBtn.disabled = false;
                translateBtn.innerHTML = origHtml;
            }
        });
    }

    // Copy to clipboard
    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            const transText = targetTextArea?.value;
            if (transText) {
                navigator.clipboard.writeText(transText).then(() => {
                    showAlert("translate-alert", "Translation copied to clipboard!", "success");
                });
            }
        });
    }

    // Export PDF & TXT Handlers
    setupDownloadButton(exportPdfBtn, "pdf");
    setupDownloadButton(exportTxtBtn, "txt");

    function setupDownloadButton(btn, format) {
        if (!btn) return;
        btn.addEventListener("click", async () => {
            if (!currentTranslationId) {
                showAlert("translate-alert", "Please generate a translation before exporting.", "warning");
                return;
            }

            try {
                const token = (typeof authManager !== "undefined" && authManager && authManager.getToken)
                    ? authManager.getToken()
                    : (typeof getAuthToken === "function" ? getAuthToken() : localStorage.getItem("ainotes_jwt_token"));
                const targetLang = targetLangSelect?.value || "ta";
                const filename = `translation_${currentTranslationId}_${targetLang}.${format}`;
                const exportUrl = apiClient.resolveUrl(`/translations/${currentTranslationId}/export?format=${format}`);
                const resp = await fetch(exportUrl, {
                    headers: { "Authorization": `Bearer ${token}` }
                });

                if (!resp.ok) throw new Error("Export download failed");
                const blob = await resp.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } catch (err) {
                showAlert("translate-alert", `Export failed: ${err.message}`, "danger");
            }
        });
    }

    // Translation History Table
    async function loadTranslationHistory() {
        if (!historyContainer) return;

        try {
            const res = await apiClient.get("/translations/history?per_page=10");
            const history = res.data?.translations || [];

            if (history.length === 0) {
                historyContainer.innerHTML = '<div class="text-muted small text-center py-3">No recent translations recorded.</div>';
                return;
            }

            historyContainer.innerHTML = `
                <table class="table table-sm table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>ID</th>
                            <th>Pair</th>
                            <th>Snippet</th>
                            <th>Date</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${history.map(t => `
                            <tr>
                                <td>#${t.id}</td>
                                <td><span class="badge bg-primary-subtle text-primary border">${(t.source_language || 'en').toUpperCase()} &rarr; ${(t.target_language || 'ta').toUpperCase()}</span></td>
                                <td class="text-truncate" style="max-width: 250px;">${escapeHtml(t.translated_text || '')}</td>
                                <td class="small text-muted">${formatDateTime(t.created_at, null, "N/A")}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary py-0 px-2 rounded-pill btn-view-trans" data-id="${t.id}" title="Load this Translation">
                                        <i class="bi bi-eye"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;

            document.querySelectorAll(".btn-view-trans").forEach(btn => {
                btn.addEventListener("click", () => {
                    const tId = parseInt(btn.dataset.id, 10);
                    const item = history.find(h => h.id === tId);
                    if (item) {
                        currentTranslationId = item.id;
                        if (sourceTextArea) sourceTextArea.value = item.original_text || "";
                        if (targetTextArea) targetTextArea.value = item.translated_text || "";
                        if (sourceLangSelect) sourceLangSelect.value = item.source_language;
                        if (targetLangSelect) targetLangSelect.value = item.target_language;
                        updateCharCount();
                        updateExportButtonsState();
                        showAlert("translate-alert", `Loaded translation #${item.id}`, "info");
                    }
                });
            });

        } catch (err) {
            console.warn("Could not load translation history:", err);
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
});
