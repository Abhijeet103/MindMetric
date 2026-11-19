/* Browser-monitored recruitment sessions. Server owns timing, keys and scoring. */
(() => {
    const root = document.getElementById("candidate-assessment");
    const start = document.getElementById("candidate-start");
    if (!root || !start) return;
    const runner = document.getElementById("candidate-runner");
    const status = document.getElementById("candidate-status");
    const saveStatus = document.getElementById("candidate-save-status");
    const csrf = document.querySelector("#candidate-csrf input").value;
    let active = false, sending = false, finishing = false, current = 0;
    let state, answers = {}, events = [], heartbeat, ticker, saveTimer;
    let revision = 0;
    let deadline = 0;

    async function request(url, data) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch(url, {
                method: "POST", credentials: "same-origin", signal: controller.signal,
                headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
                body: JSON.stringify(data),
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(result.detail || "Could not save. Check your connection and sign-in status.");
            return result;
        } finally { clearTimeout(timeout); }
    }

    async function complete(result) {
        active = false;
        finishing = false;
        clearInterval(heartbeat); clearInterval(ticker); clearTimeout(saveTimer);
        runner.hidden = true;
        document.getElementById("candidate-intro").hidden = true;
        status.textContent = result.status === "expired"
            ? "Time has ended. Your saved answers have been submitted to the recruiter."
            : "Assessment received. Your recruiter can now review the results.";
        if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
    }

    async function save(submit = false) {
        if (!active) return;
        if (sending) {
            if (submit) { finishing = true; }
            return;
        }
        sending = true;
        const batch = events.splice(0, 20);
        const snapshot = {...answers};
        try {
            const result = await request(state.url, {answers: snapshot, revision, events: batch, submit});
            if (result.status !== "active") { await complete(result); return; }
            saveStatus.textContent = "Answers saved.";
        } catch (error) {
            events = [...batch, ...events].slice(0, 200);
            saveStatus.textContent = "Not saved yet. " + error.message + " The timer continues; keep this page open.";
            if (submit) finishing = true;
        } finally {
            sending = false;
            if (finishing && active) {
                finishing = false;
                setTimeout(() => save(true), 1500);
            }
        }
    }

    function record(kind) {
        if (!active) return;
        if (events.length < 200) events.push(kind);
        if (kind === "tab_hidden" || kind === "fullscreen_exit") {
            saveStatus.textContent = "An interruption was recorded for recruiter review. The timer continues.";
        }
        void save();
    }

    function display() {
        const item = state.questions[current];
        const context = document.getElementById("candidate-context");
        const question = document.getElementById("candidate-question");
        const options = document.getElementById("candidate-options");
        const nav = document.getElementById("candidate-question-nav");
        context.replaceChildren();
        const exhibits = Boolean(item.data_table || item.case_study || item.chart);
        if (!exhibits) {
            if (["statements", "pairs", "numbers", "words", "letter_pairs"].includes(item.context_kind)) {
                renderContext(context, item);
            } else if (item.instruction) {
                const paragraph = document.createElement("p");
                paragraph.textContent = item.instruction;
                context.appendChild(paragraph);
            }
        }
        question.textContent = item.question_text || item.summary;
        renderQuestionTable(question, item);
        renderCcatSpatialStimulus(question, item);
        options.replaceChildren();
        item.options.forEach((option, index) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "answer-option";
            renderCcatSpatialOption(button, item, option, index);
            button.setAttribute("aria-pressed", String(answers[String(current)] === option));
            button.addEventListener("click", () => {
                if (!active || performance.now() >= deadline) return;
                answers[String(current)] = option;
                revision++;
                saveStatus.textContent = "Saving answer…";
                display();
                clearTimeout(saveTimer);
                saveTimer = setTimeout(() => save(), 250);
            });
            options.appendChild(button);
        });
        nav.replaceChildren();
        state.questions.forEach((_, index) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "button-secondary button-small";
            button.textContent = String(index + 1);
            button.setAttribute("aria-label", "Question " + (index + 1));
            button.setAttribute("aria-current", String(index === current));
            button.dataset.answered = String(Object.hasOwn(answers, String(index)));
            button.addEventListener("click", () => { current = index; display(); });
            nav.appendChild(button);
        });
        document.getElementById("candidate-progress").textContent = `Question ${current + 1} of ${state.questions.length} · ${Object.keys(answers).length} answered`;
        document.getElementById("candidate-previous").disabled = current === 0;
        document.getElementById("candidate-next").disabled = current === state.questions.length - 1;
    }

    function tick() {
        const remaining = Math.max(0, Math.ceil((deadline - performance.now()) / 1000));
        document.getElementById("candidate-timer").textContent = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")} remaining`;
        if (!remaining && active) {
            // The server independently expires the session, even if this timer is changed.
            void save(true);
        }
    }

    start.addEventListener("click", async () => {
        if (!document.getElementById("candidate-consent").checked) {
            status.textContent = "Acknowledge the monitoring notice before starting."; return;
        }
        start.disabled = true;
        runner.hidden = false;
        let fullscreenUnavailable = false;
        try { await runner.requestFullscreen(); }
        catch { fullscreenUnavailable = true; }
        try {
            state = await request(root.dataset.startUrl, {consent: true});
            if (state.status !== "active") { await complete(state); return; }
            answers = {...state.answers};
            revision = state.revision || 0;
            const remainingMs = Math.max(0, Date.parse(state.deadline) - Date.parse(state.server_now));
            deadline = performance.now() + remainingMs;
            document.getElementById("candidate-intro").hidden = true;
            active = true;
            if (fullscreenUnavailable) record("fullscreen_unavailable");
            display(); tick(); runner.focus();
            heartbeat = setInterval(() => save(), 10000);
            ticker = setInterval(tick, 1000);
            status.textContent = "";
        } catch (error) {
            runner.hidden = true;
            status.textContent = error.message;
            start.disabled = false;
            if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
        }
    });
    document.getElementById("candidate-previous").addEventListener("click", () => { if (current > 0) { current--; display(); } });
    document.getElementById("candidate-next").addEventListener("click", () => { if (current < state.questions.length - 1) { current++; display(); } });
    document.getElementById("candidate-submit").addEventListener("click", () => {
        if (confirm(`Submit your assessment? You have answered ${Object.keys(answers).length} of ${state.questions.length} questions. You cannot change answers after submitting.`)) {
            finishing = true;
            void save(true);
        }
    });
    document.getElementById("candidate-fullscreen").addEventListener("click", async () => {
        try { await runner.requestFullscreen(); } catch { record("fullscreen_unavailable"); }
    });
    document.addEventListener("visibilitychange", () => { if (document.hidden) record("tab_hidden"); });
    window.addEventListener("blur", () => record("window_blur"));
    document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement) record("fullscreen_exit"); });
    ["copy", "paste"].forEach(kind => runner.addEventListener(kind, event => {
        if (active) { event.preventDefault(); record(kind + "_attempt"); }
    }));
    window.addEventListener("pagehide", () => {
        if (!active) return;
        fetch(state.url, {method: "POST", credentials: "same-origin", keepalive: true,
            headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
            body: JSON.stringify({answers, revision, events: [...events, "tab_hidden"].slice(0, 20)})}).catch(() => {});
    });
})();
