/**
 * Navigation and Shell Component Controller.
 * Manages sidebar active states, mobile drawer toggling, user profile details,
 * and authentication guards on protected application views.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Enforce authentication on protected pages
    const isProtectedPage = !window.location.pathname.endsWith("index.html") &&
                            !window.location.pathname.endsWith("login.html") &&
                            !window.location.pathname.endsWith("register.html") &&
                            window.location.pathname !== "/" &&
                            !window.location.pathname.endsWith("/");

    if (isProtectedPage) {
        if (!authManager.isAuthenticated()) {
            const pageName = window.location.pathname.split("/").pop() || "dashboard.html";
            window.location.href = `login.html?redirect=${encodeURIComponent(pageName)}`;
            return;
        }
    }

    // 2. Populate user profile details into sidebar / topbar
    const user = authManager.getUser();
    if (user) {
        const userNameEls = document.querySelectorAll(".current-user-name");
        const userEmailEls = document.querySelectorAll(".current-user-email");
        const userAvatarEls = document.querySelectorAll(".current-user-avatar");

        const displayName = user.full_name || user.email.split("@")[0];
        const initial = displayName.charAt(0).toUpperCase();

        userNameEls.forEach(el => el.textContent = displayName);
        userEmailEls.forEach(el => el.textContent = user.email);
        userAvatarEls.forEach(el => el.textContent = initial);
    }

    // 3. Highlight active nav link based on current path
    const currentPath = window.location.pathname.split("/").pop() || "index.html";
    const navLinks = document.querySelectorAll(".sidebar-nav .nav-link, .navbar-nav .nav-link");
    navLinks.forEach(link => {
        const href = link.getAttribute("href");
        if (href && (href === currentPath || (currentPath === "" && href === "dashboard.html"))) {
            link.classList.add("active");
        } else if (href && href !== currentPath) {
            link.classList.remove("active");
        }
    });

    // 4. Mobile sidebar drawer toggling
    const sidebarToggleBtn = document.getElementById("sidebarToggle");
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.querySelector(".sidebar-backdrop");

    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("show");
            if (overlay) overlay.classList.toggle("show");
        });
    }

    if (overlay) {
        overlay.addEventListener("click", () => {
            if (sidebar) sidebar.classList.remove("show");
            overlay.classList.remove("show");
        });
    }

    // 5. Global Sign-out trigger
    document.querySelectorAll(".btn-logout").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            if (confirm("Are you sure you want to sign out?")) {
                authManager.logout();
            }
        });
    });
});

