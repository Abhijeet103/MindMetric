// Dependency-free client-flow checks. Run: node scripts/test_recruiter_candidate.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() { this.listeners = {}; this.children = []; this.dataset = {}; this.attributes = {}; this.value = ''; this.checked = false; this.hidden = false; this.textContent = ''; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  async fire(name, event = {}) { for (const callback of this.listeners[name] || []) await callback(event); }
  appendChild(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  setAttribute(name, value) { this.attributes[name] = value; }
  focus() {}
}

async function run() {
  const ids = ['candidate-assessment','candidate-start','candidate-runner','candidate-status','candidate-save-status','candidate-consent','candidate-intro','candidate-context','candidate-question','candidate-options','candidate-question-nav','candidate-progress','candidate-previous','candidate-next','candidate-submit','candidate-timer','candidate-fullscreen'];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const doc = new Element();
  doc.getElementById = id => elements[id];
  doc.querySelector = () => ({value: 'csrf-test-token'});
  doc.createElement = () => new Element();
  elements['candidate-assessment'].dataset.startUrl = '/start/';
  elements['candidate-consent'].checked = false;
  elements['candidate-runner'].requestFullscreen = async () => { doc.fullscreenElement = elements['candidate-runner']; };
  doc.exitFullscreen = async () => { doc.fullscreenElement = null; };
  const win = new Element();
  const requests = [];
  const timeouts = new Map();
  let timerId = 0;
  let submitStatus = 'active';
  let deferredSave = null;
  const context = {
    document: doc, window: win, performance, AbortController,
    setInterval: () => 1, clearInterval: () => {},
    setTimeout: (fn, ms) => { const id = ++timerId; timeouts.set(id, {fn, ms}); return id; },
    clearTimeout: id => timeouts.delete(id),
    confirm: () => true,
    renderContext: () => {}, renderQuestionTable: () => {}, renderCcatSpatialStimulus: () => {},
    renderCcatSpatialOption: (button, item, option) => { button.textContent = option; },
    fetch: async (url, options) => {
      const body = JSON.parse(options.body);
      requests.push({url, body, options});
      if (url === '/start/') return {ok: true, json: async () => ({id:'session', status:'active', url:'/session/', deadline:new Date(Date.now()+60000).toISOString(), server_now:new Date().toISOString(), answers:{}, questions:[{question_text:'Pick one', options:['A','B'], seed:''}, {question_text:'Pick two', options:['C','D'], seed:''}]})};
      if (deferredSave) await deferredSave;
      return {ok:true, json:async () => ({status: body.submit ? 'submitted' : submitStatus})};
    },
  };
  vm.runInNewContext(fs.readFileSync('static/js/recruiter-candidate.js', 'utf8'), context);
  const flush = () => new Promise(resolve => setImmediate(resolve));
  await elements['candidate-start'].fire('click');
  assert.equal(requests.length, 0, 'Consent must precede start');
  assert.match(elements['candidate-status'].textContent, /Acknowledge/);
  elements['candidate-consent'].checked = true;
  await elements['candidate-start'].fire('click');
  assert.equal(requests[0].body.consent, true);
  assert.equal(elements['candidate-options'].children.length, 2);
  assert.match(elements['candidate-progress'].textContent, /Question 1 of 2/);
  await elements['candidate-options'].children[1].fire('click');
  const debounce = [...timeouts.values()].find(item => item.ms === 250);
  await debounce.fn();
  await flush();
  assert.equal(requests.at(-1).body.answers['0'], 'B');
  assert.equal(requests.at(-1).options.headers['X-CSRFToken'], 'csrf-test-token');
  await elements['candidate-next'].fire('click');
  assert.match(elements['candidate-progress'].textContent, /Question 2 of 2/);
  doc.hidden = true;
  await doc.fire('visibilitychange'); await flush();
  assert.ok(requests.some(item => item.body.events?.includes('tab_hidden')));
  let prevented = false;
  await elements['candidate-runner'].fire('paste', {preventDefault: () => { prevented = true; }}); await flush();
  assert.equal(prevented, true);
  assert.ok(requests.some(item => item.body.events?.includes('paste_attempt')));
  await win.fire('pagehide'); await flush();
  assert.equal(requests.at(-1).options.keepalive, true);
  assert.equal(requests.at(-1).body.answers['0'], 'B');

  // A submit while an autosave is in flight must be retried after that save.
  let release;
  deferredSave = new Promise(resolve => { release = resolve; });
  await win.fire('blur');
  await elements['candidate-submit'].fire('click');
  release(); deferredSave = null; await flush();
  const retry = [...timeouts.values()].find(item => item.ms === 1500);
  assert.ok(retry, 'Queued submission is retained');
  await retry.fn(); await flush();
  assert.equal(requests.at(-1).body.submit, true);
  assert.equal(elements['candidate-runner'].hidden, true);
  assert.match(elements['candidate-status'].textContent, /Assessment received/);
  const count = requests.length;
  await win.fire('blur'); await flush();
  assert.equal(requests.length, count, 'Monitoring stops after completion');
  console.log('Recruiter candidate client checks passed: consent, answers, navigation, CSRF, activity logs, unload save, queued submission and completion.');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
