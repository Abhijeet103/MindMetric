# Production activation audit — 14 November 2026

Aggregate audit of the PostgreSQL database configured in the workspace and public HTTPS responses from mindmetric.store. Customer figures exclude staff and superusers. Aggregate queries ran inside explicit PostgreSQL `BEGIN READ ONLY` transactions, confirmed with `SHOW transaction_read_only`, and rolled back. No production records, subscriptions, or permissions were changed. No customer identifiers or credentials are included here.

## Observed funnel

| Metric | Count |
| --- | ---: |
| Total accounts, including one staff account | 175 |
| Customer accounts | 174 |
| Customers with recorded practice progress | 6 |
| Customers who started a recorded test | 13 |
| Customers with a completed test | 10 |
| Customers with neither practice progress nor test attempts | 161 |
| Recorded practice questions solved | 154 |
| Test attempts | 14 |
| Completed attempts | 11 |
| Attempts still marked in progress | 3 |
| Customers marked paid | 98 |
| Customers with active admin subscriptions | 97 |
| Customers with active PayPal subscriptions | 1 |
| Customers with a recorded PayPal checkout order | 6 |

All 97 customer admin subscriptions have gift-labelled provider references. Paid access must therefore be separated from purchased subscriptions in reporting. The single active PayPal subscriber has one completed test. Six customers have pending PayPal orders, including the customer who also has a successful order; pending does not itself establish a failed payment. There are 13 customer PayPal subscription/order records in total.

## Signup composition

| Authentication method | Accounts | Any recorded learning | Last login >1 hour after signup |
| --- | ---: | ---: | ---: |
| Email/password | 156 | 2 | 0 |
| Google/social | 18 | 11 | 6 |

All 18 social accounts have verified email records; none of the 156 password accounts does. From 26 October onward, 156 customers registered, and only five started a recorded test. Last-login timestamps are not browsing sessions: a customer can return with an existing authenticated session without updating last_login. These patterns suggest low-intent or automated registrations but do not prove bots. Acquisition source, request logs, IP/device history, and session/page events are unavailable in this audit.

## Confirmed live JavaScript defect

Public GET of `/accounts/login/` sets `__Host-mindmetric_csrf_v2`. Public GET of `/static/js/site.js` returns a helper that only looks up the cookie name passed to it. Test setup, practice progress, and answer-saving code pass `csrftoken`, which differs from the production cookie name.

Executing the actual downloaded helper in Node with a simulated production cookie returns an empty token. Executing the local helper against the same cookie returns the token. Requests relying on that helper therefore lack the required CSRF token in a normal production-cookie-only session and are expected to fail CSRF validation. No authenticated production POST was sent to reproduce a 403, since this audit avoided writes.

This can prevent timed-test creation. Subsequent SSH inspection established that the practice-save endpoint is CSRF-exempt: its observed redirects are caused by missing authentication, so those save failures must not be attributed to this cookie mismatch. Counts of recorded practice must not be interpreted as complete measurements of actual practice. The local fix in `static/js/site.js:getCookie` already handles production, development, legacy cookies, and a hidden form token, but is absent from the live script inspected during this audit.

## Additional flow and measurement issues

- Timed tests require browser fullscreen; unsupported browsers are blocked. The section flow requests fullscreen after awaiting test setup, which may also lose transient user activation. Mobile impact and frequency need browser/device evidence.
- Practice cards lead into practice mode. Reaching a timed section requires a separate mode switch and fullscreen start.
- The configured default login destination is the homepage. Redirects with an explicit next destination can differ. A direct first-practice destination would reduce navigation for users without a next destination.
- Existing analytics code configures consent-based page analytics but has no explicit signup-to-first-answer or test-start-failure events. The database cannot identify which page or error caused abandonment.
- Completed test summary scores exist even though `AttemptAnswer` contains no customer answer rows. Full-test scoring uses other storage, including section payloads/Redis; absence of these rows does not establish zero answers.
- Three old attempts remain in progress. The production schema lacks the newer adaptive/workshop/configuration tables present locally, so local features cannot be assumed to be deployed.

## Priority

1. Release the already-local CSRF helper fix with the normal static deployment/cache refresh, then verify a real first-practice save and timed-test start on desktop and mobile.
2. Make fullscreen optional for ordinary practice tests or provide a supported fallback; retain stricter modes only where needed.
3. Instrument signup, first practice answer, test-start request/success/error, and checkout stages with consent-aware analytics and privacy-conscious server events. Keep gifts, purchased access, and engagement as separate metrics.
4. Assess suspicious registrations using logs before classifying or removing accounts. Add appropriate signup abuse protection without making the first practice unnecessarily difficult.

The available evidence points first to broken activation/tracking and signup quality. It does not establish server latency, question quality, pricing, or lack of demand as the cause. No deployment, account deletion, email campaign, or billing change was performed.

## SSH inspection of 34.199.89.88

Read-only SSH inspection followed with the owner's authorization. No service restart, deployment, load test, production file edit, or production record change was made. HTTP samples were ordinary anonymous GET requests; database probes used read-only transactions. Log results below aggregate requests, not unique customers.

### Resource and latency snapshot

| Observation | Result |
| --- | --- |
| Instance type, verified through instance metadata | t3.small |
| Reported RAM | 1,909 MiB |
| Available RAM | 1,337 MiB |
| CPU sample, five vmstat rows | Approximately 99% idle |
| Root disk | 37% used, approximately 5.1GB available |
| Swap | None |
| Uptime | 117 days |
| Uvicorn workers | 1 |
| Uvicorn resident memory | Approximately 180 MiB |
| App service restarts reported by systemd | 0 since current service activation |
| App service active since | 23 October 2026, 22:56 UTC |
| Kernel OOM matches since 24 October | 0 in retained journal |
| Redis service | redis6.service active; PING successful |
| Redis memory / evictions / rejected connections | Approximately 896 KiB / 0 / 0 |
| Supabase pooler region indicated by configured hostname | us-east-1 |
| Three database connection samples | 18.8–28.1 ms |
| SELECT 1 samples on established connections | Usually 2.3–3.0 ms; first sample 10.6 ms |
| Anonymous app-origin GET samples on localhost | 35.7–66.7 ms across home and practice listing pages |
| Fresh public HTTPS requests from audit workstation | Approximately 1.1–1.4 seconds including network, TLS and body download |

These are light-load point samples, not historical utilisation, regional benchmarks, p95 measurements, or capacity guarantees. Historical CPU-credit balance was not inspected. Present observations do not support CPU, RAM, Redis, or app-to-database distance as the immediate cause of failed test starts. The server has 2GB RAM rather than the previously described t3.micro's 1GB.

### Retained application logs: 24 October to 14 November

- **68 module test-setup POST requests, all HTTP 403; zero successful setup responses.** Four GIA modules were affected. This agrees with the CSRF defect. Access-policy denials can also return 403, so response codes alone cannot attribute every request to CSRF. The downloaded JavaScript independently reproduces an empty token with the actual production cookie name.
- **2,851 practice-save POSTs returned 302; 60 returned 200.** The view is login-required and CSRF-exempt. Retained Nginx logs show practice-module referrers for these redirects. The client follows redirects and does not check response status/content, so the user can see a successful local practice interaction without saved progress. The logs do not distinguish intended guest practice from expired or missing sessions.
- **103 POSTs to `/billing/paypal/webhook/` returned 404**, on 11–12 November in retained Nginx logs. Deployed Django routes place the handler at `/api/billing/paypal/webhook/`. The sender was not authenticated or identified by the available user-agent string, and the PayPal dashboard was not inspected. Confirm the configured provider webhook URL and delivery details before calling these genuine PayPal deliveries or diagnosing lost payments. No successful requests to the correct webhook path were found in the inspected route summaries.
- **166 HTTP 500 responses** mostly concern scanner-like paths such as `/phpmyadmin/`, `/graphql`, and `/.env`; these counts should not be presented as 166 failed tests. No Redis/database exception signatures were found in the checked application journal. Retained Nginx errors include one upstream timeout. Root cause and historical peak conditions were not established.
- Running checkout is **`1a06df3` from 24 October**. The local CSRF fix and newer assessment work are absent from this checkout.

### Additional confirmed frontend/backend mismatch

The deployed `SectionTestSetupView` returns snake_case fields: `attempt_id`, `submit_url`, `progress_url`, and `end_url`. Live `loadTestSetup` reads the camelCase equivalents only. Even after fixing CSRF, this can leave submission/progress URLs and attempt identifiers empty. The local JavaScript already accepts snake_case plus the older camelCase names. Both fixes must be released together and verified through first answer, saved progress, completion, and dashboard display.

Static storage uses manifest-hashed filenames. The live homepage references `/static/js/site.fdd4edb401f9.js`; that actual rendered asset was fetched and independently confirmed to lack both production-cookie support and snake_case submission URL handling. Its bytes differ from the unversioned asset, but both have the defects. Deploy through `collectstatic` and ensure rendered pages reference the new hashed asset; checking the unversioned asset alone is insufficient release verification.

### Return-activity cross-check

`TenantUser.last_seen_at` is a better supplementary measure than `User.last_login`, because existing sessions do not update last_login. Of 156 password users, one has authenticated activity more than an hour and more than a day after signup. Of 18 social users, 11 have activity after an hour and four after a day. This reinforces the signup-quality concern while still not proving automation.

### Recommended release order

1. Release and verify the CSRF and response-field compatibility fixes together. Check the *rendered page's hashed JavaScript*, module start, answer save, completion and persisted result; verify desktop and mobile. Do not deploy unrelated unreviewed local work merely to ship the helper.
2. Make guest versus saved practice explicit. Let guests try a short sample, then offer sign-in to retain progress; return structured 401 responses for expired-session API calls and show a recoverable prompt. Never silently treat redirected HTML as a successful save.
3. Verify the webhook URL in the PayPal dashboard against `/api/billing/paypal/webhook/`, inspect verified delivery/event IDs, then assess whether supported reconciliation is needed. Do not mark pending orders paid solely because a callback was missed.
4. Remove mandatory fullscreen from normal learning sessions or offer a functional fallback. Request fullscreen directly from a user gesture when that mode is selected. Keep test time authoritative on the server.
5. Send a new learner directly to a relevant short diagnostic: choose exam, answer a few questions, see useful feedback, then offer a timed test. Preserve explicit login `next` destinations.
6. Add server-side structured outcomes for test-start failures, first answer, completion and checkout; add `$request_time` and `$upstream_response_time` to access logging for real latency distributions. Observe consent requirements for optional client analytics. Report purchased, gifted, anonymous and engaged cohorts separately.
7. Introduce signup abuse protection and verified-email checks with measured friction, based on evidence. Do not delete or label users as bots from inactivity alone.
8. Reassess hosting after these fixes and a controlled load test. A larger VPS may improve cost/headroom, but it cannot resolve the observed authentication, CSRF and response-contract defects.

## Follow-up: owner reports manual activation after a PayPal payment

The owner confirmed that a recent customer paid through PayPal but needed manual admin activation. Consequently, the active PayPal subscription in the database is **not evidence that automatic activation succeeded**.

Read-only follow-up found that the customer with the only active customer PayPal subscription has an earlier pending checkout on 11 November at 07:01 IST and a second subscription/order record created at 07:12 IST. A browser return containing an order token reached `/api/billing/paypal/return/` at 07:14 IST and returned HTTP 302. The active subscription was updated at 17:10 IST, consistent with later administrative intervention; the database does not retain the previous status in that row. There is no matching object-edit admin log establishing the action, and custom admin bulk actions need not create such a log. No raw customer or order identifiers are included here.

The 103 webhook 404s occurred on 11–12 November, overlapping this checkout. This makes the webhook mismatch a strong candidate for a missing automatic activation/recovery path, but it does not prove those requests were authenticated PayPal notifications for this order. HTTP 302 on the browser return also does not establish whether capture/activation succeeded: that view redirects on both success and error. Available billing logs do not provide the outcome.

Before claiming an exact payment root cause, inspect the corresponding PayPal order/capture state and verified webhook delivery details. Correct or support the configured webhook path, verify signatures, preserve idempotent activation, and reconcile only confirmed completed captures while respecting any existing manually granted access. Pending database orders alone are not proof of payment. No provider capture, refund, activation, or subscription write was performed in this follow-up.
