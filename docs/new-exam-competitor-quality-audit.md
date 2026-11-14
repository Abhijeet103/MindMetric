# New exam question quality and competitor comparison

Audit date: 14 November 2026. Scope: SHL-style Reasoning, Consulting Problem
Solving, Watson–Glaser-style Critical Thinking and Consulting Case Practice
(12 playable modules). Baseline: local commit `2370026`.

The platform now has broader practice coverage and more defensible answer rules.
It is still a small original skills-practice product. This review does **not**
establish equivalence to official assessments or superiority to commercial prep.

## Evidence and comparison method

Reviewed public provider pages, freely accessible samples and official guidance.
No paid competitor subscription or private item bank was inspected. Competitor
feature statements below describe what their own public material shows; they do
not establish the quality of their whole bank or validate marketing claims.
Questions were not copied or closely paraphrased from those sources.

| Track | Public reference and competitor evidence | Baseline weakness | Implemented change | Remaining gap |
|---|---|---|---|---|
| SHL-style | [SHL G+ factsheet](https://www.shl.com/assets/documents/product-factsheet-verify-g-plus.pdf) describes charts/tables, deduction and visual rules. [JobTestPrep's public sample](https://www.jobtestprep.co.uk/free-shl-test-practice) demonstrates worked numerical, deductive and inductive examples. | One sales-table structure; ordering largely a fully specified chain; many inductive items change a single feature. | Numerical families 6→9, including revenue growth, weighted contribution margin and target profit. Deduction adds partially constrained schedules with only one valid offered option. Induction adds movement plus fill changes, with distractors violating individual rules. | Still MCQ skill drills. No calendar manipulation, interactive chart construction or node-connection player. No publisher scoring model. |
| Consulting Problem Solving | [PrepLounge's drill catalogue](https://www.preplounge.com/en/case-interview-exercises) visibly covers charts, numerical reasoning, break-even, opportunity costs and structuring. [CaseCoach](https://casecoach.com/bcg-mckinsey-bain-case-interview-prep-home-new/) advertises case libraries and drills in structuring, calculation, case maths and chart interpretation. | Maths reused SHL's regional sales table with an added revenue bar chart; evidence had only three recurring scenarios. | Dedicated eight-family business-maths generator: market funnel, break-even, price/volume, capacity/yield, weighted margin, currency, compound growth and opportunity cost. Evidence adds controlled comparisons, alert base rates and displaced contribution. | Only table and bar-chart exhibits. No line/stacked charts, chart-only discovery tasks, open market-sizing estimates or scored structure/communication exercises. |
| Watson–Glaser-style | [Pearson's historical UK practice booklet](https://www.pearsonvue.com/content/dam/VUE/vue/en/documents/clients/phnro/wg_practice.pdf) distinguishes five operations and their directions. [AssessmentDay](https://www.assessmentday.co.uk/watson-glaser-critical-thinking.htm) provides section-specific practice and public tutorials. | Each skill relied on one narrow template. Inference often reduced to a random draw; interpretation lacked its distinct standard; argument alternatives could be irrelevant by inspection. | Three scenario families per skill. Representative surveys and record audits; access/capacity/measurement assumptions; conditional, overlap and exclusion deductions; weighted-rate reversals, causal overreach and scope interpretation; arguments both supporting and opposing proposals. Section instructions and help now distinguish deduction from interpretation. | No independently edited long passage bank or linked passage sessions. Inference rules are deliberately explicit and narrower than the historical booklet's allowance for common knowledge. This is not an exact version-specific mock. |
| BCG/Bain-style cases | [BCG's preparation guidance](https://careers.bcg.com/global/en/case-interview-preparation) emphasises structured reasoning, questions, data analysis and communication; its cases can admit multiple defensible approaches. [Bain's interviewing page](https://www.bain.com/careers/hiring-process/interviewing/) offers case preparation. The CaseCoach/PrepLounge public material above also illustrates the broader practice experience. | Every linked case was automation profit, proposed profit, break-even and recommendation. | Three case scenarios: automation; market entry with forecast capture and cannibalisation; serial-stage capacity with yield, bottlenecks and demand caps. Each retains four linked questions with shared exhibits. Entry ends with evidence selection; capacity ends with a profit-based recommendation. | Four-question MCQ mini-cases, not full interview or chatbot simulations. No spoken/written recommendation rubric, evolving exhibit release, clarification dialogue or peer practice. |

The SHL documents are dated product descriptions (2018 G+ and
[2022 interactive inductive](https://www.shl.com/assets/documents/rebranded-assets/product-factsheet-verify-interactive-inductive.pdf));
these are not evidence that one timing or interaction format applies to every
current SHL invitation. The Pearson booklet is historical. Firm interviews and
online assessments vary by office, role and hiring cycle. No universal BCG/Bain
provider mapping or current exam-paper claim is made here.

## Concrete quality fixes

- Business cases now account explicitly for units, periods, demand caps, yield,
  cannibalisation and unchanged costs. Each step is answerable directly from the
  exhibits, preventing an earlier wrong answer from forcing later errors.
- Numerical distractors target identifiable mistakes: wrong denominators,
  averaging percentages without weights, multiplying an exchange rate in the
  wrong direction, ignoring opportunity cost, and confusing contribution with
  revenue. Duplicate automation distractors were replaced. The common numeric
  option builder can still need a fallback when mistake values coincide;
  distractor selection rates should guide further improvement.
- Interpretation directions use evidence supported beyond reasonable doubt;
  deduction requires a conclusion necessary under every valid interpretation.
  Assumption instructions explain the negation test. Strong arguments can oppose
  a proposal; irrelevant positive arguments are not automatically rewarded.
- SHL schedule exercises now distinguish a valid offered schedule from a uniquely
  determined global order. Hard schedules include non-adjacency constraints.
- The compound visual family requires both position and fill changes. Four frames
  establish the rule; distractors preserve one property while violating another.
  Tests check the SVG geometry produced by the actual renderer.
- New content retains original provenance, generator version 2, explanations,
  deterministic seeded generation and server-side answer checking. Test payloads
  omit explanations, keys and generator metadata. Existing adaptive sessions
  retain already-generated questions; later questions use the deployed generator.

## Reproducible sample results

Used the same 180 seeds at easy/medium/hard: **540 questions per module and 6,480
per version**. The table counts implemented family labels after normalising case
steps; these are template counts, **not** counts of independently reviewed items.

| Module | Families before → after | Distinct exact tasks before → after, out of 540 |
|---|---:|---:|
| SHL numerical | 6 → 9 | 540 → 540 |
| SHL deduction | 4 → 5 | 534 → 520 |
| SHL induction | 11 → 12 | 221 → 220 |
| Consulting maths | 6 → 8 | 540 → 517 |
| Consulting evidence | 3 → 6 | 407 → 460 |
| Short business cases | 1 → 3 | 540 → 480 |
| Inference | 1 → 3 | 532 → 536 |
| Assumptions | 1 → 3 | 333 → 390 |
| Deduction | 1 → 3 | 540 → 352 |
| Interpretation | 1 → 3 | 537 → 441 |
| Arguments | 1 → 3 | 230 → 516 |
| Linked case sessions | 1 → 3 | 540 → 480 |

Both samples had zero failures for the structural checks: offered answer key,
unique normalised options, present explanation, repeatable content/options/keys,
and no keys/explanations/metadata/seed exposed in timed serialisation. Those
checks alone do **not** prove correct or unambiguous content. Separate tests
independently calculate the new maths/case answers, enumerate valid schedules,
verify compound visual rules and verify the weighted-rate reversal.

Exact task diversity falls in several modules. Conversely, replacing numbers or
names can produce a new exact signature without a new reasoning task. Neither
metric demonstrates a larger professionally reviewed bank. Session deduplication
still prevents exact repeats within a generated form; cross-session exposure
control and more substantively different scenarios remain priorities.

Machine-readable results: [question-bank-audit-summary.json](question-bank-audit-summary.json).

Re-run from the repository root with the project environment:

```bash
DJANGO_SETTINGS_MODULE=backend.config.test_settings python scripts/audit_question_bank.py --output /tmp/question-audit.json
node scripts/check_question_player.js /tmp/question-audit.json
DJANGO_SETTINGS_MODULE=backend.config.test_settings python manage.py test backend.apps.assessments.tests.test_competitor_quality_enhancements backend.apps.assessments.tests.test_shl_and_quality_release backend.apps.assessments.tests.test_adaptive_configuration
```

## Priorities identified after the first expansion

1. Independent subject-matter review of every critical-thinking scenario and all
   distractors. Challenge alternative readings before labelling a bank reviewed.
2. Broader original passage and case topics, plus exposure tracking across recent
   sessions. Prioritise semantic variety over changing numbers and company names.
3. Additional chart formats and information-sufficiency exercises; progressively
   disclosed case exhibits and a transparent written-recommendation rubric.
4. Pilot data on response times, correctness, distractor selection and user item
   reports. Refine difficulty using observed evidence rather than numeric size.
5. Separate version-specific format simulators if faithful SHL or firm assessment
   preparation becomes a product commitment. Current adaptive staircase practice
   is a training heuristic, not publisher-calibrated adaptive scoring.

No paid competitor purchase, official question import, production database change
or deployment was performed for this audit.


## Engineering gap resolution follow-up

The [applied practice workshop release](applied-practice-workshops.md) adds the
interactive responses, line/stacked charts, linked passages, progressive exhibits,
saved written recommendations, self/human/peer review, exposure tracking, reporting
and descriptive pilot workflow identified above. The table and sample metrics in
this report record the first expansion; consult the follow-up for current behaviour.

Independent editorial approval and psychometric calibration remain uncompleted
external validation work. The review registry contains 61 family snapshots and six
passages, all initially pending review. Technical test passes do not establish
publisher equivalence, predictive validity or expert approval.
