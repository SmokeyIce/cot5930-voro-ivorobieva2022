document.querySelectorAll("[data-image-form]").forEach((form) => {
  const input = form.querySelector('input[type="file"]');
  const label = form.querySelector("[data-file-label]");

  input.addEventListener("change", () => {
    label.textContent = input.files?.[0]?.name || "Choose a PNG image";
  });
});