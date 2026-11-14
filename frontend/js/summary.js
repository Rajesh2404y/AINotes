/**
 * AI Summarizer Interface Controller.
 * Handles document selection, multi-tier mode selection, summary generation API call,
 * rendering summary & key takeaways & definitions & keywords, PDF/TXT export, and clipboard copy.
 */

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Verify Authentication
    if (typeof checkAuth === "function" && !checkAuth()) {
        return;
    }

    const documentSelect = document.getElementById("document-select");
    const docMetaBadge = document.getElementById("doc-meta-badge");
    const originalTextArea = document.getElementById("original-source-text");
    const summaryTypeBtns = document.querySelectorAll(".btn-summary-type");
    const generateBtn = document.getElementById("btn-generate-summary");
    const summaryOutputArea = document.getElementById("summary-output-container");

    let currentMode = "medium";
    let activeDocId = sessionStorage.getItem("active_document_id") || null;
    let documentsMap = {};

    // 2. Mode Selector Handling
    summaryTypeBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            summaryTypeBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentMode = btn.dataset.mode;
        });
    });

    // 3. Load User Documents for Selector
    await loadUserDocuments();

    async function loadUserDocuments() {
        try {
            const res = await apiClient.get("/documents?limit=50");
            const docs = res.documents || res.data?.documents || res.data || [];
            if (documentSelect) {
                documentSelect.innerHTML = '<option value="">-- Choose a Processed Document --</option>';
                docs.forEach(doc => {
                    documentsMap[doc.id] = doc;
                    const opt = document.createElement("option");
                    opt.value = doc.id;
                    opt.textContent = `${doc.title || doc.original_filename} (${doc.total_words || 0} words)`;
                    documentSelect.appendChild(opt);
                });

                // Auto-select active doc from session if present
                if (activeDocId && documentsMap[activeDocId]) {
                    documentSelect.value = activeDocId;
                    onDocumentSelected(activeDocId);
                } else if (sessionStorage.getItem("active_document_text") && originalTextArea) {
                    originalTextArea.value = sessionStorage.getItem("active_document_text");
                    if (docMetaBadge) {
                        docMetaBadge.textContent = sessionStorage.getItem("active_document_title") || "Active Note";
                        docMetaBadge.className = "badge bg-primary-subtle text-primary border";
                    }
                }
            }
        } catch (err) {
            console.warn("Could not load user documents list:", err);
        }
    }

    // Document Selector change event
    if (documentSelect) {
        documentSelect.addEventListener("change", (e) => {
            const docId = e.target.value;
            if (docId) {
                activeDocId = docId;
                sessionStorage.setItem("active_document_id", docId);
                onDocumentSelected(docId);
            } else {
                activeDocId = null;
                if (docMetaBadge) {
                    docMetaBadge.textContent = "No Document Selected";
                    docMetaBadge.className = "badge bg-body-tertiary text-muted border";
                }
            }
        });
    }

    async function onDocumentSelected(docId) {
        try {
            const res = await apiClient.get(`/documents/${docId}`);
            const doc = res.document || res.data?.document || res.data;
            if (doc && originalTextArea) {
                originalTextArea.value = doc.cleaned_text || doc.extracted_text || "";
                if (docMetaBadge) {
                    docMetaBadge.textContent = `${doc.title || doc.original_filename} (${doc.total_words || 0} words)`;
                    docMetaBadge.className = "badge bg-success-subtle text-success border border-success-subtle";
                }
                sessionStorage.setItem("active_document_id", doc.id);
                sessionStorage.setItem("active_document_title", doc.title || doc.original_filename);
                sessionStorage.setItem("active_document_text", originalTextArea.value);
            }
        } catch (err) {
            console.error("Failed to load document text:", err);
            showAlert("summary-alert", "Failed to load document details.", "danger");
        }
    }

    // 4. Generate Summary Action
    if (generateBtn) {
        generateBtn.addEventListener("click", async () => {
            const rawText = originalTextArea?.value.trim() || "";

            if (!rawText) {
                showAlert("summary-alert", "Please select a document or paste text before generating a summary.", "warning");
                return;
            }

            if (rawText.length < 40) {
                showAlert("summary-alert", "Source content is too brief to generate a meaningful summary.", "warning");
                return;
            }

            // If no document selected or user edited text directly, ingest as direct text document
            let targetDocId = activeDocId;
            const originalButtonHtml = generateBtn.innerHTML;
            generateBtn.disabled = true;

            try {
                if (!targetDocId) {
                    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Preparing Document...';
                    const title = "Pasted Study Note (" + formatDisplayDate(new Date()) + ")";
                    const docRes = await apiClient.post("/documents/text", {
                        title: title,
                        content: rawText
                    });
                    const newDoc = docRes.document;
                    targetDocId = newDoc.id;
                    activeDocId = targetDocId;
                    sessionStorage.setItem("active_document_id", targetDocId);
                    await loadUserDocuments();
                }

                generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Generating AI Summary...';

                // Call Backend Summarization API
                const summaryRes = await apiClient.post("/summaries/generate", {
                    document_id: parseInt(targetDocId, 10),
                    summary_type: currentMode
                });

                const summaryData = summaryRes.data || summaryRes;
                renderSummary(summaryData);
                showAlert("summary-alert", "AI Summary synthesized successfully!", "success");

            } catch (err) {
                console.error("Summary Generation Error:", err);
                showAlert("summary-alert", err.message || "Failed to generate summary.", "danger");
            } finally {
                generateBtn.disabled = false;
                generateBtn.innerHTML = originalButtonHtml;
            }
        });
    }

    // 5. Render Generated Summary Results
    function renderSummary(summary) {
        if (!summaryOutputArea) return;

        const meta = summary.metadata || {};
        const quality = meta.quality || {};
        const modelName = meta.model_name || summary.model_name || "DistilBART-CNN";
        const duration = meta.processing_duration || summary.processing_duration || 0;
        const compression = quality.compression_ratio !== undefined ? `${quality.compression_ratio}%` : "50%";
        const qualityGrade = quality.quality_grade || "HIGH";

        const takeaways = summary.key_takeaways || [];
        const definitions = summary.definitions || [];
        const keywords = summary.keywords || [];

        let takeawaysHtml = "";
        if (takeaways.length > 0) {
            takeawaysHtml = `
                <div class="mb-4">
                    <h6 class="fw-bold mb-2"><i class="bi bi-check2-circle text-primary me-1"></i> Key Takeaways</h6>
                    <ul class="list-unstyled mb-0">
                        ${takeaways.map(pt => `
                            <li class="mb-2 d-flex align-items-start gap-2">
                                <i class="bi bi-dot text-primary fs-4 mt-n2"></i>
                                <span>${escapeHtml(pt)}</span>
                            </li>
                        `).join("")}
                    </ul>
                </div>
            `;
        }

        let definitionsHtml = "";
        if (definitions.length > 0) {
            definitionsHtml = `
                <div class="mb-4">
                    <h6 class="fw-bold mb-2"><i class="bi bi-book text-primary me-1"></i> Important Definitions</h6>
                    <div class="list-group list-group-flush border rounded-3 overflow-hidden">
                        ${definitions.map(d => {
                            const term = typeof d === "object" ? d.term : "";
                            const defn = typeof d === "object" ? d.definition : d;
                            return `
                                <div class="list-group-item bg-body-tertiary">
                                    <strong class="text-primary">${escapeHtml(term)}</strong>
                                    <p class="mb-0 text-secondary small">${escapeHtml(defn)}</p>
                                </div>
                            `;
                        }).join("")}
                    </div>
                </div>
            `;
        }

        let keywordsHtml = "";
        if (keywords.length > 0) {
            keywordsHtml = `
                <div class="mb-4">
                    <h6 class="fw-bold mb-2"><i class="bi bi-tags text-primary me-1"></i> Topic Keywords</h6>
                    <div class="d-flex flex-wrap gap-2">
                        ${keywords.map(kw => `<span class="badge bg-body-secondary text-body border">#${escapeHtml(kw)}</span>`).join("")}
                    </div>
                </div>
            `;
        }

        summaryOutputArea.innerHTML = `
            <div class="card border-0 shadow-sm p-4">
                <!-- Meta Status Bar -->
                <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2 border-bottom pb-3">
                    <div class="d-flex align-items-center gap-2 flex-wrap">
                        <span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-2 rounded-pill">
                            <i class="bi bi-stars me-1"></i> ${(summary.summary_type || currentMode).toUpperCase()}
                        </span>
                        <span class="badge bg-primary-subtle text-primary border px-2 py-1 small">
                            ${modelName}
                        </span>
                        <span class="text-muted small">
                            Duration: ${duration.toFixed(2)}s | Compression: ${compression}
                        </span>
                    </div>
                    <div class="d-flex gap-2">
                        <button id="btn-copy-summary" class="btn btn-outline-secondary btn-sm rounded-pill">
                            <i class="bi bi-clipboard me-1"></i> Copy
                        </button>
                        <a id="btn-export-pdf" href="${apiClient.resolveUrl(`/summaries/${summary.id}/export?format=pdf`)}" class="btn btn-outline-danger btn-sm rounded-pill" target="_blank">
                            <i class="bi bi-file-earmark-pdf me-1"></i> PDF
                        </a>
                        <a id="btn-export-txt" href="${apiClient.resolveUrl(`/summaries/${summary.id}/export?format=txt`)}" class="btn btn-outline-secondary btn-sm rounded-pill" target="_blank">
                            <i class="bi bi-file-earmark-text me-1"></i> TXT
                        </a>
                    </div>
                </div>

                <!-- Summary Body Text -->
                <div id="summary-content-text" class="summary-body mb-4">
                    <h5 class="fw-bold text-primary mb-2">Executive Summary</h5>
                    <div class="text-secondary leading-relaxed mb-4" style="line-height: 1.7;">
                        ${escapeHtml(summary.summary_text).replace(/\n\n/g, "<br><br>")}
                    </div>

                    ${takeawaysHtml}
                    ${definitionsHtml}
                    ${keywordsHtml}
                </div>

                <!-- Handoff to Next Phases -->
                <div class="d-flex gap-2 pt-3 border-top flex-wrap">
                    <button id="btn-handoff-quiz" class="btn btn-primary btn-sm rounded-pill px-3">
                        <i class="bi bi-patch-question me-1"></i> Generate Practice Quiz
                    </button>
                    <button id="btn-handoff-translate" class="btn btn-outline-primary btn-sm rounded-pill px-3">
                        <i class="bi bi-translate me-1"></i> Translate this Summary
                    </button>
                </div>
            </div>
        `;

        // Wire Export & Handoff Buttons
        document.getElementById("btn-copy-summary")?.addEventListener("click", () => {
            const summaryText = summary.summary_text;
            navigator.clipboard.writeText(summaryText).then(() => {
                showAlert("summary-alert", "Summary copied to clipboard!", "success");
            });
        });

        document.getElementById("btn-handoff-quiz")?.addEventListener("click", () => {
            sessionStorage.setItem("active_summary_id", summary.id);
            sessionStorage.setItem("active_summary_text", summary.summary_text);
            window.location.href = "quiz-config.html";
        });

        document.getElementById("btn-handoff-translate")?.addEventListener("click", () => {
            sessionStorage.setItem("active_summary_id", summary.id);
            sessionStorage.setItem("translate_handoff_text", summary.summary_text);
            window.location.href = "translate.html";
        });

        // Add authorization headers for direct export links via fetch-and-download
        setupExportLink("btn-export-pdf", `/summaries/${summary.id}/export?format=pdf`, `summary_${summary.id}.pdf`);
        setupExportLink("btn-export-txt", `/summaries/${summary.id}/export?format=txt`, `summary_${summary.id}.txt`);
    }

    function setupExportLink(elementId, apiPath, filename) {
        const link = document.getElementById(elementId);
        if (!link) return;
        link.addEventListener("click", async (e) => {
            e.preventDefault();
            try {
                const token = (typeof authManager !== "undefined" && authManager && authManager.getToken)
                    ? authManager.getToken()
                    : (typeof getAuthToken === "function" ? getAuthToken() : localStorage.getItem("ainotes_jwt_token"));
                const exportUrl = apiClient.resolveUrl(apiPath);
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
                showAlert("summary-alert", "Export failed: " + err.message, "danger");
            }
        });
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
