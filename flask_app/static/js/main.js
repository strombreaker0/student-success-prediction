/**
 * AI-Based Student Academic Success Prediction System
 * Production Client Script: Theme Toggle, Password Visibility, Autocomplete, Debounce
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Theme Management (Dark / Light persistence)
  const themeToggleBtns = document.querySelectorAll("#theme-toggle-btn, .theme-toggle-trigger");
  const htmlEl = document.documentElement;
  const currentTheme = localStorage.getItem("edu_theme") || "light";
  htmlEl.setAttribute("data-theme", currentTheme);
  updateThemeIcons(currentTheme);

  themeToggleBtns.forEach(btn => {
    btn.addEventListener("click", function () {
      const active = htmlEl.getAttribute("data-theme");
      const next = active === "dark" ? "light" : "dark";
      htmlEl.setAttribute("data-theme", next);
      localStorage.setItem("edu_theme", next);
      updateThemeIcons(next);
      window.dispatchEvent(new CustomEvent("themeChanged", { detail: { theme: next } }));
    });
  });

  function updateThemeIcons(theme) {
    const icons = document.querySelectorAll("#theme-icon, .theme-icon-el");
    icons.forEach(icon => {
      if (theme === "dark") {
        icon.className = "bi bi-sun-fill";
      } else {
        icon.className = "bi bi-moon-stars-fill";
      }
    });
  }

  // 2. Mobile Sidebar Toggle & Outside Click
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".app-sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      sidebar.classList.toggle("show");
    });

    document.addEventListener("click", function (e) {
      if (sidebar.classList.contains("show") && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
        sidebar.classList.remove("show");
      }
    });
  }

  // 3. Password Visibility Toggle
  document.querySelectorAll(".password-toggle-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const targetId = btn.getAttribute("data-target");
      const input = targetId ? document.getElementById(targetId) : btn.closest(".input-group").querySelector("input");
      if (input) {
        const isPassword = input.getAttribute("type") === "password";
        input.setAttribute("type", isPassword ? "text" : "password");
        const icon = btn.querySelector("i");
        if (icon) {
          icon.className = isPassword ? "bi bi-eye-slash" : "bi bi-eye";
        }
      }
    });
  });

  // 4. Prevent Duplicate Form Submissions
  const forms = document.querySelectorAll("form:not(.no-debounce)");
  forms.forEach(function (form) {
    form.addEventListener("submit", function () {
      const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        setTimeout(function () {
          submitBtn.disabled = true;
          if (submitBtn.tagName === "BUTTON") {
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Processing...';
            // Re-enable after 8 seconds in case of timeout or client validation halt
            setTimeout(() => {
              submitBtn.disabled = false;
              submitBtn.innerHTML = originalText;
            }, 8000);
          }
        }, 50);
      }
    });
  });

  // 5. Global Search Autocomplete
  const searchInput = document.getElementById("global-search-input");
  const searchResults = document.getElementById("search-results-dropdown");
  let searchTimer = null;

  if (searchInput && searchResults) {
    searchInput.addEventListener("input", function () {
      clearTimeout(searchTimer);
      const query = searchInput.value.trim();
      if (query.length < 2) {
        searchResults.style.display = "none";
        return;
      }

      searchTimer = setTimeout(function () {
        fetch(`/search?q=${encodeURIComponent(query)}`)
          .then((r) => r.json())
          .then((items) => {
            if (!items || items.length === 0) {
              searchResults.innerHTML = '<div class="p-3 text-muted small text-center"><i class="bi bi-search me-1"></i>No matching students found</div>';
              searchResults.style.display = "block";
              return;
            }

            let html = "";
            items.forEach((it) => {
              html += `<a href="${it.url}" class="dropdown-item py-2 px-3 d-flex align-items-center justify-content-between border-bottom border-light">
                <div>
                  <div class="fw-semibold text-primary"><i class="bi bi-person me-2"></i>${it.label}</div>
                </div>
                <span class="badge bg-secondary text-uppercase" style="font-size:10px;">${it.type}</span>
              </a>`;
            });
            searchResults.innerHTML = html;
            searchResults.style.display = "block";
          })
          .catch(() => {
            searchResults.style.display = "none";
          });
      }, 250);
    });

    document.addEventListener("click", function (e) {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.style.display = "none";
      }
    });
  }
});
