# Live hiring-guide scenario checks

Validated on 19 November 2026 using `gpt-6-luna` and hosted web search through the application's real research service, database cache, catalogue matching and report-view context. These checks used live model responses, not provider fixtures.

| Company | Role | Result |
| --- | --- | --- |
| Canonical | Software engineer | General Intelligence Assessment (GIA) matched Thomas GIA (`prepgia`); recommendation, first-day practice link and “Use this test” link present. Personality Profile Analysis and coding formats were saved as missing suggestions. |
| Canonical | Talent acquisition specialist | GIA matched Thomas GIA with recommendation and practice links. The guide explicitly notes that this exact job title was not confirmed and distinguishes the employer's general process from role-specific evidence. |
| Crossover | Software engineer | Criteria Cognitive Aptitude Test (CCAT) matched the existing CCAT track, with recommendation, plan links and “Use this test.” Missing technical formats were saved as suggestions. |
| JPMorgan | Software engineer | Reused the existing coding-focused guide. HackerRank coding assessment remained a missing-test suggestion. The guide did not claim that this role uses CCAT. |
| MindMetric QA Fixture Company 8F3C (deliberately nonexistent) | Software engineer | No sourced stages, interview experiences or assessments; uncertainty stated explicitly and only general preparation advice returned. No tests invented or suggested for development. |

Official ground truth: [Canonical hiring process](https://canonical.com/careers/hiring-process), [Thomas's Canonical case study](https://www.thomas.co/uk/case-study/canonical), [Crossover selection process](https://www.crossover.com/selection-process).

## Defects found and corrected

The initial Canonical engineering result failed to recommend GIA. Search returned the official careers page with `utm_*` query parameters, while the model cited the clean URL. Exact URL comparison incorrectly removed all official stages and the GIA assessment from the guide. Source matching now removes only known analytics parameters and fragments; meaningful parameters such as `role=` remain distinct and cannot be used to substitute a different page.

The catalogue also lacked the name “General Intelligence Assessment (GIA).” Added that alias, Thomas Aptitude/GIA variants and proctored CCAT variants. A sourced assessment that matches an existing track now produces a recommendation and a plan link even when the model omits that track from its separate practice list. These are generic matching fixes, not hardcoded employer-to-test mappings.

The two saved Canonical provider responses were reprocessed with the corrected source checks and matching. No new model searches were purchased to repair those guides.

## Cache and suggestion checks

- Four new research requests were made; JPMorgan was already cached.
- All five repeated requests reused the same saved guide. The recheck replaced the API client with a function that raises if any API call is attempted; all requests passed.
- Canonical also reused its guide with punctuation/case/whitespace variants of the original inputs.
- Repeating each request created zero additional suggestions.
- The two Canonical guides reused one PPA suggestion. Known GIA and CCAT tracks were not added as missing tests.
- Full guides remain reusable for seven days by default, including findings, sources, assessment names and plans.

## Automated validation

105 page tests pass. New regressions cover tracked-versus-clean source URLs, retention of meaningful query parameters, GIA name variants, proctored CCAT matching, and generation of the existing practice links when the model omits its recommendation.

These scenarios check specific live outputs and matching behavior. They do not guarantee identical model results for every role, location or future hiring process. Each guide retains its sources and uncertainty notes.

## Additional live missing-test scenario: P&G

A fresh Procter & Gamble / Brand manager guide identified two assessments absent from the catalogue and automatically created `TestSuggestion` records:

| Missing assessment | Record | Status | Source |
| --- | --- | --- | --- |
| P&G Peak Performance Assessment | 7 | New | hiring-research |
| P&G Interactive Assessment | 8 | New | hiring-research |

Both records contain the [official P&G hiring-process source](https://www.pgcareers.com/global/en/hiring-process). The rendered guide shows that the assessments were saved for future development. Exactly one new AI search was used; a repeated request reused the cached guide and added zero suggestions. The tests were queued for development rather than published as playable tracks.

A dedicated automated regression also passes: it saves both missing assessments, keeps Peak Performance separate from the existing Personality Profile Analysis (both may be abbreviated PPA), preserves the source links, and verifies no duplicate suggestions or extra model calls on a repeat request.
