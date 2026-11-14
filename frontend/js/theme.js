/**
 * Theme Management Script.
 * Supports Light, Dark, and Auto mode with persistent local storage.
 */

const themeManager = {
    init() {
        const savedTheme = localStorage.getItem(CONFIG.STORAGE_KEYS.THEME) || localStorage.getItem("ainotes_theme") || "dark";
        this.applyTheme(savedTheme, true);
        this.bindEvents();
    },

    applyTheme(theme, isInit = false) {
        let activeTheme = theme;
        if (theme === "auto") {
            activeTheme = (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
        }
        const prevTheme = document.documentElement.getAttribute("data-bs-theme");
        document.documentElement.setAttribute("data-bs-theme", activeTheme);
        localStorage.setItem(CONFIG.STORAGE_KEYS.THEME, theme);
        localStorage.setItem("ainotes_theme", activeTheme);

        // Update toggle icons
        const toggleBtns = document.querySelectorAll(".theme-toggle-btn");
        toggleBtns.forEach(btn => {
            const icon = btn.querySelector("i");
            if (icon) {
                if (activeTheme === "dark") {
                    icon.className = "bi bi-moon-stars-fill text-warning";
                } else {
                    icon.className = "bi bi-sun-fill text-warning";
                }
            }
        });

        // Update any radio selects in settings page
        const themeRadio = document.querySelector(`input[name="themeChoice"][value="${theme}"]`);
        if (themeRadio) {
            themeRadio.checked = true;
        }

        // Only dispatch if theme actually changed to prevent cascading chart redraws on init
        if (!isInit || prevTheme !== activeTheme) {
            window.dispatchEvent(new CustomEvent("themeChanged", { detail: { theme: activeTheme } }));
        }
    },

    toggle() {
        const currentTheme = document.documentElement.getAttribute("data-bs-theme") || "light";
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        this.applyTheme(nextTheme);
    },

    bindEvents() {
        document.querySelectorAll(".theme-toggle-btn").forEach(btn => {
            btn.addEventListener("click", () => this.toggle());
        });

        // System preference change listener
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", e => {
            const savedTheme = localStorage.getItem(CONFIG.STORAGE_KEYS.THEME);
            if (savedTheme === "auto") {
                this.applyTheme("auto");
            }
        });
    }
};

// Auto-run immediately to prevent flash of wrong theme
(function() {
    const saved = localStorage.getItem("ainotes_theme_preference") || "light";
    let active = saved;
    if (saved === "auto") {
        active = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.setAttribute("data-bs-theme", active);
})();

document.addEventListener("DOMContentLoaded", () => {
    themeManager.init();
});

