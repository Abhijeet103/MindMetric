// Subtle motion for the home page: the headline types itself once and lower
// sections ease in as they scroll into view. Text is always in the HTML, so
// crawlers, screen readers and visitors without JS or with reduced motion see
// the finished page.
(function () {
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

  const title = document.querySelector("[data-type-on]");
  if (title) {
    const full = title.textContent.trim();
    title.setAttribute("aria-label", full);
    title.textContent = "";
    const typed = document.createElement("span");
    typed.setAttribute("aria-hidden", "true");
    const caret = document.createElement("span");
    caret.className = "type-caret";
    caret.setAttribute("aria-hidden", "true");
    // The untyped rest stays in the layout (transparent) so nothing shifts.
    const rest = document.createElement("span");
    rest.className = "type-rest";
    rest.setAttribute("aria-hidden", "true");
    rest.textContent = full;
    title.append(typed, caret, rest);
    let i = 0;
    const step = () => {
      i += 1;
      typed.textContent = full.slice(0, i);
      rest.textContent = full.slice(i);
      if (i < full.length) {
        const pause = /[ .,]/.test(full[i - 1]) ? 90 : 45;
        window.setTimeout(step, pause);
      } else {
        window.setTimeout(() => caret.classList.add("is-done"), 2200);
      }
    };
    window.setTimeout(step, 250);
  }

  const sections = document.querySelectorAll("[data-reveal]");
  if (sections.length && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-revealed");
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -10% 0px" });
    sections.forEach((section) => {
      const box = section.getBoundingClientRect();
      if (box.top > window.innerHeight) {
        section.classList.add("reveal-pending");
        observer.observe(section);
      }
    });
  }
})();
