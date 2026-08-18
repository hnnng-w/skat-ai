(() => {
  "use strict";

  for (const input of document.querySelectorAll('input[type="file"]')) {
    input.addEventListener("change", () => {
      const label = input.closest("label");
      if (label && input.files.length === 1) {
        label.title = "One local JSON file selected";
      }
    });
  }
})();
