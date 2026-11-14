/**
 * User Profile and Security Management Controller.
 * Loads authenticated profile via GET /api/auth/me,
 * submits profile updates via PUT /api/auth/profile,
 * and processes secure password changes via POST /api/auth/change-password.
 */

document.addEventListener("DOMContentLoaded", async () => {
    if (!authManager.isAuthenticated()) return;

    await loadUserProfile();
    bindProfileForms();
});

async function loadUserProfile() {
    try {
        const user = await authManager.fetchProfile();
        if (user) {
            populateProfileFields(user);
        }
    } catch (err) {
        console.error("Error loading user profile:", err);
    }
}

function populateProfileFields(user) {
    const elName = document.getElementById("profile-display-name");
    const elEmail = document.getElementById("profile-display-email");
    const elAvatar = document.getElementById("profile-display-avatar");
    const elJoined = document.getElementById("profile-display-joined");
    const elLastLogin = document.getElementById("profile-display-last-login");
    const elRole = document.getElementById("profile-display-role");

    const inputName = document.getElementById("inputFullName");
    const inputEmail = document.getElementById("inputEmail");

    const displayName = user.full_name || user.email;
    const initial = displayName.charAt(0).toUpperCase();

    if (elName) elName.textContent = displayName;
    if (elEmail) elEmail.textContent = user.email;
    if (elAvatar) elAvatar.textContent = initial;
    if (elRole) elRole.textContent = (user.role || "student").toUpperCase();

    if (elJoined && user.created_at) {
        elJoined.textContent = formatDisplayDate(user.created_at, null, "--");
    }
    if (elLastLogin && user.last_login) {
        elLastLogin.textContent = formatDateTime(user.last_login, null, "First session");
    } else if (elLastLogin) {
        elLastLogin.textContent = "First session";
    }

    if (inputName) inputName.value = user.full_name || "";
    if (inputEmail) inputEmail.value = user.email || "";
}

function bindProfileForms() {
    // 1. Edit Profile Form
    const editForm = document.getElementById("edit-profile-form");
    if (editForm) {
        editForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById("btn-save-profile");
            const fullName = document.getElementById("inputFullName")?.value.trim();
            const email = document.getElementById("inputEmail")?.value.trim();

            if (!fullName || !email) {
                showAlert("profile-alert", "Full name and email are required.", "warning");
                return;
            }

            const origHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Updating...';

            try {
                const res = await apiClient.put("/auth/profile", {
                    full_name: fullName,
                    email: email
                });

                submitBtn.disabled = false;
                submitBtn.innerHTML = origHtml;

                if (res.status === "success" && res.user) {
                    authManager.updateStoredUser(res.user);
                    populateProfileFields(res.user);
                    showAlert("profile-alert", "Profile updated successfully!", "success");
                }
            } catch (err) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origHtml;
                const msg = (err.data && err.data.message) || err.message || "Failed to update profile.";
                showAlert("profile-alert", msg, "danger");
            }
        });
    }

    // 2. Change Password Form
    const pwForm = document.getElementById("change-password-form");
    if (pwForm) {
        pwForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById("btn-change-password");
            const currentPw = document.getElementById("currentPassword")?.value;
            const newPw = document.getElementById("newPassword")?.value;
            const confirmPw = document.getElementById("confirmNewPassword")?.value;

            if (!currentPw || !newPw || !confirmPw) {
                showAlert("password-alert", "All password fields are required.", "warning");
                return;
            }

            if (newPw !== confirmPw) {
                showAlert("password-alert", "New passwords do not match.", "danger");
                return;
            }

            if (newPw.length < 8) {
                showAlert("password-alert", "New password must be at least 8 characters.", "danger");
                return;
            }

            const origHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Updating Password...';

            try {
                const res = await apiClient.post("/auth/change-password", {
                    current_password: currentPw,
                    new_password: newPw,
                    confirm_new_password: confirmPw
                });

                submitBtn.disabled = false;
                submitBtn.innerHTML = origHtml;
                pwForm.reset();
                showAlert("password-alert", "Password changed successfully!", "success");
            } catch (err) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origHtml;
                const msg = (err.data && err.data.message) || err.message || "Failed to change password.";
                showAlert("password-alert", msg, "danger");
            }
        });
    }
}

