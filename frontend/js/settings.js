/**
 * Settings and Application Preferences Controller.
 * Manages theme preference configuration, default AI generation options,
 * cache cleanup, and local data export.
 */

document.addEventListener("DOMContentLoaded", () => {
    if (!authManager.isAuthenticated()) return;

    loadSavedSettings();
    bindSettingsEvents();
});

function loadSavedSettings() {
    // 1. Theme Choice
    const currentTheme = localStorage.getItem(CONFIG.STORAGE_KEYS.THEME) || "light";
    const radio = document.querySelector(`input[name="themeChoice"][value="${currentTheme}"]`);
    if (radio) radio.checked = true;

    // 2. Study Preferences
    const rawSettings = localStorage.getItem(CONFIG.STORAGE_KEYS.SETTINGS);
    const settings = rawSettings ? JSON.parse(rawSettings) : {
        defaultSummaryMode: "medium",
        defaultDifficulty: "Medium",
        defaultLanguage: "hi",
        timezone: "Asia/Kolkata",
        emailNotifications: true,
        autoSaveNotes: true
    };

    const selSummary = document.getElementById("prefDefaultSummary");
    const selDifficulty = document.getElementById("prefDefaultDifficulty");
    const selLang = document.getElementById("prefDefaultLanguage");
    const selTimezone = document.getElementById("prefTimezone");
    const chkEmail = document.getElementById("prefEmailNotif");
    const chkAutoSave = document.getElementById("prefAutoSave");

    if (selSummary) selSummary.value = settings.defaultSummaryMode || "medium";
    if (selDifficulty) selDifficulty.value = settings.defaultDifficulty || "Medium";
    if (selTimezone) selTimezone.value = settings.timezone || "Asia/Kolkata";

    if (selLang) {
        selLang.innerHTML = CONFIG.SUPPORTED_LANGUAGES.map(lang => 
            `<option value="${lang.code}" ${lang.code === (settings.defaultLanguage || 'hi') ? 'selected' : ''}>${lang.name}</option>`
        ).join("");
    }

    if (chkEmail) chkEmail.checked = settings.emailNotifications ?? true;
    if (chkAutoSave) chkAutoSave.checked = settings.autoSaveNotes ?? true;
}

function bindSettingsEvents() {
    // Theme Radios
    document.querySelectorAll('input[name="themeChoice"]').forEach(radio => {
        radio.addEventListener("change", (e) => {
            if (e.target.checked) {
                themeManager.applyTheme(e.target.value);
                showAlert("settings-alert", `Theme switched to ${e.target.value.toUpperCase()} mode.`, "success");
            }
        });
    });

    // Preferences Form Save
    const prefForm = document.getElementById("study-preferences-form");
    if (prefForm) {
        prefForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const settings = {
                defaultSummaryMode: document.getElementById("prefDefaultSummary")?.value,
                defaultDifficulty: document.getElementById("prefDefaultDifficulty")?.value,
                defaultLanguage: document.getElementById("prefDefaultLanguage")?.value,
                timezone: document.getElementById("prefTimezone")?.value || "Asia/Kolkata",
                emailNotifications: document.getElementById("prefEmailNotif")?.checked,
                autoSaveNotes: document.getElementById("prefAutoSave")?.checked
            };

            localStorage.setItem(CONFIG.STORAGE_KEYS.SETTINGS, JSON.stringify(settings));
            showAlert("settings-alert", "Preferences saved successfully!", "success");
        });
    }

    // Cache clearing
    document.getElementById("btn-clear-cache")?.addEventListener("click", () => {
        if (confirm("Clear local study cache and drafts? Your saved database notes will remain intact.")) {
            sessionStorage.clear();
            localStorage.removeItem("translate_handoff_text");
            showAlert("settings-alert", "Temporary study cache cleared.", "info");
        }
    });

    // Export Data
    document.getElementById("btn-export-data")?.addEventListener("click", () => {
        const user = authManager.getUser();
        const exportObj = {
            user,
            exportedAt: new Date().toISOString(),
            settings: JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.SETTINGS) || "{}")
        };
        const blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `AINotes_UserData_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
    });
}

