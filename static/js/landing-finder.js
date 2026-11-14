// Homepage finder: type a test, a test publisher, or a company and jump to the right practice.
// Without JavaScript the form still submits to the company lookup.
(() => {
  const form = document.querySelector("[data-landing-finder]");
  const dataEl = document.getElementById("landing-finder-data");
  if (!form || !dataEl) return;

  const data = JSON.parse(dataEl.textContent);
  const input = form.querySelector("input[name=q]");
  const list = form.querySelector(".landing-finder-list");
  let options = [];
  let active = -1;

  const normalise = (text) => (text || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9 ]+/g, " ").trim();

  const matches = (query) => {
    const q = normalise(query);
    if (!q) return [];
    const words = q.split(/\s+/);
    const hit = (haystack) => words.every((word) => haystack.split(/\s+/).some((token) => token.startsWith(word)));
    const results = [];
    for (const test of data.tests) {
      if (hit(normalise(`${test.label} ${test.hint} ${test.keywords}`))) {
        results.push({kind: "test", title: test.label, meta: test.hint || "Practice test", url: test.url});
      }
    }
    for (const company of data.companies) {
      if (hit(normalise(company.name))) {
        results.push({kind: "company", title: company.name, meta: `Uses ${company.test}`, url: company.url});
      }
    }
    results.splice(6);
    results.push({kind: "lookup", title: `Search companies for “${query.trim()}”`, meta: "", url: `${data.lookup_url}?q=${encodeURIComponent(query.trim())}`});
    return results;
  };

  const setActive = (index) => {
    active = index;
    [...list.children].forEach((item, i) => item.setAttribute("aria-selected", String(i === active)));
    const current = list.children[active];
    input.setAttribute("aria-activedescendant", current ? current.id : "");
    current?.scrollIntoView({block: "nearest"});
  };

  const close = () => {
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    active = -1;
  };

  const render = () => {
    options = matches(input.value);
    list.replaceChildren();
    if (!options.length) return close();
    options.forEach((option, index) => {
      const item = document.createElement("li");
      item.id = `landing-finder-option-${index}`;
      item.role = "option";
      item.className = `landing-finder-option is-${option.kind}`;
      const title = document.createElement("span");
      title.className = "landing-finder-option-title";
      title.textContent = option.title;
      item.append(title);
      if (option.meta) {
        const meta = document.createElement("small");
        meta.textContent = option.meta;
        item.append(meta);
      }
      item.addEventListener("mousedown", (event) => {
        event.preventDefault();
        go(option);
      });
      list.append(item);
    });
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    setActive(options.length > 1 ? 0 : -1);
  };

  const go = (option) => {
    window.showPageLoader?.();
    window.location.assign(option.url);
  };

  input.addEventListener("input", render);
  input.addEventListener("focus", () => input.value && render());
  input.addEventListener("blur", () => setTimeout(close, 120));
  input.addEventListener("keydown", (event) => {
    if (list.hidden) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive(Math.min(active + 1, options.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive(Math.max(active - 1, 0));
    } else if (event.key === "Escape") {
      close();
    }
  });
  form.addEventListener("submit", (event) => {
    const query = input.value.trim();
    if (!query) {
      event.preventDefault();
      input.focus();
      return;
    }
    const choice = options[active] || matches(query)[0];
    if (choice) {
      event.preventDefault();
      go(choice);
    }
  });
})();
