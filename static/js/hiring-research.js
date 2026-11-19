(() => {
    const form = document.getElementById("hiring-search");
    if (!form) return;
    const status = document.getElementById("hiring-status");
    const report = document.getElementById("hiring-report");
    const button = form.querySelector("button[type=submit]");
    const originalLabel = button.textContent;
    let generation = 0;
    let controller;
    const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

    function busy(value) {
        button.disabled = value || form.dataset.canResearch !== "true";
        button.textContent = value ? "Researching…" : originalLabel;
        report.setAttribute("aria-busy", String(value));
    }

    async function request(url, options = {}) {
        controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 25000);
        try {
            const response = await fetch(url, {credentials: "same-origin", ...options, signal: controller.signal});
            const body = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(body.error || "Research is unavailable. Please try again later.");
            return body;
        } finally { clearTimeout(timeout); }
    }

    async function follow(result, token) {
        const deadline = Date.now() + 10 * 60 * 1000;
        while (token === generation) {
            if (result.status !== "pending") {
                // Server-rendered templates escape all model text and validate external links.
                report.innerHTML = result.html || "";
                status.textContent = result.status === "completed" ? (result.cached ? "Your saved prep guide is ready." : "Your prep guide is ready.") : "Research couldn't finish. Try again later.";
                return;
            }
            if (Date.now() > deadline) throw new Error("Research is taking longer than expected. Reload this page to check it again.");
            status.textContent = "Searching hiring information and interview accounts, then building your plan. This can take a few minutes; you can return to this page.";
            await wait(5000);
            if (token !== generation) return;
            result = await request(result.status_url);
        }
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (form.dataset.canResearch !== "true") return;
        const token = ++generation;
        const data = new FormData(form);
        data.set("csrfmiddlewaretoken", document.querySelector('#hiring-csrf input').value);
        busy(true);
        report.replaceChildren();
        document.getElementById("hiring-curated").hidden = true;
        status.textContent = "Starting your hiring research…";
        try {
            const result = await request(form.dataset.researchUrl, {method: "POST", body: data});
            const url = new URL(window.location.href);
            url.search = new URLSearchParams({company: data.get("company"), role: data.get("role"), report: result.id});
            history.replaceState(null, "", url);
            await follow(result, token);
        } catch (error) {
            status.textContent = error.name === "AbortError" ? "The connection timed out. Reload this page to check your research before starting again." : error.message;
        } finally { if (token === generation) busy(false); }
    });

    if (report.dataset.statusUrl) {
        const token = ++generation;
        busy(true);
        follow({status: "pending", status_url: report.dataset.statusUrl}, token)
            .catch(error => { status.textContent = error.message; })
            .finally(() => { if (token === generation) busy(false); });
    }
    window.addEventListener("pagehide", () => { generation++; controller?.abort(); });
})();
