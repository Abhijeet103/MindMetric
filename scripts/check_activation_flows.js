// Run real client helpers against production cookies and representative API responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/site.js', 'utf8');
const helperStart = source.indexOf('async function savePracticeProgress(');
const helperEnd = source.indexOf('function dismissFlash(', helperStart);
const context = {document: {cookie: '', querySelector: () => null}};
vm.createContext(context);
vm.runInContext(source.slice(helperStart, helperEnd), context);

async function main() {
  for (const name of ['__Host-mindmetric_csrf_v2', 'mindmetric_csrf_v2', 'csrftoken']) {
    context.document.cookie = `other=value; ${name}=token%2Bvalue`;
    assert.equal(context.getCookie('csrftoken'), 'token+value');
  }
  context.document.querySelector = () => ({value: 'masked-form-token'});
  assert.equal(context.getCookie('csrftoken'), 'masked-form-token');
  context.document.querySelector = () => null;
  context.document.cookie = '__Host-mindmetric_csrf_v2=production-token';

  const responses = [
    {ok: true, json: async () => ({practice_questions_solved: 1})},
    {ok: false, status: 401},
    {ok: true, redirected: true},
    {ok: false, status: 403},
    {ok: false, status: 500},
    {ok: true, json: async () => {throw new Error('HTML login page');}},
    {ok: true, json: async () => ({})},
  ];
  for (const [index, response] of responses.entries()) {
    context.fetch = async (url, options) => {
      assert.equal(options.headers['X-CSRFToken'], 'production-token');
      return response;
    };
    const outcome = await context.savePracticeProgress('/save/', {});
    assert.equal(outcome.saved, index === 0);
    assert.equal(Boolean(outcome.authenticationRequired), Boolean(response.status === 401 || response.redirected));
  }
  context.fetch = async () => {throw new Error('offline');};
  assert.equal((await context.savePracticeProgress('/save/', {})).saved, false);

  // Execute the actual setup callback with the backend's snake_case response.
  const start = source.indexOf('  const loadTestSetup = async () => {');
  const end = source.indexOf('\n  const syncPracticeProgress', start);
  Object.assign(context, {
    player: {dataset: {testSetupUrl: '/setup/'}},
    normalizePlayerQuestion: (item) => item,
    fetch: async () => ({ok: true, json: async () => ({
      previews: [{id: 1}], submit_url: '/submit/', progress_url: '/progress/',
      attempt_id: 42, end_url: '/end/', time_limit_seconds: 60,
    })}),
  });
  vm.runInContext('let testSetupLoaded = false, testQuestions = [], timeLimitSeconds = 0, endUrl = "";\n' + source.slice(start, end) + '\nglobalThis.setup = loadTestSetup;', context);
  assert.equal(await context.setup(), true);
  assert.equal(context.player.dataset.submitUrl, '/submit/');
  assert.equal(context.player.dataset.progressUrl, '/progress/');
  assert.equal(context.player.dataset.attemptId, 42);
  assert.equal(context.player.dataset.endUrl, '/end/');
  console.log('Activation flow checks passed: CSRF cookies, setup contract, failed saves.');
}
main().catch((error) => {console.error(error); process.exitCode = 1;});
