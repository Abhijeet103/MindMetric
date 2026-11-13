# Assessment quality and expansion audit

Reviewed: 14 November 2026. Scope: local generators, assessment configuration, serialization, player, existing quality tests, seed migrations, and public official assessment information. This is an analysis and implementation proposal; no live question banks or application behavior were changed.

## Recommendation

Improve the existing GIA and CCAT content before expanding the assessment catalogue. Next, build shared numerical data interpretation and deductive reasoning modules, then use them for SHL-style and consulting problem-solving practice. Add business cases after the shared question engine supports linked exhibits and multiple questions per case. Reserve game simulations for a later phase.

Consulting recruitment is not one universal problem-solving test: aptitude tests, linked business cases, games, and behavioural exercises need different interaction and scoring models. Firm, role, office and recruitment cycle must be recorded separately.

## Implementation follow-up

The follow-up request implemented the quality fixes and first expansion in the
workspace: real generator tiers, new vocabulary concepts and fact-based verbal
logic, four-pair GIA perception, reproducible word selection, neutral spatial
prompts, stable glyph outlines, worked feedback with manual progression, semantic
session deduplication, and three independent SHL-style modules. The fixed SHL
practice form has 24 items in 36 minutes, with separate 12-item module tests.

Migrations 0015–0016 add the schema/content and release the track on platform
tenants while retaining institution allocations. They were exercised on disposable
local databases; the configured remote database was not migrated.

Verification: 130 tests run, 129 passing, 64% coverage. The remaining India free-plan
currency-format assertion also fails on an unchanged HEAD checkout under the same
settings. Assessment integration covers generated answers, visual data, hidden test
answers, full-test submission and scoring, free limits and tenant allocation. Lint,
JavaScript syntax, Django system checks and migration drift checks pass. Browser
QA verified a displayed numerical table and worked feedback with manual progression.
The historical findings below describe the state before these changes. Content is
original practice material and still requires empirical difficulty calibration.

## 1. Evidence from the current implementation

Relevant files:

- `prepgia/generators.py`: eight generators, including database-backed GIA word meaning.
- `backend/apps/assessments/config.py`: GIA and CCAT are active; SHL Verify and Watson–Glaser are upcoming placeholders, with routes disabled.
- `backend/apps/assessments/services.py`: question generation and player serialization.
- `static/js/site.js`: mixed CCAT ordering, shape rendering and feedback.
- `backend/apps/assessments/tests/test_question_quality.py` and `test_ccat_question_variation.py`: existing validity and variation checks.

### Generated sample audit

Generated 1,000 medium questions per non-database generator using seeds `audit:0` through `audit:999`. Separately compared easy and hard at the same 100 seeds. Removed question IDs and metadata for the difficulty comparison. For distinct items, compared prompt, answer and sorted options, so changing option order does not count as new content.

The host Python has no Django installed. The isolated sample execution parsed the generator module and omitted only its Django model import; database-backed word meaning was excluded. This validates generated payload properties, not Django integration, browser rendering, psychometric validity or every answer's correctness. The Django test suite was not run.

| Generator | Distinct items / 1,000 | Identical easy/hard content / 100 |
|---|---:|---:|
| GIA reasoning | 998 | 100 |
| GIA perceptual speed | 1,000 | 0 |
| GIA number speed | 1,000 | 0 |
| GIA spatial | 943 | 100 |
| CCAT numerical | 657 | 100 |
| CCAT verbal | 69 | 100 |
| CCAT spatial | 194 | 100 |

No duplicate option values or missing correct-answer values were found in these 7,000 samples. That is a useful structural baseline, but does not establish semantic quality. Name substitutions also inflate GIA reasoning uniqueness; its underlying relationship structure remains narrow.

### Highest priority findings

| Priority | Finding and evidence | Improvement |
|---|---|---|
| P0 | All three CCAT generators ignore difficulty when selecting content and parameters. GIA reasoning and spatial also use difficulty only as a label. | Define real difficulty controls and test them with the same seed. Keep official-format practice distinct from optional advanced drills. |
| P0 | CCAT spatial questions disclose rules: polygon and dot questions give the increment; rotation gives direction; matrix instructions describe row/column rules. These strings are sent to the test player. | Keep task instructions neutral in timed tests. Offer rule hints separately in learning mode and explain the rule after submission. |
| P0 | Shape-cycle questions show only three distinct shapes and ask for a fourth from a claimed repeating cycle. No repeat has yet been demonstrated. | Show enough of the cycle to establish the rule, or replace the family with a constrained, inferable sequence. |
| P0 | The CCAT verbal bank contains only 69 entries across eight families. The 1,000 samples expose 69 underlying items despite answer shuffling. | Expand an editorially reviewed bank and deduplicate by source item and semantic family. |
| P0 | GIA perceptual speed uses four pairs on easy but six on medium/hard, with seven answer options. | Use four pairs and answers 0–4 in an official-style mode; label six-pair exercises as extended drills. |
| P1 | Matrix answers always have internal value `Option 1`. In 91 sampled matrix items this never changes, although their display position is shuffled. | Assign opaque IDs independently of correctness and rendering order. The normal player renders SVGs, so this is a payload-level cue, not evidence that the first visible button is always correct. |
| P1 | Size-growth always asks the same question with answer `Extra large`; bar-growth has only two orientations and answer `4 bars`. | Parameterize starts, changes, directions and distractors; retire families too shallow to provide useful repeated practice. |
| P1 | CCAT category items include geography, electrical units and scientific facts. Cause/effect distractors are often implausible. | Prioritize contextual language reasoning and provided-information logic; remove unrelated trivia and absurd distractors. |
| P1 | Sentence completion can be underconstrained: “The new process should ___ the time required…” can support both reduce and divide in suitable contexts. | Add context that makes one answer defensible; have an independent reviewer challenge every option. |
| P1 | Most generators supply no item-specific explanation. The word-meaning fallback says a category is shared by three words, but GIA has three words total and a related pair. | Add a worked explanation and distractor reasoning per item. Correct the three-word feedback to describe two related words. |
| P1 | GIA word selection uses database `order_by('?')`, independently of its supplied seed, and can fall back to another difficulty. | Select from a stable, versioned candidate list with the seeded RNG; store source item ID and effective difficulty. Add exposure-aware selection. |
| P1 | GIA word seed catalogues repeatedly reuse unrelated odd words such as wallet, helmet and teapot, even for advanced vocabulary. | Make difficulty depend on semantic discrimination, rather than unfamiliar paired words and an obvious everyday object. |
| P2 | CCAT composition is 17 numerical, 17 verbal and 16 spatial; the browser interleaves them in a fixed rotation. | Treat these quotas as the platform's practice blueprint, not an official published distribution. Use a persisted, constrained ordering with coverage and difficulty balance. |

Existing tests cover reproducibility, family coverage, distinct option values, grammar and some spatial invariants. Their variation signatures include option ordering, so their pass thresholds can overstate actual content variety. Extend them with semantic item signatures and independent answer solvers.

## 2. Improve Thomas GIA without changing the skill being practised

The [official Thomas example booklet](https://www.thomas.co/sites/default/files/2021-07/Aptitude%20Example%20Booklet_2021%20V1.pdf) describes five tasks, eight practice examples before each task, two-person comparisons, four letter pairs, three-number distance decisions, three-word odd-one-out decisions and rotated/mirrored symbol comparisons. Existing staged practice and number-distance logic broadly fit that structure.

Recommended work by module:

- **Reasoning:** retain two-person comparisons; deliberately balance positive, reversed and negative wording. Difficulty should change wording and memory demand while retaining the task format. Do not make long consulting logic puzzles part of the GIA mock.
- **Perceptual speed:** preserve four pairs in mocks. Vary confusability and case order. Measure accuracy and response time separately and verify consistent layout on supported screen sizes.
- **Number speed:** keep the current unequal-gap constraint. Balance lower/higher correct answers and introduce closer gap comparisons gradually, rather than just making all numbers larger.
- **Word meaning:** review synonyms, opposites and categorical relations for a clear intended pair. Remove repeated odd-word cues, accidental multiple relations and weak labels. Store a relationship explanation.
- **Spatial:** verify the exact rendered glyph silhouettes under rotations and reflections. Use stable SVG assets to avoid font-dependent differences; test visual equivalence, not only JSON differences.

Do not claim that raw practice performance is an official GIA percentile. Any platform cohort percentile should identify the reference population and minimum sample requirement.

## 3. Improve CCAT quality

[Criteria's candidate guide](https://www.criteriacorp.com/candidates/ccat-prep) confirms 50 questions in 15 minutes, verbal/math-and-logic/spatial content, no calculator and no penalty for wrong answers. Its verbal example has five options, whereas this platform currently uses four throughout; audit format fidelity by family before claiming an exact mock.

Proposed content blueprint:

| Area | Retain | Add or strengthen |
|---|---|---|
| Numerical | Percentages, ratios, work rate, averages, series | Short word problems, multi-step relationships, estimation, independently checked numerical distractors |
| Verbal | Analogies, synonyms/antonyms, contextual completion | Stronger context, matching grammatical form, close but demonstrably incorrect alternatives |
| Logic | Current quantitative foundations | Syllogisms, ordering constraints, conditional reasoning and conclusions from supplied facts |
| Spatial | Rotation, reflection, count and matrix primitives | Uncued rules, richer transformations, enough evidence to infer sequences, visual ambiguity checks |

Every numerical explanation should state the setup, calculation, units and common error. Verbal explanations should state why the intended relationship is strongest. Spatial explanations should point to the changing visual properties.

Suggested release targets, to be validated through a pilot: at least 300 reviewed verbal items; 20 materially distinct quantitative/logic families; zero exact underlying repeats within a full mock; and tracked repeat exposure across recent sessions. These are product targets, not publisher standards.

## 4. Assessments suitable for expansion

Fit and effort below are engineering judgments from the local architecture, not market-demand estimates. Official public information was checked on the review date; older documents remain dated evidence.

| Assessment / audience | Verified public information | Suitable addition | Fit / priority |
|---|---|---|---|
| SHL Verify / graduate and professional aptitude | [SHL G+ factsheet](https://service.shl.com/docs/Verify%20Interactive%20G%20plus%20Factsheet.pdf) describes numerical, deductive and inductive reasoning with adaptive interactive tasks. The linked sheet is dated 2018; confirm current versions before fixing mock timings. | Launch original reasoning drills first; add charts, scheduling and interactive tasks for format-specific mocks. | High skill reuse; medium implementation effort; first expansion. |
| Big Four cognitive practice | [Deloitte UK](https://www.deloitte.com/uk/en/careers/early-careers/early-careers-assessment.html) describes numerical/verbal reasoning alongside behavioural assessment; [PwC UK](https://www.pwc.co.uk/careers/early-careers/apply/hints-tips.html) describes numerical, inductive and deductive reasoning. | Shared data interpretation, verbal and logical practice with firm-specific study guides. | High reuse; first expansion alongside SHL foundations. |
| KPMG UK | [Official apprentice process](https://www.kpmgcareers.co.uk/apprentice/applying-to-kpmg/application-process/) describes timed numerical/logical cognitive assessment plus a separate scenario-based skills assessment. | Cognitive practice first; add scenario coaching with a separate scoring model later. | High cognitive reuse; do not generalize this route to every KPMG role. |
| EY UK | [Official application process](https://www.ey.com/en_uk/careers/students/application-process.) describes immersive rank-order, written/video responses and numerical reasoning where applicable. | Numerical reasoning now; written/video and behavioural practice later. | Good partial fit; full process requires more interaction types. |
| Aon / cut-e assessment families | [Official candidate preparation](https://www.aon.com/en/capabilities/talent-and-rewards/prepare-for-your-online-assessment) includes numerical, verbal and several logical task formats with practice resources. | Add family-specific numerical and logical drills after common foundations. | Medium fit; distinctive interactive formats need dedicated players. No universal consulting-firm mapping established here. |
| Watson–Glaser | [Pearson research summary](https://www.pearson.com/content/dam/one-dot-com/one-dot-com/global/Files/efficacy-and-research/reports/Watson-Glaser_One_Page_Summary.pdf) describes passage/scenario-based critical thinking and assumption/argument/conclusion reporting. | Original passages with careful inference, assumption, deduction, interpretation and argument items. Review the current four-module placeholder before choosing a version-specific taxonomy. | Good MCQ-player fit; high editorial effort; second wave. |
| BCG Online Case Experience | [BCG Mexico](https://careers.bcg.com/global/en/locations/mexico/application-interviews) describes Casey-guided business cases testing problem-solving and analytical skills. | Linked exhibits, commercial calculations, evidence selection and written recommendations. | Strong consulting relevance; needs a case player; second wave. Evidence is office-specific. |
| Bain digital assessment | [Bain Seoul's 2025 FAQ](https://www.bain.com/contentassets/5439dff63ba449c9b2ebcee47eb214bb/2025-summer-_-seoul-ac-recruiting-faqs.pdf) identifies TestGorilla and case skills, critical thinking, numerical reasoning and working with data. | Original business-data and critical-thinking practice; office/cycle-specific guides. | Good shared-skill fit; historical office evidence, not a verified global 2026 provider claim. |
| McKinsey Solve | [Official Solve page](https://www.mckinsey.com/careers/mckinsey-digital-assessment) confirms gamified problem-solving assessment. | Original resource allocation, constraint and multi-stage decision exercises after simulation infrastructure exists. | Relevant audience, low current-player fit; third wave. Avoid unverified claims about current game components. |

Use a generic **Consulting Problem Solving** track for common business mathematics, charts, evidence and recommendations. Provide firm guides as separate entry points into relevant skills. This avoids duplicating a whole question bank for each firm.

Research public descriptions and link official candidate practice resources. Create original exercises with reviewed answers; fetching reference material should not become importing proprietary question banks. McKinsey's old PST should not be the default current product identity when its central careers page promotes Solve.

## 5. How to add these to this codebase

1. **Quality foundation:** fix the findings above; introduce stable item IDs, generator versions, family IDs, explanations, review state and semantic signatures. Retain the existing seed and payload interface.
2. **Shared skills:** build numerical data interpretation, deductive logic and critical reasoning. Reuse authentication, billing, attempts, progress and server-side answer checking. Add real generators and section types before enabling upcoming cards.
3. **Assessment profiles:** configure timing, aids policy, question counts, composition, interaction type and scoring by assessment version. Store firm, region, role, source URL and last verification date in guides. Existing model choices, validation maps, routes and serializer branches also need updates; a new catalogue card alone is insufficient.
4. **Case sessions:** add shared exhibits, linked question groups, MCQ/numeric/free-text responses, stage transitions and a final recommendation rubric. Numeric/MCQ answers can be deterministic; written answers require transparent rubric feedback.
5. **Simulations:** implement state transitions, constraints, action logs and decision-based feedback separately from simple MCQ correctness.

Keep behavioural coaching distinct from aptitude scoring. Work-style preferences should not be presented as having a universal correct answer.

## 6. Question acceptance and release checks

- Independently verify numerical and logical answer keys; validate unique normalized option values and exactly one defensible answer.
- Have a second reviewer challenge wording, assumptions and alternative semantic interpretations.
- Compare semantic signatures, ignoring UUIDs, names where appropriate, option order and superficial text changes.
- Verify that same-seed content is reproducible within a fixed generator/bank version, while difficulty materially affects intended features.
- Test rendered spatial equivalence under transformations, supported devices and fonts. Different JSON is not proof of different appearance.
- Check that timed payloads expose neither answers, explanations, hints nor correctness-correlated internal IDs. Record a neutral user report-item action.
- Pilot items and track correctness, response-time distributions and distractor selection. Use those observations to refine difficulty; do not infer psychometric calibration from generated labels.

## 7. Original example items for the proposed direction

**CCAT-style numerical:** A subscription costs £80. It increases by 25%, then falls by 20%. Final price? £76 / £80 / £84 / £100. **Answer: £80.** £80 × 1.25 × 0.80 = £80. The percentages use different bases.

**GIA word meaning:** cautious / prudent / reckless. **Answer: reckless.** The first two describe care to avoid risk; reckless describes lack of such care. This tests a clear semantic relation rather than recognition of an unrelated object.

**Deductive reasoning:** Every priority order receives a tracking code. No order without a tracking code can be dispatched. Order K is a priority order. Must K already have been dispatched? **Answer: no.** It must have a code, but a code does not guarantee dispatch. Use this distinction to design a formal conclusion question with unambiguous response instructions.

**Consulting mini-case:** A service handles 10,000 jobs monthly, charges £30 per job and incurs £18 variable cost per job plus £80,000 monthly fixed costs. Automation costs an additional £10,000 monthly and reduces variable cost by £3 per job. Volume and prices stay unchanged. What is the monthly profit improvement? £10,000 / £20,000 / £30,000 / £40,000. **Answer: £20,000.** Variable savings are £30,000 less £10,000 incremental cost. Baseline profit is £40,000 and new profit is £60,000. Follow-on questions can test break-even volume and evidence needed before investment.

These are newly authored illustrative items, not publisher questions or a calibrated release bank.

## 8. Implementation follow-up — 14 November 2026

The quality fixes and independent SHL-style practice described above are now
implemented. The initial vocabulary expansion provides 60 concepts and 720 GIA
word combinations; the larger editorial targets in section 3 remain future work.

The next release adds Consulting Problem Solving, five-module Watson–Glaser-style
critical thinking, and BCG/Bain-style linked case practice. Shared tables, bar
charts and case exhibits are rendered in the question player. Four-question
cases stay together in both normal mixed tests and adaptive sessions. The new
questions are original generated exercises with worked explanations; content
tests independently verify case arithmetic and critical-thinking answer rules.
Independent editorial review and pilot calibration remain necessary before
making fidelity or predictive-validity claims.

Central admin configuration now controls free/paid practice-session lengths,
free test allowances, module and full-test composition, timers, and normal or
adaptive delivery. Tenant and module overrides inherit unspecified settings.
Attempts snapshot their configuration. Consulting and linked case tracks default
to adaptive; other tracks retain normal delivery unless configured otherwise.
Adaptive delivery uses configurable correct/incorrect streaks across easy,
medium and hard questions, with durable server-side deadlines and locked answers.
It reports raw practice scores rather than a publisher percentile. This is a
training heuristic, not an IRT-calibrated assessment.

Official reference resources are now stored separately from playable questions,
including current [McKinsey interviewing resources](https://www.mckinsey.com/careers/interviewing),
[Pearson practice tests](https://www.talentlens.com/practice-tests.html),
[BCG case preparation](https://careers.bcg.com/global/en/case-interview-preparation)
and [Bain interviewing guidance](https://www.bain.com/careers/hiring-process/interviewing/).
McKinsey's linked historical PST Practice C is an official practice paper carrying
a 2006 copyright, not a verified actual past exam or current Solve form. No
reusable licensed PYQ bank was established in this review. These resources are
link-only; no publisher questions were imported. Admin records distinguish
link-only resources from material with documented reuse permission.
