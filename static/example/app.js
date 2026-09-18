(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector("[data-theme-toggle]");
  const themeIcon = document.querySelector("[data-theme-icon]");
  const toast = document.querySelector("[data-toast]");

  const preferredTheme = () => {
    const saved = localStorage.getItem("authkits-example-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };

  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    if (themeIcon) themeIcon.textContent = theme === "dark" ? "☼" : "◐";
    if (themeButton) {
      themeButton.setAttribute(
        "aria-label",
        theme === "dark" ? "Use light theme" : "Use dark theme",
      );
    }
  };

  applyTheme(preferredTheme());

  themeButton?.addEventListener("click", () => {
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("authkits-example-theme", next);
    applyTheme(next);
  });

  let toastTimer;
  const showToast = (message) => {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 1800);
  };

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.querySelector(button.dataset.copy);
      if (!target) return;

      try {
        await navigator.clipboard.writeText(target.textContent.trim());
        button.textContent = "Copied";
        showToast("Copied to clipboard");
        window.setTimeout(() => {
          button.textContent = "Copy";
        }, 1600);
      } catch {
        showToast("Copy failed");
      }
    });
  });
})();
