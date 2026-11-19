# Company and role hiring preparation

The `/companies/` page has Company and Role fields with one “Get your prep guide” button. It researches the hiring process and candidate experiences, identifies relevant assessments, and builds a seven-day plan. Signed-in users can request guides when enabled. The backend also supports an optional location and 3-, 7- or 14-day plans.

## Enable

Run migrations, configure these server environment variables, then restart the application:

```dotenv
OPENAI_API_KEY=<server-side project key>
HIRING_RESEARCH_ENABLED=True
HIRING_RESEARCH_MODEL=gpt-6-luna
HIRING_RESEARCH_CACHE_DAYS=7
HIRING_RESEARCH_USER_DAILY_LIMIT=5
HIRING_RESEARCH_SITE_DAILY_LIMIT=100
```

The OpenAI project must have billing, model access and hosted web search enabled. The existing Redis cache must be available. No SDK or additional worker is needed: the service uses the Responses REST API in background mode, saves the provider response ID server-side, and polls while the browser waits. JavaScript is required for live research. Provider calls time out after 20 seconds, browser requests after 25 seconds. Pending reports expire after ten minutes when next checked; upstream work may still finish, but is bounded by tool/output limits. The model is configurable without code changes.

The limits apply to new research runs, not cached results. The site limit uses the existing tenant-scoped cache, so it is per tenant on institution deployments. Each run allows at most five tool calls and 6,500 output tokens, with low reasoning effort. These are usage controls, not a dollar cap; also configure a budget in the OpenAI project. Failed starts count toward daily limits to bound repeated provider failures. Entire guides (stages, experiences, source links, discovered tests and plans) are persisted and reused across users for equivalent company/role/location/day queries within the same tenant for seven days by default, configurable with `HIRING_RESEARCH_CACHE_DAYS`. Company punctuation, case and repeated whitespace are normalized; role punctuation is preserved to distinguish C++ from C#. Concurrent identical requests share the same pending job. Failed reports are retained for a one-minute cooldown. A reload of the saved URL resumes polling or shows the stored report. Without an open browser, provider work continues but the application saves its final output on the next visit.

## Evidence and practice

Research searches official employer information first, then public interview experiences, and can refine its searches. The model returns a strict JSON report. The application validates that format, checks consecutive plan days, and removes hiring stages or experiences without links present in the actual web tool's sources/citation annotations. Inline links are shown beside each finding. This establishes link provenance, not factual entailment: AI summaries and source classifications can still be mistaken. Uncertain findings, missing dates, and role/location differences should appear in the report's uncertainty section. No fallback hiring stages or interview stories are fabricated on provider errors.

Practice keys are restricted to the platform's six existing tracks; the page filters them again against the visitor's available catalogue before constructing internal links. Recommendations are skill preparation, not proof of an employer's assessment vendor. Missing formats such as coding or system design are called out in the coverage note. The plan can contain self-study tasks without platform tests.

Sourced assessment names are matched locally against known aliases and database catalogue entries. Existing accessible tests get a “Use this test” link. Missing tests are automatically saved in the existing `TestSuggestion` model with the company/role context and sources, using `source_page=hiring-research`. A unique discovery key prevents duplicates across guides, users and concurrent requests; normalized existing manual suggestions are reused and their review status is preserved. Automated suggestions have no applicant email and do not create marketing contacts. The normal manual suggestion form still requires an email. This records future test development; it does not publish or generate a new playable test. Catalogue matching runs again on cached guides, so adding a test later updates the links without paying for another research run.

Only the company, role, location, chosen preparation period and public practice catalogue are sent to OpenAI. The provider does not receive user IDs, emails, resumes, tenant records or application deadlines. Search terms and generated public-web reports are persisted in `HiringResearch`; background requests also store data at the provider. Tenant checks apply to status and page reloads. Reports are shared within a tenant when search inputs match; they are not private applicant documents. Do not enter personal applicant information into the search fields. Stale database rows can be removed periodically using the `expires_at` field; cache expiration prevents reuse but does not delete them.

Official API references: [web search](https://developers.openai.com/api/docs/guides/tools-web-search), [background mode](https://developers.openai.com/api/docs/guides/background), [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna).

## Validation

```sh
DJANGO_SETTINGS_MODULE=backend.config.test_settings python manage.py test backend.apps.pages.tests.test_hiring_research backend.apps.pages.tests.test_student_redesign
```

Tests mock the provider; they make no paid API calls. Before enabling in production, run a real company/role search with a configured project, inspect source accuracy and relevance, and check observed cost/latency. Deploying this code alone leaves live research disabled and keeps the curated lookup available.
