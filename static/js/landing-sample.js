// Homepage sample question: answer once, see feedback, try again or move on.
// No timer and no auto-play; the result is announced through aria-live.
(function () {
  const card = document.querySelector("[data-landing-sample]");
  if (!card) return;
  const options = card.querySelectorAll("[data-sample-option]");
  const results = card.querySelectorAll("[data-sample-result]");

  function show(kind) {
    options.forEach((option) => {
      option.disabled = true;
      option.setAttribute("aria-pressed", "false");
      if (option.dataset.sampleOption === "right") option.classList.add("is-right");
    });
    const picked = card.querySelector(`[data-sample-option="${kind}"]`);
    picked.setAttribute("aria-pressed", "true");
    if (kind === "wrong") picked.classList.add("is-wrong");
    results.forEach((result) => { result.hidden = result.dataset.sampleResult !== kind; });
    // The answer buttons are now disabled, so move focus to the feedback line.
    card.querySelector(`[data-sample-result="${kind}"] .landing-sample-feedback`)?.focus({ preventScroll: true });
  }

  function reset() {
    options.forEach((option) => {
      option.disabled = false;
      option.classList.remove("is-right", "is-wrong");
      option.removeAttribute("aria-pressed");
    });
    results.forEach((result) => { result.hidden = true; });
    options[0].focus({ preventScroll: true });
  }

  options.forEach((option) => option.addEventListener("click", () => show(option.dataset.sampleOption)));
  card.querySelector("[data-sample-reset]")?.addEventListener("click", reset);
})();
