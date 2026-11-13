// Exercise the actual ordering function without requiring a browser runtime.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/site.js', 'utf8');
const start = source.indexOf('function orderMixedQuestions(');
const end = source.indexOf('function renderQuestionTable(', start);
const context = {};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
const sessions = [
  [{id: 'math-1'}, {id: 'math-2'}],
  Array.from({length: 8}, (_, index) => ({id: `case-${index}`, case_study: {id: index < 4 ? 'case-a' : 'case-b'}, source_question_index: index})),
];
const before = JSON.stringify(sessions);
for (let attempt = 1; attempt <= 80; attempt += 1) {
  const ordered = context.orderMixedQuestions(sessions, attempt);
  assert.equal(ordered.length, 10);
  assert.equal(new Set(ordered.map((q) => q.id)).size, 10);
  for (const caseId of ['case-a', 'case-b']) {
    const positions = ordered.map((q, index) => q.case_study?.id === caseId ? index : -1).filter((index) => index >= 0);
    assert.equal(positions.length, 4);
    assert.equal(positions[3] - positions[0], 3, 'A linked case must remain contiguous');
    const indexes = positions.map((index) => ordered[index].source_question_index);
    assert.deepEqual(Array.from(indexes), caseId === 'case-a' ? [0,1,2,3] : [4,5,6,7]);
  }
  assert.equal(JSON.stringify(ordered), JSON.stringify(context.orderMixedQuestions(sessions, attempt)), 'Reload order must be stable');
}
assert.equal(JSON.stringify(sessions), before, 'Ordering must not mutate source sessions');
console.log('Player ordering checks passed (80 attempts).');
