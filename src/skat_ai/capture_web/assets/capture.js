(() => {
  "use strict";

  const focusKey = "skat-ai-capture-focus";
  const restoreFocus = () => {
    const remembered = sessionStorage.getItem(focusKey);
    if (!remembered) return;
    const target = document.querySelector(remembered);
    if (target) target.focus();
    sessionStorage.removeItem(focusKey);
  };
  const replacePage = async (response, pushHistory) => {
    const html = await response.text();
    const next = new DOMParser().parseFromString(html, "text/html");
    const replacement = next.querySelector("#capture-app");
    if (!replacement) throw new Error("Invalid local Capture response.");
    document.querySelector("#capture-app").replaceWith(replacement);
    document.title = next.title;
    if (pushHistory && response.url) history.pushState({}, "", response.url);
    replacement.querySelectorAll("[data-analysis-method-form]").forEach(updateSearchSettings);
    restoreFocus();
  };
  restoreFocus();

  const updateSearchSettings = (form) => {
    const method = form.querySelector("[data-analysis-method]");
    const settings = form.querySelector("[data-search-settings]");
    if (!method || !settings) return;
    const visible = method.value !== "immediate_expected_value";
    settings.hidden = !visible;
    const seed = settings.querySelector('[name="search_random_seed"]');
    if (seed) seed.required = visible;
  };
  document.querySelectorAll("[data-analysis-method-form]").forEach(updateSearchSettings);

  document.addEventListener("change", (event) => {
    const form = event.target.closest("[data-analysis-method-form]");
    if (form) updateSearchSettings(form);
  });

  document.addEventListener("submit", async (event) => {
    const confirmation = event.target.dataset.confirm;
    if (confirmation && !window.confirm(confirmation)) {
      event.preventDefault();
      return;
    }
    if (event.target.matches("[data-native-submit]")) return;
    const active = document.activeElement;
    if (active && active.name) {
      const valueSelector = active.value
        ? `[value="${CSS.escape(active.value)}"]`
        : "";
      sessionStorage.setItem(
        focusKey,
        `[name="${CSS.escape(active.name)}"]${valueSelector}`,
      );
    }
    event.preventDefault();
    try {
      const data = new FormData(event.target, event.submitter);
      const response = await fetch(event.target.action, {
        method: "POST",
        body: new URLSearchParams(data),
        credentials: "same-origin",
      });
      await replacePage(response, response.ok);
    } catch (_error) {
      if (event.submitter?.name) {
        const hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = event.submitter.name;
        hidden.value = event.submitter.value;
        event.target.append(hidden);
      }
      HTMLFormElement.prototype.submit.call(event.target);
    }
  });

  document.addEventListener("click", async (event) => {
    const link = event.target.closest("a.position-card, a[data-report-link]");
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey) return;
    event.preventDefault();
    try {
      await replacePage(await fetch(link.href, { credentials: "same-origin" }), true);
    } catch (_error) {
      window.location.assign(link.href);
    }
  });

  window.addEventListener("popstate", () => window.location.reload());

  document.addEventListener("keydown", (event) => {
    if (event.altKey && event.key === "ArrowLeft") {
      const previous = document.querySelector("[data-position-previous]");
      if (previous) window.location.assign(previous.href);
    }
    if (event.altKey && event.key === "ArrowRight") {
      const next = document.querySelector("[data-position-next]");
      if (next) window.location.assign(next.href);
    }
    if (event.altKey && event.key.toLowerCase() === "u") {
      const form = document.querySelector("[data-undo-form]");
      if (form) form.requestSubmit();
    }
    if (event.key === "/" && document.activeElement?.tagName !== "INPUT") {
      const input = document.querySelector("[data-card-input]");
      if (input) {
        event.preventDefault();
        input.focus();
      }
    }
  });
})();
