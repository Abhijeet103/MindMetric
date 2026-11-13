(() => {
  const player = document.querySelector('[data-adaptive-player]');
  if (!player) return;
  const find = (name) => player.querySelector(`[data-adaptive-${name}]`);
  let pending = {};
  let busy = false;
  let timer = null;
  const setBusy = (value) => {
    busy = value;
    find('options').querySelectorAll('button').forEach((button) => { button.disabled = value; });
    find('start').disabled = value;
    find('end').disabled = value;
  };
  const render = (state) => {
    find('start').hidden = true;
    find('progress').textContent = `${state.answered} / ${state.total} answered`;
    if (state.complete) {
      if (timer) clearInterval(timer);
      find('question-shell').hidden = true;
      const result = find('result');
      result.hidden = false;
      result.textContent = `Test complete. ${state.score} correct answers. ${state.scoring_note}`;
      state.sections.forEach((section) => {
        const line = document.createElement('p');
        line.textContent = `${section.title}: ${section.correct} correct, ${section.incorrect} incorrect`;
        result.appendChild(line);
      });
      return;
    }
    find('question-shell').hidden = false;
    find('module').textContent = state.module_title;
    const item = normalizePlayerQuestion(state.question);
    renderContext(find('context'), item);
    const question = find('question');
    question.textContent = item.question_text || item.summary;
    renderCcatSpatialStimulus(question, item);
    renderQuestionTable(question, item);
    const memoryTask = item.reveal_mode === 'context_then_question';
    find('context').hidden = false;
    find('question').hidden = memoryTask;
    find('options').hidden = memoryTask;
    find('reveal').hidden = !memoryTask;
    const options = find('options');
    options.replaceChildren();
    options.classList.toggle('ccat-spatial-answer-options', item.context_kind === 'ccat_spatial');
    item.options.forEach((option, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'answer-option';
      renderCcatSpatialOption(button, item, option, index);
      button.addEventListener('click', () => void send({question_index: state.question_index, selected_option: String(option)}));
      options.appendChild(button);
    });
    if (timer) clearInterval(timer);
    const tick = () => {
      const seconds = Math.max(0, Math.ceil((Date.parse(state.deadline) - Date.now())/1000));
      find('timer').textContent = formatSeconds(seconds);
      if (seconds === 0 && !busy) void send({finish: true});
    };
    timer = setInterval(tick, 1000);
    tick();
  };
  const send = async (payload) => {
    if (busy) return;
    pending = payload;
    setBusy(true);
    find('error').hidden = true;
    find('retry').hidden = true;
    try {
      const response = await fetch(player.dataset.advanceUrl, {
        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': player.querySelector('[name=csrfmiddlewaretoken]').value},
        body: JSON.stringify(payload),
      });
      const state = await response.json();
      if (!response.ok) throw new Error(state.detail || 'Could not save the answer.');
      render(state);
      setBusy(false);
    } catch (error) {
      busy = false;
      find('error').textContent = `${error.message} Retry to continue with the same answer.`;
      find('error').hidden = false;
      find('retry').hidden = false;
      // Keep answer controls disabled until the potentially accepted answer is
      // retried. The server deduplicates a retry and rejects answer changes.
    }
  };
  find('reveal').addEventListener('click', () => {
    find('context').hidden = true;
    find('reveal').hidden = true;
    find('question').hidden = false;
    find('options').hidden = false;
  });
  find('start').addEventListener('click', () => void send({}));
  find('retry').addEventListener('click', () => void send(pending));
  find('end').addEventListener('click', () => void send({finish: true}));
})();
