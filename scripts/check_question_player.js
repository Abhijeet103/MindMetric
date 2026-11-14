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

// Optional fixtures exercise the real SVG renderer without a browser. Compare
// the actual element tree, including geometry/fill, rather than only item JSON.
if (process.argv[2]) {
  class SvgElement {
    constructor(tag) { this.tag = tag; this.attributes = {}; this.children = []; }
    setAttribute(key, value) { this.attributes[key] = value; }
    append(...children) { this.children.push(...children); }
    appendChild(child) { this.children.push(child); }
  }
  context.document = {createElementNS: (_namespace, tag) => new SvgElement(tag)};
  const svgStart = source.indexOf('function renderCcatSpatialSvg(');
  const svgEnd = source.indexOf('function renderCcatSpatialStimulus(', svgStart);
  vm.runInContext(source.slice(svgStart, svgEnd), context);
  const canonicalSvg = (element) => JSON.stringify({
    tag: element.tag,
    attributes: Object.fromEntries(Object.entries(element.attributes).sort()),
    children: element.children.map(canonicalSvg).sort(),
  });
  const audit = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const fixtures = audit.sections.shl_inductive.visual_fixtures;
  assert.ok(fixtures.length >= 30, 'Expected compound visual fixtures at all three difficulties');
  for (const options of fixtures) {
    const rendered = options.map((option) => canonicalSvg(context.renderCcatSpatialSvg(option)));
    assert.equal(rendered.length, 4);
    assert.equal(new Set(rendered).size, 4, 'All offered figures must render differently');
  }
  console.log(`SVG geometry checks passed (${fixtures.length} compound questions).`);
}

class ChartNode {
  constructor(tag) { this.tag = tag; this.attributes = {}; this.children = []; this.style = {}; this.dataset = {}; this.textContent = ''; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.children.push(child); }
  set innerHTML(_value) { throw new Error('Charts must use text nodes for untrusted labels'); }
}
context.document = {createElement: (tag) => new ChartNode(tag), createElementNS: (_namespace, tag) => new ChartNode(tag)};
const descendants = (node) => [node, ...node.children.flatMap(descendants)];
for (const values of [[100, 80, 130], [-10, 0, 20], [0, 0, 0]]) {
  const chart = context.renderDataChart({type: 'line', title: 'Revenue (£)', labels: ['Jan', 'Feb', 'Mar'], values});
  const nodes = descendants(chart);
  const points = nodes.find((node) => node.tag === 'polyline').attributes.points;
  assert.equal(points.split(' ').length, 3);
  assert.ok(!/NaN|Infinity/.test(points));
  assert.equal(nodes.filter((node) => node.tag === 'circle').length, 3);
  assert.equal(nodes.filter((node) => node.tag === 'tbody')[0].children.length, 3);
}
const stacked = context.renderDataChart({type: 'stacked', title: 'Client mix', labels: ['Before', 'After'], series: [{name: 'Existing', values: [100, 120]}, {name: 'New', values: [400, 320]}]});
const stackedNodes = descendants(stacked);
const bars = stackedNodes.filter((node) => node.tag === 'span');
assert.equal(bars.length, 4);
assert.ok(bars.every((node) => Number.parseFloat(node.style.width) >= 0 && Number.parseFloat(node.style.width) <= 100));
assert.equal(stackedNodes.find((node) => node.tag === 'tbody').children.length, 2);
const maliciousLabel = '<img src=x onerror=alert(1)>';
const safeChart = context.renderDataChart({title: maliciousLabel, labels: [maliciousLabel], values: [2]});
assert.ok(descendants(safeChart).some((node) => node.textContent === maliciousLabel));
console.log('Line, stacked, zero/negative value and safe-label chart checks passed.');

const cookieStart = source.indexOf('function getCookie(name)');
const cookieEnd = source.indexOf('function dismissFlash', cookieStart);
vm.runInContext(source.slice(cookieStart, cookieEnd), context);
for (const name of ['__Host-mindmetric_csrf_v2', 'mindmetric_csrf_v2', 'csrftoken']) {
  context.document = {cookie: `other=x; ${name}=encoded%20token`, querySelector: () => null};
  assert.equal(context.getCookie('csrftoken'), 'encoded token');
}
context.document = {cookie: 'mindmetric_csrf_v2=raw', querySelector: () => ({value: 'masked-form-token'})};
assert.equal(context.getCookie('csrftoken'), 'masked-form-token');
context.document = {cookie: 'example=abc%3Ddef', querySelector: () => null};
assert.equal(context.getCookie('example'), 'abc=def');
console.log('CSRF token lookup checks passed for form, production, development and legacy cookies.');
