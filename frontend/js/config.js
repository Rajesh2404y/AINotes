/**
 * Global Frontend Application Configuration.
 * Configures the backend REST API base URL, storage keys, and system constants.
 */

// 1. Resolve environment-specific API Base URL dynamically
const getResolvedApiBaseUrl = () => {
    // If pre-configured or injected via window
    if (typeof window !== "undefined" && window.CUSTOM_API_BASE_URL) {
        return window.CUSTOM_API_BASE_URL;
    }

    if (typeof window !== "undefined" && window.location) {
        const protocol = window.location.protocol;
        const hostname = window.location.hostname;
        const port = window.location.port;

        // If opened directly from file system (file://)
        if (protocol === "file:") {
            return "http://127.0.0.1:5000/api";
        }

        // If served from Flask backend on port 5000 or custom port
        if (port === "5000" || port === "5001") {
            return `${window.location.origin}/api`;
        }

        // If local development on another port (e.g. Live Server 5500, Vite 5173, etc.)
        if (hostname === "localhost" || hostname === "127.0.0.1") {
            return "http://127.0.0.1:5000/api";
        }

        // Production or reverse-proxied origin (e.g. /api)
        return `${window.location.origin}/api`;
    }

    return "http://127.0.0.1:5000/api";
};

// 2. Define global constant API_BASE_URL
const API_BASE_URL = getResolvedApiBaseUrl();

// 3. Centralized CONFIG Object
const CONFIG = {
    API_BASE_URL: API_BASE_URL,
    STORAGE_KEYS: {
        AUTH_TOKEN: "ainotes_jwt_token",
        USER_DATA: "ainotes_user_info",
        THEME: "ainotes_theme_preference",
        SETTINGS: "ainotes_user_settings"
    },
    APP_NAME: "AI Notes Summarizer",
    VERSION: "1.0.0",
    SUPPORTED_LANGUAGES: [
        { code: "en", name: "English" },
        { code: "es", name: "Spanish (Español)" },
        { code: "fr", name: "French (Français)" },
        { code: "de", name: "German (Deutsch)" },
        { code: "hi", name: "Hindi (हिन्दी)" },
        { code: "ta", name: "Tamil (தமிழ்)" },
        { code: "te", name: "Telugu (తెలుగు)" },
        { code: "ml", name: "Malayalam (മലയാളം)" },
        { code: "kn", name: "Kannada (ಕನ್ನಡ)" },
        { code: "zh", name: "Mandarin Chinese (中文)" },
        { code: "ar", name: "Arabic (العربية)" }
    ],
    SUMMARY_TYPES: {
        SHORT: { key: "short", name: "Short & Crisp", targetReduction: "75%" },
        MEDIUM: { key: "medium", name: "Standard Summary", targetReduction: "50%" },
        DETAILED: { key: "detailed", name: "Comprehensive Study Guide", targetReduction: "25%" }
    },
    QUIZ_TYPES: [
        { id: "mcq", label: "Multiple Choice Questions", icon: "bi-check2-circle" },
        { id: "true_false", label: "True / False", icon: "bi-toggle-on" },
        { id: "one_word", label: "One-Word / Short Answer", icon: "bi-chat-left-dots" },
        { id: "fill_blank", label: "Fill in the Blanks", icon: "bi-input-cursor-text" }
    ],
    DIFFICULTIES: ["Easy", "Medium", "Hard"],
    QUESTION_COUNTS: [5, 10, 15, 20],
    DEFAULT_TIMEZONE: "Asia/Kolkata"
};

// 4. Timezone & Unambiguous Date Formatting Utilities
const DEFAULT_TIMEZONE = "Asia/Kolkata";
const TIMEZONE_ABBREVIATIONS = {
    "Asia/Kolkata": "IST",
    "Asia/Calcutta": "IST",
    "UTC": "UTC",
    "GMT": "GMT",
    "Europe/London": "BST",
    "America/New_York": "EST",
    "America/Los_Angeles": "PST",
    "America/Chicago": "CST",
    "Asia/Singapore": "SGT",
    "Asia/Tokyo": "JST",
    "Asia/Dubai": "GST",
    "Australia/Sydney": "AEST"
};

const ALREADY_FORMATTED_DATE_RE = /^\d{1,2}\s+[A-Za-z]{3}\s+\d{4},\s+\d{2}:\d{2}:\d{2}\s+(?:AM|PM)\s+[A-Z0-9+-]+$/;

function getUserTimezone() {
    try {
        const rawSettings = localStorage.getItem(CONFIG?.STORAGE_KEYS?.SETTINGS || "ainotes_user_settings");
        if (rawSettings) {
            const settings = JSON.parse(rawSettings);
            if (settings && settings.timezone) {
                return settings.timezone;
            }
        }
    } catch (e) {
        // Safe fallback
    }
    return CONFIG.DEFAULT_TIMEZONE || "Asia/Kolkata";
}

function parseUtcDate(input) {
    if (!input) return null;
    if (input instanceof Date) {
        return isNaN(input.getTime()) ? null : input;
    }
    if (typeof input === "number") {
        const d = new Date(input);
        return isNaN(d.getTime()) ? null : d;
    }
    if (typeof input !== "string") return null;

    let str = input.trim();
    if (!str) return null;

    // If naive ISO format from DB without timezone offset (e.g. 2026-11-12T05:06:39 or 2026-11-12 05:06:39)
    if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/.test(str) && !str.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(str)) {
        str = str.replace(" ", "T") + "Z";
    }

    const d = new Date(str);
    return isNaN(d.getTime()) ? null : d;
}

function formatDateTime(input, timeZone = null, fallback = "--") {
    if (!input) return fallback;
    const targetTz = timeZone || getUserTimezone();

    // Check if string is already formatted (prevent double conversion)
    if (typeof input === "string") {
        const trimmed = input.trim();
        if (ALREADY_FORMATTED_DATE_RE.test(trimmed)) {
            return trimmed;
        }
    }

    const date = parseUtcDate(input);
    if (!date) return fallback;

    try {
        const formatter = new Intl.DateTimeFormat("en-US", {
            timeZone: targetTz,
            year: "numeric",
            month: "short",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: true
        });
        const parts = Object.fromEntries(formatter.formatToParts(date).map(p => [p.type, p.value]));
        const tzAbbr = TIMEZONE_ABBREVIATIONS[targetTz] || parts.timeZoneName || targetTz;
        return `${parts.day} ${parts.month} ${parts.year}, ${parts.hour}:${parts.minute}:${parts.second} ${parts.dayPeriod.toUpperCase()} ${tzAbbr}`;
    } catch (e) {
        console.warn("Date formatting error:", e);
        return fallback;
    }
}

function formatDisplayDate(input, timeZone = null, fallback = "--") {
    if (!input) return fallback;
    const targetTz = timeZone || getUserTimezone();
    const date = parseUtcDate(input);
    if (!date) return fallback;

    try {
        const formatter = new Intl.DateTimeFormat("en-US", {
            timeZone: targetTz,
            year: "numeric",
            month: "short",
            day: "2-digit"
        });
        const parts = Object.fromEntries(formatter.formatToParts(date).map(p => [p.type, p.value]));
        return `${parts.day} ${parts.month} ${parts.year}`;
    } catch (e) {
        return fallback;
    }
}

function formatTimeAgo(isoString) {
    if (!isoString) return "Recently";
    try {
        const date = parseUtcDate(isoString);
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
        return formatDisplayDate(date);
    } catch {
        return "Recently";
    }
}

const DateUtils = {
    DEFAULT_TIMEZONE,
    TIMEZONE_ABBREVIATIONS,
    getUserTimezone,
    parseUtcDate,
    formatDateTime,
    formatDisplayDate,
    formatTimeAgo
};

// 5. Attach explicitly to window for global access across scripts
if (typeof window !== "undefined") {
    window.API_BASE_URL = API_BASE_URL;
    window.CONFIG = CONFIG;
    window.DateUtils = DateUtils;
    window.getUserTimezone = getUserTimezone;
    window.parseUtcDate = parseUtcDate;
    window.formatDateTime = formatDateTime;
    window.formatDisplayDate = formatDisplayDate;
    window.formatTimeAgo = formatTimeAgo;
    // Centralized getAuthToken fallback function
    window.getAuthToken = () => {
        return (typeof authManager !== "undefined" && authManager && authManager.getToken)
            ? authManager.getToken()
            : localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    };
}

// 6. CommonJS / Module export support
if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        CONFIG,
        API_BASE_URL,
        DateUtils,
        getUserTimezone,
        parseUtcDate,
        formatDateTime,
        formatDisplayDate,
        formatTimeAgo
    };
}
