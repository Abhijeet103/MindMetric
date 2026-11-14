# Applied practice workshops and quality workflow

Implemented locally, 14 November 2026. These additions address the engineering
and content gaps identified in the competitor audit. Independent expert approval,
pilot calibration and equivalence to a publisher's specific assessment remain
external validation work; the application does not claim them.

## Learner entry points

Every new assessment practice page now has an **Open practice workshop** button:

| Assessment | URL | Available exercises |
|---|---|---|
| SHL-style | `/practice/shl_verify/workshop/` | Assign people to appointment slots; build bars from percentage data; connect the next nodes in an alternating sequence |
| Consulting Problem Solving | `/practice/consulting/workshop/` | Line and stacked-chart analysis; open market sizing; progressive consulting case |
| Critical thinking | `/practice/watson_glaser/workshop/` | Six shared reading passages with five linked questions each, covering every critical-thinking skill |
| Consulting cases | `/practice/consulting_cases/workshop/` | Progressive cases; market sizing; chart interpretation |

Workshop responses use the interaction itself rather than an MCQ substitute:

- The schedule accepts **any** assignment satisfying all stated constraints.
- Chart construction checks the entered counts against the original data, with a
  live bar preview. Sequence tasks accept an ordered path selected from nodes.
- Line and stacked charts include labelled quantities and exact-value tables for
  accessibility. Insight exercises distinguish descriptive evidence from causes.
- Market sizing accepts a numeric estimate and a written assumption chain. It
  presents a worked illustrative estimate and a structure/arithmetic/uncertainty/
  evidence rubric, without imposing a unique speculative answer.
- The progressive case has six stages: analysis structure, current economics,
  newly released proposal, break-even, evidence selection, and recommendation.
  The server sends only the current stage. Later exhibits and answer references
  are unavailable until the learner reaches the relevant stage.
- Written drafts persist, including the numeric part of market estimates.
  Responses lock on submission. Network retries do not create duplicate answers,
  and reload resumes the saved stage using the URL's session identifier.

The central admin practice allowance still applies. A workshop must fit within
its module's configured free/paid session allowance; zero disables new sessions.
A six-stage case requires an allowance of at least six questions. Existing
sessions retain their allowance snapshot. Workshops are learning exercises and
are separate from timed full-test attempts and their scores.

## Writing review and peer feedback

Writing receives no automatic correctness or communication grade. After a
response is submitted, learners see the reference approach and explicit rubric.
They can save 0–2 self-ratings for each criterion. Those ratings are labelled
self-review and never added to the objective raw score.

Tenant administrators with the relevant permissions can open **Learning
sessions** in Django admin, inspect saved work and enter **Review notes**. The
application records the reviewer and timestamp, and the learner sees the notes
on the completed session. Administrators cannot edit a learner's submitted
answers through that form.

A completed session also offers **Create peer review link**. This is an explicit
owner action; the app sends no email or message. The link:

- shares the completed questions, responses, exhibits and rubrics;
- requires a signed-in reviewer associated with the same tenant (or a valid
  active tenant membership), plus current assessment access;
- expires after seven days and can be revoked by the owner;
- binds to the first peer who submits feedback and rejects self-review through
  the peer form;
- stores the token as a hash; the raw link is returned only when created.

Creating a replacement link revokes the previous link. Revocation stops access
while retaining feedback already given for the learner. Peer notes are separate
from administrator notes, self-ratings and objective correctness.

## Recent exposure, reporting and pilot observations

For signed-in learners, delivered items receive scoped receipts. Practice and
normal/adaptive test delivery record issuance separately from an answer; fetching
an item is not evidence it was viewed. New batches prefer items outside the last
200 issuances for that learner, tenant and module. Linked-case signatures ignore
session identifiers, so changing an ID cannot hide a repeated task.

After 60 unsuccessful generation retries, recent-history avoidance relaxes to
keep small banks usable. Within-form exact deduplication and case-group integrity
remain required. This is best-effort repeat reduction, not an unlimited bank or
an exposure-calibrated selection algorithm.

Learners can report wording, key, display or other issues from ordinary question
players and workshops. The API verifies ownership and tenant scope. Workshop
reports can reference only reached stages. Reports appear under **Item reports**
for resolution and reviewer notes.

Practice observations are checked against the server's stored answer key. Timed
answers are recorded through the test engine, not the public practice-observation
endpoint. Accepted observations cannot be rewritten by changing a client answer.
Optional client timing is bounded and labelled as such; it may include idle time
and is not used for scoring. Workshop stage timings are server elapsed time and
can likewise include thinking or idle time.

**Item exposures** includes an admin action to export aggregate answered counts,
correct counts and mean recorded client response times by section. It excludes
learner identifiers from the CSV. These are descriptive pilot observations, not
norms, calibrated item parameters, reliability estimates or publisher scores.

## Editorial review

Migrations create six original linked-passage records under **Editorial reviews**,
all marked **Needs independent review**. They contain 30 linked questions in total.
These passages supplement the generated critical-thinking families; they are not
a professionally validated or version-specific publisher bank.

Run the following management command to populate representative examples for all
61 newly added question families:

```bash
python manage.py refresh_question_reviews
```

The command creates review snapshots at available difficulties, including all four
steps of each case scenario. It never approves content. Re-running unchanged
snapshots preserves review status. Changed snapshots return to needs-review;
withdrawn families stay withdrawn. Representative examples cannot prove that
every possible generated variant has been independently reviewed.

Only a platform superuser can edit the global editorial registry. Approval requires
an identified reviewer and written review notes. The reviewer should independently
solve each example, challenge competing readings and distractors, check units and
assumptions, and document the conclusion. No independent approval was fabricated
as part of implementation.

Approved passage edits are used for new passage sessions. Approval is shown only
when the saved session matches the approved revision. Withdrawing a passage
prevents new use and stops resume of that passage. Withdrawing a template family
removes it from new learner batch/adaptive generation; existing generated timed
forms remain saved and are not rewritten. If all eligible content is withdrawn,
a new form may be unavailable until the administrator restores reviewed content.

## Deployment and validation

Apply migrations through `0022`, refresh the review snapshots and collect static
assets using the environment intended for deployment:

```bash
python manage.py migrate
python manage.py refresh_question_reviews
python manage.py collectstatic --noinput
```

This work applied migrations and review records only to the local SQLite database.
No production database migration or deployment was performed.

The previous India pricing failure is fixed: the free-plan zero-price label uses
the visitor's regional currency independently of a paid plan's administrator-set
currency. It does not change paid prices or submit payments.

Validation covers progressive disclosure, alternate valid schedules, typed-input
validation, immutable answers, draft recovery, quota inheritance, tenant/owner
scope, CSRF, editorial withdrawal/revision handling, peer-link expiry/revocation,
server answer verification and repeat reduction. The Node checks exercise actual
SVG/chart rendering functions, including distinct figures, stacked bars,
zero/negative line values and safe text labels. Browser visual inspection remains
unavailable in the current Work settings.

## Work that still requires external evidence

- Independent subject-matter approval of the 67 review records and broader
  editorial coverage beyond the representative generated samples.
- Pilot responses sufficient to estimate difficulty, discrimination, reliability
  and distractor effectiveness; an appropriate reference population for any norms.
- Verification of a specific publisher/version/office format before claiming a
  faithful simulator. The workshops are original skill exercises and do not
  replicate proprietary interfaces, conversational interviews or publisher scoring.
- Spoken interview coaching and live peer conversation are outside the saved
  written-review workflow. No automated language assessment has been claimed.

Final local verification: **195/195 Django tests pass**, with **72% coverage**.
All ten workshop entries across the four assessment routes passed authenticated
live HTTP/CSRF start checks; temporary QA identities and sessions were removed.
Django checks, migration drift checks, Ruff and diff whitespace checks pass.
Node checks cover 80 case orderings, 36 compound visual questions, the new chart
renderer and CSRF token lookup under custom development/production cookie names.
The shared CSRF helper now prefers the rendered form token and supports the app's
custom cookies, fixing a pre-existing mismatch with the legacy `csrftoken` name.
