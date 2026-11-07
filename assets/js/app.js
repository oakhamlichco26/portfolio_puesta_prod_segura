// Portfolio estático · Puesta en Producción Segura
// JS vanilla, sin dependencias externas. Sin scripts inline (CSP).

(function () {
  "use strict";

  var html = document.documentElement;
  var themeToggle = document.getElementById("theme-toggle");
  var menuBtn = document.getElementById("menu-toggle");
  var menuList = document.getElementById("menu-list");
  var sidebar = document.getElementById("sidebar");

  // ------------------------------------------------------------------
  // Tema claro/oscuro (prefers-color-scheme + toggle manual + localStorage)
  // ------------------------------------------------------------------
  var THEME_KEY = "pps-theme";

  function setTheme(theme) {
    if (theme === "dark") {
      html.classList.add("dark");
    } else {
      html.classList.remove("dark");
    }
    if (themeToggle) {
      themeToggle.setAttribute("aria-pressed", theme === "dark");
    }
    if (theme === "system" || theme === "auto") {
      localStorage.removeItem(THEME_KEY);
    } else {
      localStorage.setItem(THEME_KEY, theme);
    }
  }

  function resolveTheme() {
    var saved = localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") {
      setTheme(saved);
    } else {
      setTheme(window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    }
  }

  resolveTheme();

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var next = html.classList.contains("dark") ? "light" : "dark";
      setTheme(next);
    });
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", function (e) {
        if (!localStorage.getItem(THEME_KEY)) {
          setTheme(e.matches ? "dark" : "light");
        }
      });
  }

  // ------------------------------------------------------------------
  // Menú hamburguesa accesible (móvil) + cierre con Esc
  // ------------------------------------------------------------------
  var expanded = false;
  var backdrop = null;

  function ensureBackdrop() {
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "sidebar-backdrop";
      backdrop.addEventListener("click", function () {
        setExpanded(false);
      });
      document.body.appendChild(backdrop);
    }
    return backdrop;
  }

  function removeBackdrop() {
    if (backdrop) {
      backdrop.classList.remove("visible");
    }
  }

  function setExpanded(isOpen) {
    expanded = isOpen;
    if (menuBtn) {
      menuBtn.setAttribute("aria-expanded", String(isOpen));
    }
    if (sidebar) {
      if (isOpen) {
        sidebar.classList.add("open");
        ensureBackdrop().classList.add("visible");
      } else {
        sidebar.classList.remove("open");
        removeBackdrop();
      }
    }
  }

  if (menuBtn) {
    menuBtn.addEventListener("click", function () {
      setExpanded(!expanded);
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && expanded) {
      setExpanded(false);
      if (menuBtn) menuBtn.focus();
    }
  });

  // Al hacer clic en un enlace del menú (móvil), se cierra el menú
  if (menuList) {
    menuList.addEventListener("click", function (e) {
      var link = e.target.closest("a");
      if (link && expanded) {
        setExpanded(false);
      }
    });
  }

  // ------------------------------------------------------------------
  // Resaltar el ejercicio activo en el sidebar (por ruta actual)
  // ------------------------------------------------------------------
  function setActiveMenuItem() {
    if (!menuList) return;
    var path = location.pathname.replace(/^.*\//, "");
    var links = menuList.querySelectorAll("a");
    links.forEach(function (a) {
      var href = a.getAttribute("href") || "";
      var isActive = href === path || (path === "" && href === "index.html");
      a.classList.toggle("active", isActive);
    });
  }
  setActiveMenuItem();

  // ------------------------------------------------------------------
  // Botones "Copiar" de los bloques de código
  // ------------------------------------------------------------------
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-copy]");
    if (!btn) return;
    e.preventDefault();

    var figure = btn.closest(".code-block");
    var codeEl = figure ? figure.querySelector("pre code") : null;
    if (!codeEl) return;

    var text = codeEl.textContent || "";
    var oldLabel = btn.textContent;

    function reset() {
      btn.textContent = oldLabel;
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(function () {
          btn.textContent = "¡Copiado!";
          setTimeout(reset, 1200);
        })
        .catch(function (err) {
          // Fallback silencioso si el portapapeles no está disponible
          console.warn("No se pudo copiar al portapapeles:", err);
          reset();
        });
    } else {
      reset();
    }
  });
})();
