(() => {
  const root = document.querySelector('[data-workshop]');
  if (!root) return;
  const get = (name) => root.querySelector(`[data-workshop-${name}]`);
  let state = null, busy = false, readAnswer = () => null;
  const csrf = root.querySelector('[name=csrfmiddlewaretoken]').value;
  const element = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
  const previouslyDisabled = new WeakMap();
  const setBusy = (value) => { busy = value; root.querySelectorAll('button').forEach((button) => { if (value) { previouslyDisabled.set(button, button.disabled); button.disabled = true; } else if (previouslyDisabled.has(button)) { button.disabled = previouslyDisabled.get(button); previouslyDisabled.delete(button); } }); };
  const request = async (url, payload) => {
    if (busy) return;
    setBusy(true); get('status').textContent = 'Saving…';
    try {
      const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf}, body: JSON.stringify(payload)});
      if (response.redirected || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('Session unavailable. Sign in again or return to the assessment.');
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Could not save. Your current response is still on screen.');
      if (payload.action === 'report') { get('status').textContent = 'Issue saved for review.'; return; }
      const draftOnly = payload.action === 'draft';
      state = result;
      const location = new URL(window.location.href); location.searchParams.set('session', state.session_id); window.history.replaceState(null, '', location);
      if (!draftOnly) render();
      get('status').textContent = draftOnly ? 'Draft saved.' : 'Progress saved.';
    } catch (error) { get('status').textContent = error.message; }
    finally { setBusy(false); }
  };
  const update = (payload) => request(`/api/tests/workshops/${state.session_id}/`, {stage_index: state.stage_index, ...payload});
  const render = () => {
    get('player').hidden = false;
    get('title').textContent = state.title;
    get('intro').textContent = state.intro;
    get('progress').textContent = state.complete ? 'Workshop complete' : `Stage ${state.stage_index + 1} of ${state.total}`;
    const shell = get('stage'); shell.replaceChildren();
    get('feedback').replaceChildren(); get('report').replaceChildren();
    get('submit').hidden = state.complete || state.answered;
    get('next').hidden = state.complete || !state.answered;
    get('draft').hidden = true;
    if (state.complete) {
      shell.appendChild(element('p', `${state.correct} of ${state.graded} objective responses correct. ${state.written} written responses saved. Rubric ratings are self-review, not an automated quality score.`));
      state.responses.forEach((row, i) => { const details = element('details'); details.append(element('summary', `Response ${i + 1}`), element('pre', typeof row.answer === 'object' ? JSON.stringify(row.answer, null, 2) : String(row.answer))); shell.appendChild(details); });
      if (state.human_review) shell.append(element('h3', 'Reviewer feedback'), element('p', state.human_review));
      (state.peer_reviews || []).forEach((review) => shell.append(element('h3', 'Peer feedback'), element('p', review.feedback)));
      const inviteNote = element('p', 'You can create a revocable 7-day link sharing your completed responses and rubrics with a signed-in peer in your organisation.');
      const invite = element('button', 'Create peer review link'); invite.type = 'button'; invite.className = 'button-secondary';
      const revoke = element('button', 'Revoke review links'); revoke.type = 'button'; revoke.className = 'button-secondary';
      const linkArea = element('p'); linkArea.setAttribute('role', 'status');
      const inviteRequest = async (revokeLinks) => {
        if (busy) return;
        setBusy(true);
        try {
          const response = await fetch(`/api/tests/workshops/${state.session_id}/review-invite/`, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf}, body: JSON.stringify({revoke: revokeLinks})});
          if (!response.ok || response.redirected) throw new Error('Could not update the review link. Sign in and retry.');
          const data = await response.json(); linkArea.replaceChildren();
          if (data.revoked) linkArea.textContent = 'Review links revoked.';
          else { const link = element('a', data.url); link.href = data.url; linkArea.appendChild(link); }
        } catch (error) { linkArea.textContent = error.message; }
        finally { setBusy(false); }
      };
      invite.addEventListener('click', () => void inviteRequest(false)); revoke.addEventListener('click', () => void inviteRequest(true));
      shell.append(inviteNote, invite, revoke, linkArea);
      shell.appendChild(element('p', 'Choose an exercise above to begin a new session.'));
      return;
    }
    const stage = state.stage;
    if (stage.passage) { const passage = element('article'); passage.className = 'workshop-passage'; passage.append(element('h3', 'Shared passage'), element('p', stage.passage), element('p', state.review_status)); shell.appendChild(passage); }
    if (stage.instruction) shell.appendChild(element('p', stage.instruction));
    const question = element('h3', stage.question); shell.appendChild(question);
    renderQuestionTable(question, {data_table: stage.data_table, chart: stage.chart});
    (stage.context_tables || []).forEach((table) => { const block = element('div'); const heading = element('h4', 'Earlier exhibit'); block.appendChild(heading); shell.appendChild(block); renderQuestionTable(heading, {data_table: table}); });
    (stage.constraints || []).forEach((rule) => shell.appendChild(element('p', rule)));
    const inputs = element('div'); inputs.className = 'workshop-inputs'; shell.appendChild(inputs);
    if (stage.kind === 'choice') {
      stage.options.forEach((value, i) => { const label = element('label'); const input = element('input'); input.type = 'radio'; input.name = 'workshop-choice'; input.value = value; input.id = `workshop-choice-${i}`; label.append(input, document.createTextNode(value)); inputs.appendChild(label); });
      readAnswer = () => inputs.querySelector('input:checked')?.value;
    } else if (stage.kind === 'numeric') {
      const label = element('label', 'Your numeric answer'); const input = element('input'); input.type = 'number'; input.step = 'any'; label.appendChild(input); inputs.appendChild(label); readAnswer = () => input.value;
    } else if (stage.kind === 'written' || stage.kind === 'estimate') {
      let estimate = null;
      if (stage.kind === 'estimate') { const label = element('label', 'Base-case annual revenue estimate (£)'); estimate = element('input'); estimate.type = 'number'; estimate.step = 'any'; estimate.min = '0'; if (state.draft && typeof state.draft === 'object') estimate.value = state.draft.estimate; label.appendChild(estimate); inputs.appendChild(label); }
      const label = element('label', 'Your reasoning'); const text = element('textarea'); text.rows = 9; text.maxLength = 6000; text.value = typeof state.draft === 'string' ? state.draft : state.draft?.text || ''; label.appendChild(text); inputs.appendChild(label);
      get('draft').hidden = state.answered;
      readAnswer = () => ({text: text.value, ...(estimate ? {estimate: estimate.value} : {})});
    } else if (stage.kind === 'schedule') {
      stage.labels.forEach((slot) => { const label = element('label', slot); const select = element('select'); select.appendChild(element('option', 'Choose a person')); select.firstChild.value = ''; stage.options.forEach((person) => { const option = element('option', person); option.value = person; select.appendChild(option); }); label.appendChild(select); inputs.appendChild(label); });
      readAnswer = () => Array.from(inputs.querySelectorAll('select')).map((s) => s.value);
    } else if (stage.kind === 'chart_builder') {
      const chart = element('div'); shell.appendChild(chart);
      const draw = () => { chart.replaceChildren(renderDataChart({title: 'Your constructed chart (requests)', labels: stage.labels, values: Array.from(inputs.querySelectorAll('input')).map((i) => Number(i.value) || 0)})); };
      stage.labels.forEach((name) => { const label = element('label', `${name}: requests`); const input = element('input'); input.type = 'number'; input.min = '0'; input.step = '1'; input.addEventListener('input', draw); label.appendChild(input); inputs.appendChild(label); });
      readAnswer = () => Array.from(inputs.querySelectorAll('input')).map((i) => i.value); draw();
    } else if (stage.kind === 'node_path') {
      const selected = []; const path = element('p', 'Your path:'); inputs.appendChild(path);
      stage.options.forEach((value) => { const button = element('button', value); button.type = 'button'; button.className = 'button-secondary'; button.addEventListener('click', () => { if (selected.length >= stage.length) return; selected.push(value); button.disabled = true; path.textContent = `Your path: ${selected.join(' → ')}`; }); inputs.appendChild(button); });
      const reset = element('button', 'Reset path'); reset.type = 'button'; reset.addEventListener('click', () => { selected.length = 0; inputs.querySelectorAll('button').forEach((b) => { b.disabled = false; }); path.textContent = 'Your path:'; }); inputs.appendChild(reset); readAnswer = () => [...selected];
    }
    if (state.answered) {
      inputs.querySelectorAll('input, textarea, select, button').forEach((input) => { input.disabled = true; });
      const feedback = get('feedback'); feedback.append(element('h3', state.feedback.correct === null ? 'Review your reasoning' : state.feedback.correct ? 'Correct' : 'Review the solution'), element('p', state.feedback.explanation));
      if (state.feedback.answer !== undefined && state.feedback.answer !== null) feedback.appendChild(element('p', `Reference answer: ${Array.isArray(state.feedback.answer) ? state.feedback.answer.join(' → ') : state.feedback.answer}`));
      feedback.appendChild(element('pre', typeof state.feedback.response === 'object' ? JSON.stringify(state.feedback.response, null, 2) : String(state.feedback.response)));
      if (state.feedback.reference) feedback.appendChild(element('p', state.feedback.reference));
      if (state.feedback.rubric.length) {
        feedback.appendChild(element('p', 'Self-review: 0 = not addressed; 1 = partly addressed; 2 = clearly supported. These ratings do not change your objective score.'));
        const selects = [];
        state.feedback.rubric.forEach((criterion, i) => { const label = element('label', `${criterion.label}: ${criterion.criterion}`); const select = element('select'); [0, 1, 2].forEach((n) => { const option = element('option', String(n)); option.value = String(n); select.appendChild(option); }); select.value = String(state.feedback.self_review[i] || 0); label.appendChild(select); feedback.appendChild(label); selects.push(select); });
        const save = element('button', 'Save self-review'); save.type = 'button'; save.addEventListener('click', () => void update({action: 'self_review', scores: selects.map((s) => Number(s.value))})); feedback.appendChild(save);
      }
    }
    const report = get('report'); const details = element('details'); details.appendChild(element('summary', 'Report an issue with this stage'));
    const text = element('textarea'); text.maxLength = 2000; text.setAttribute('aria-label', 'Describe the issue');
    const send = element('button', 'Send for review'); send.type = 'button'; send.addEventListener('click', () => void request('/api/tests/item-events/', {action: 'report', session_id: state.session_id, stage_index: state.stage_index, reason: 'other', detail: text.value})); details.append(text, send); report.appendChild(details);
  };
  root.querySelectorAll('[data-workshop-kind]').forEach((button) => button.addEventListener('click', () => void request(root.dataset.startUrl, {assessment_type: root.dataset.assessment, kind: button.dataset.workshopKind})));
  get('submit').addEventListener('click', () => void update({action: 'answer', answer: readAnswer()}));
  get('draft').addEventListener('click', () => void update({action: 'draft', ...readAnswer()}));
  get('next').addEventListener('click', () => void update({action: 'next'}));
  const sessionId = new URL(window.location.href).searchParams.get('session');
  if (sessionId && /^\d+$/.test(sessionId)) {
    setBusy(true);
    void fetch(`/api/tests/workshops/${sessionId}/`).then(async (response) => { if (!response.ok) throw new Error('Could not resume this session. Choose an exercise to continue.'); state = await response.json(); if (state.assessment_type !== root.dataset.assessment) throw new Error('This session belongs to another assessment. Open it from that assessment workshop.'); render(); }).catch((error) => { get('status').textContent = error.message; }).finally(() => setBusy(false));
  }
})();
