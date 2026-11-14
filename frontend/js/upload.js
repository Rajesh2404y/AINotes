/**
 * Document Ingestion & Extraction Frontend Controller.
 * Connects drag-and-drop & file picker to POST /api/documents/upload and POST /api/documents/extract,
 * handles direct text paste ingestion via POST /api/documents/text,
 * visualizes processing statistics (pages, words, characters, OCR, quality),
 * and enables text copying, document deletion, and transition to Summarization.
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const filePreview = document.getElementById("file-preview");
    const fileNameEl = document.getElementById("preview-filename");
    const fileSizeEl = document.getElementById("preview-filesize");
    const fileIconEl = document.getElementById("preview-icon");
    const removeFileBtn = document.getElementById("btn-remove-file");
    const uploadForm = document.getElementById("upload-form");
    const submitBtn = document.getElementById("btn-submit-upload");
    const progressWrapper = document.getElementById("upload-progress-wrapper");
    const progressBar = document.getElementById("upload-progress-bar");
    const progressLabel = document.getElementById("upload-progress-label");
    const progressPercent = document.getElementById("upload-progress-percent");

    // Direct Paste Elements
    const pasteArea = document.getElementById("paste-content");
    const wordCountEl = document.getElementById("paste-word-count");
    const charCountEl = document.getElementById("paste-char-count");
    const pasteForm = document.getElementById("paste-form");
    const submitPasteBtn = document.getElementById("btn-submit-paste");

    // Results Elements
    const resultsContainer = document.getElementById("extraction-results-container");
    const resFormat = document.getElementById("res-format");
    const resPages = document.getElementById("res-pages");
    const resWords = document.getElementById("res-words");
    const resQuality = document.getElementById("res-quality");
    const resFilename = document.getElementById("res-filename");
    const resCharacters = document.getElementById("res-characters");
    const resOcrBadge = document.getElementById("res-ocr-badge");
    const resWarningsBox = document.getElementById("res-warnings-box");
    const resWarningsList = document.getElementById("res-warnings-list");
    const resExtractedPreview = document.getElementById("res-extracted-preview");
    const copyExtractedBtn = document.getElementById("btn-copy-extracted");
    const deleteExtractedBtn = document.getElementById("btn-delete-extracted");
    const uploadAnotherBtn = document.getElementById("btn-upload-another");

    let selectedFile = null;
    let activeDocument = null;

    const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"];
    const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

    // --- Drag and Drop Handlers ---
    if (dropZone && fileInput) {
        dropZone.addEventListener("click", () => fileInput.click());

        ["dragenter", "dragover"].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add("drag-over");
            });
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove("drag-over");
            });
        });

        dropZone.addEventListener("drop", (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelection(files[0]);
            }
        });

        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });
    }

    function handleFileSelection(file) {
        const fileName = file.name.toLowerCase();
        const isValidExtension = ALLOWED_EXTENSIONS.some(ext => fileName.endsWith(ext));

        if (!isValidExtension) {
            showAlert("upload-alert", `Invalid file format. Supported formats: ${ALLOWED_EXTENSIONS.join(", ")}`, "danger");
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            showAlert("upload-alert", `File size exceeds the 20 MB limit. Your file is ${formatBytes(file.size)}.`, "danger");
            return;
        }

        if (file.size === 0) {
            showAlert("upload-alert", "The selected file is empty (0 bytes).", "danger");
            return;
        }

        selectedFile = file;

        // Update preview UI
        if (fileNameEl) fileNameEl.textContent = file.name;
        if (fileSizeEl) fileSizeEl.textContent = formatBytes(file.size);

        if (fileIconEl) {
            if (fileName.endsWith(".pdf")) {
                fileIconEl.className = "bi bi-file-earmark-pdf-fill text-danger fs-1";
            } else if (fileName.endsWith(".docx")) {
                fileIconEl.className = "bi bi-file-earmark-word-fill text-primary fs-1";
            } else if (fileName.endsWith(".png") || fileName.endsWith(".jpg") || fileName.endsWith(".jpeg")) {
                fileIconEl.className = "bi bi-file-earmark-image-fill text-info fs-1";
            } else {
                fileIconEl.className = "bi bi-file-earmark-text-fill text-secondary fs-1";
            }
        }

        if (dropZone) dropZone.classList.add("d-none");
        if (filePreview) filePreview.classList.remove("d-none");
        hideAlert("upload-alert");
    }

    if (removeFileBtn) {
        removeFileBtn.addEventListener("click", () => {
            resetFileSelection();
        });
    }

    function resetFileSelection() {
        selectedFile = null;
        if (fileInput) fileInput.value = "";
        if (dropZone) dropZone.classList.remove("d-none");
        if (filePreview) filePreview.classList.add("d-none");
        if (progressWrapper) progressWrapper.classList.add("d-none");
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-cloud-arrow-up-fill me-1"></i> Upload & Extract Text';
        }
    }

    // --- Direct Paste Word and Char Counter ---
    if (pasteArea) {
        pasteArea.addEventListener("input", () => {
            const text = pasteArea.value.trim();
            const words = text ? text.split(/\s+/).length : 0;
            const chars = text.length;

            if (wordCountEl) wordCountEl.textContent = `${words} words`;
            if (charCountEl) charCountEl.textContent = `${chars} characters`;
        });
    }

    // --- File Upload & Extraction Submit Handler ---
    if (uploadForm) {
        uploadForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!selectedFile) {
                showAlert("upload-alert", "Please select a file to upload.", "warning");
                return;
            }

            if (!authManager.isAuthenticated()) {
                showAlert("upload-alert", "You must be signed in to upload documents.", "danger");
                return;
            }

            // Step 1: Uploading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Uploading...';
            if (progressWrapper) progressWrapper.classList.remove("d-none");
            updateProgress(35, "Uploading file securely to server...");

            const formData = new FormData();
            formData.append("file", selectedFile);

            try {
                // Upload file
                const token = authManager.getToken();
                const uploadUrl = apiClient.resolveUrl("/documents/upload");
                const uploadResponse = await fetch(uploadUrl, {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`
                    },
                    body: formData
                });

                const uploadData = await uploadResponse.json();
                if (!uploadResponse.ok) {
                    throw new Error(uploadData.message || "Failed to upload document.");
                }

                const docId = uploadData.document.id;
                updateProgress(70, "Extracting text and running OCR analysis...");
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Extracting Text...';

                // Step 2: Trigger Extraction Pipeline
                const extractData = await apiClient.post("/documents/extract", {
                    document_id: docId
                });

                updateProgress(100, "Processing complete!");

                setTimeout(() => {
                    displayExtractionResults(extractData.document, extractData.warnings);
                }, 500);

            } catch (err) {
                console.error("Upload/Extraction Error:", err);
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i> Retry Upload & Extract';
                if (progressWrapper) progressWrapper.classList.add("d-none");
                showAlert("upload-alert", err.message || "Failed to process document.", "danger");
            }
        });
    }

    // --- Direct Text Paste Ingestion Submit Handler ---
    if (pasteForm) {
        pasteForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const title = document.getElementById("paste-title")?.value.trim() || "Pasted Notes";
            const content = pasteArea?.value.trim() || "";

            if (!content) {
                showAlert("paste-alert", "Please paste educational study text before submitting.", "warning");
                return;
            }

            if (content.length < 50) {
                showAlert("paste-alert", "Content is too brief for effective AI summarization (minimum 50 characters).", "warning");
                return;
            }

            submitPasteBtn.disabled = true;
            submitPasteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Ingesting Text...';

            try {
                const res = await apiClient.post("/documents/text", {
                    title,
                    content
                });

                displayExtractionResults(res.document, res.warnings);
                showAlert("paste-alert", "Text ingested successfully!", "success");
            } catch (err) {
                submitPasteBtn.disabled = false;
                submitPasteBtn.innerHTML = '<i class="bi bi-lightning-charge-fill me-1"></i> Ingest Text & Prepare';
                showAlert("paste-alert", err.message || "Failed to ingest text notes.", "danger");
            }
        });
    }

    // --- Render Extraction Results ---
    function displayExtractionResults(doc, warnings = []) {
        activeDocument = doc;

        // Hide upload forms / reset submit buttons
        const uploadCard = document.getElementById("upload-card");
        if (uploadCard) uploadCard.classList.add("d-none");
        if (pasteForm) pasteForm.closest(".card")?.classList.add("d-none");

        // Populate metrics
        if (resFormat) resFormat.textContent = doc.file_type || "UNKNOWN";
        if (resPages) resPages.textContent = doc.total_pages || 1;
        if (resWords) resWords.textContent = doc.total_words || 0;
        if (resFilename) resFilename.textContent = doc.original_filename || "Document";
        if (resCharacters) resCharacters.textContent = doc.total_characters || 0;

        if (resQuality) {
            const q = (doc.extraction_quality || "HIGH").toUpperCase();
            resQuality.textContent = q;
            if (q === "HIGH") {
                resQuality.className = "badge bg-success-subtle text-success fs-6 mt-1";
            } else if (q === "MEDIUM") {
                resQuality.className = "badge bg-warning-subtle text-warning fs-6 mt-1";
            } else {
                resQuality.className = "badge bg-danger-subtle text-danger fs-6 mt-1";
            }
        }

        if (resOcrBadge) {
            if (doc.ocr_used) {
                const conf = doc.extraction_metadata?.ocr_confidence;
                resOcrBadge.className = "badge bg-info-subtle text-info border";
                resOcrBadge.textContent = conf ? `Yes (${Math.round(conf)}% conf)` : "Yes";
            } else {
                resOcrBadge.className = "badge bg-secondary-subtle text-secondary border";
                resOcrBadge.textContent = "No (Direct Text)";
            }
        }

        // Warnings list
        if (warnings && warnings.length > 0) {
            if (resWarningsBox) resWarningsBox.classList.remove("d-none");
            if (resWarningsList) {
                resWarningsList.innerHTML = warnings.map(w => `<li>${escapeHtml(w)}</li>`).join("");
            }
        } else if (resWarningsBox) {
            resWarningsBox.classList.add("d-none");
        }

        // Extracted text preview
        if (resExtractedPreview) {
            resExtractedPreview.value = doc.cleaned_text || doc.extracted_text || "No text available.";
        }

        // Save active document state for the Summarizer
        sessionStorage.setItem("active_document_id", doc.id);
        sessionStorage.setItem("active_document_title", doc.original_filename);
        sessionStorage.setItem("active_document_text", doc.cleaned_text || doc.extracted_text || "");

        // Show Results container
        if (resultsContainer) {
            resultsContainer.classList.remove("d-none");
            resultsContainer.scrollIntoView({ behavior: "smooth" });
        }
    }

    // --- Copy Extracted Text Handler ---
    if (copyExtractedBtn) {
        copyExtractedBtn.addEventListener("click", () => {
            const text = resExtractedPreview?.value || "";
            if (text) {
                navigator.clipboard.writeText(text).then(() => {
                    const origHtml = copyExtractedBtn.innerHTML;
                    copyExtractedBtn.innerHTML = '<i class="bi bi-check2 text-success me-1"></i> Copied!';
                    setTimeout(() => {
                        copyExtractedBtn.innerHTML = origHtml;
                    }, 2000);
                });
            }
        });
    }

    // --- Delete Document Handler ---
    if (deleteExtractedBtn) {
        deleteExtractedBtn.addEventListener("click", async () => {
            if (!activeDocument || !activeDocument.id) return;
            if (confirm(`Are you sure you want to delete "${activeDocument.original_filename}"? This action cannot be undone.`)) {
                try {
                    await apiClient.delete(`/documents/${activeDocument.id}`);
                    alert("Document deleted successfully.");
                    window.location.reload();
                } catch (err) {
                    alert(`Failed to delete document: ${err.message}`);
                }
            }
        });
    }

    // --- Process Another Document Handler ---
    if (uploadAnotherBtn) {
        uploadAnotherBtn.addEventListener("click", () => {
            window.location.reload();
        });
    }

    // Helpers
    function updateProgress(percent, label) {
        if (progressBar) progressBar.style.width = `${percent}%`;
        if (progressPercent) progressPercent.textContent = `${percent}%`;
        if (progressLabel) progressLabel.textContent = label;
    }

    function formatBytes(bytes) {
        if (bytes === 0) return "0 Bytes";
        const k = 1024;
        const sizes = ["Bytes", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    }

    function hideAlert(containerId) {
        const container = document.getElementById(containerId);
        if (container) container.innerHTML = "";
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/[&<>'"]/g, tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag));
    }
});
