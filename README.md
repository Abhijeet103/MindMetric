# PrepGIA

PrepGIA is a Django application for Thomas GIA, CCAT and independent SHL-style reasoning practice with:

- Django views and templates
- Django static assets in `static/css` and `static/js`
- SQLite database
- Python question-generation pipeline

## Current scope

- Django app skeleton with role-based user model
- Google OAuth-ready authentication flow via `django-allauth`
- Free and paid access model
- One-time full test rule for free users
- Section-wise test support
- Django SEO-friendly server-rendered pages
- SQLite database schema
- Python question generators for the five GIA sections, three CCAT modules and three SHL-style reasoning modules
- Export pipeline from SQLite into JSON for question previews

## Project structure

- `backend/`: Django project config and apps
- `templates/`: Django templates
- `static/`: CSS and JS assets
- `lib/`: shared question preview helpers
- `prepgia/schema.py`: SQLite schema and seed helpers
- `prepgia/generators.py`: question generation logic
- `scripts/init_db.py`: database initialization
- `scripts/generate_questions.py`: sample question generation and persistence
- `scripts/export_questions.py`: export generated questions for Next.js consumption

## Django backend

Install backend dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

Run Django:

```bash
PYTHONPATH=. .venv/bin/python manage.py runserver
```

Run the automated checks used in CI:

```bash
DJANGO_SETTINGS_MODULE=backend.config.test_settings .venv/bin/python manage.py check
DJANGO_SETTINGS_MODULE=backend.config.test_settings .venv/bin/coverage run manage.py test
.venv/bin/coverage report
```

`requirements.txt` is the hashed production lockfile. Change dependencies only
in `requirements.in`, then regenerate it with:

```bash
.venv/bin/pip-compile --generate-hashes --output-file requirements.txt requirements.in
```

Copy environment variables first:

```bash
cp .env.example .env
```

Important backend endpoints:

- `/accounts/google/login/`
- `/api/auth/session/`
- `/api/auth/google/`
- `/api/billing/status/`
- `/api/billing/checkout/weekly/`
- `/api/billing/stripe/webhook/`
- `/api/tests/sections/`
- `/api/tests/attempts/start/`

## Python data pipeline

Initialize the database:

```bash
PYTHONPATH=. .venv/bin/python scripts/init_db.py
```

Generate sample questions:

```bash
PYTHONPATH=. .venv/bin/python scripts/generate_questions.py --section all --difficulty easy --count 3
```

Export questions for the Next app:

```bash
PYTHONPATH=. .venv/bin/python scripts/export_questions.py
```

## Django pages

Useful routes:

- `/`
- `/practice`
- `/sections`
- `/sections/reasoning`
- `/login`
- `/pricing`
- `/dashboard`

## SEO direction

The Django page structure is set up to support:

- server-rendered marketing pages
- route-level metadata
- section-specific landing pages
- keyword-focused information architecture
- later addition of sitemap, robots, and structured data

## Access rules

- Every new user starts as `free`
- Free users can take the full test only once
- Free users can use section-wise tests
- Paid users can take unlimited full tests
- Paid users can take unlimited section-wise tests
- After purchase, the backend upgrades the role from `free` to `paid`

## Razorpay setup

Add these values to `.env`:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- `RAZORPAY_ENABLED` (set to `True` to enable Razorpay; defaults to `False`)
- `STRIPE_ENABLED` (set to `True` to enable Stripe; defaults to `False`)

In Razorpay Dashboard, enable international payments and add a webhook for
`payment.captured` pointing to:

`https://mindmetric.store/api/billing/razorpay/webhook/`

MindMetric supports USD, INR, EUR, GBP and CHF storefront prices. Prices are
managed in Django admin; the initial migration creates INR pricing for India and
CHF pricing for Switzerland. Confirm that international payments are activated
on the Razorpay account before accepting live USD, EUR, GBP or CHF payments.
## Production HTTPS on EC2

This repo includes nginx and Certbot deployment helpers in [`deploy/`](./deploy):

- [`deploy/mindmetric.conf`](./deploy/mindmetric.conf)
- [`deploy/setup_certbot_nginx.sh`](./deploy/setup_certbot_nginx.sh)
- [`deploy/SSL_CERTBOT_EC2.md`](./deploy/SSL_CERTBOT_EC2.md)

Recommended production env values after SSL is live:

```env
DJANGO_ALLOWED_HOSTS=mindmetric.store,www.mindmetric.store,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://mindmetric.store,https://www.mindmetric.store
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
```

Keep these disabled until the certificate is successfully installed and nginx is serving HTTPS.

## Assessment quality and SHL-style practice

The assessment catalogue includes independent SHL-style numerical, deductive and
inductive reasoning at `/practice/shl_verify/`. Each module offers original
questions, worked explanations and timed practice. The mixed practice form has
24 questions in 36 minutes; it is a fixed form, not an official adaptive SHL test.
Numerical practice includes business-data tables and allows a calculator.

GIA retains four letter pairs at every difficulty. CCAT now uses difficulty tiers,
contextual vocabulary and stated-information logic, neutral spatial prompts and
session deduplication. Practice feedback stays visible until **Next question**.

When deploying this change, run migrations and rebuild the served static assets:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

Migrations 0015 and 0016 add the module choices and word explanations, replace
specific old seed items with semantic pairs, and enable SHL-style practice on
platform tenants. Institution allocations and administrator-authored word items
are retained. Institutions can enable the new track through the existing tenant
admin assessment controls. Existing active Redis test sessions should finish or
expire before rollout; generation changes apply to new question batches.

Vocabulary content currently contains 60 concepts across three difficulty tiers;
GIA uses 720 combinations of those pairs with unrelated odd words. These are
practice materials, not a psychometrically calibrated item bank.

## Central question limits and adaptive practice

Use **Admin → Assessments → Test configurations**
(`/admin/assessments/testconfiguration/`) to manage practice allowances, test
question counts, timers and **Normal / Adaptive** test type. Blank fields inherit
their values. The saved row displays its effective settings for review.

- Leave tenant, assessment and module blank for a platform-wide default.
- Select an assessment to override its defaults; select a module for finer control.
- Select a tenant for institution-specific overrides. Tenant settings take
  precedence over platform settings, with module settings most specific within
  each scope. Institution administrators can edit only their own tenant.
- **Free practice questions** and **Paid practice questions** control the number
  per practice session. Free module/full-test attempts are separate allowances;
  zero disables the corresponding free allowance.
- **Module test questions** sets a standalone module's length. **Full test module
  questions** sets each module's contribution to a full test. Full-test type and
  total timer use the assessment-level settings; module overrides can set their
  adaptive difficulty rules. Warm-up counts apply to normal staged tests.

For example, set the global row's free practice count to `5`, then add a CCAT row
with test type **Adaptive** to enable adaptive CCAT tests. Existing attempts keep
their saved configuration. Linked cases contain four questions; shared counts
round up to complete cases, and explicit case-module counts must be multiples of
four.

Adaptive tests serve one question at a time and lock accepted answers. By default,
two consecutive correct answers increase difficulty and one incorrect answer
decreases it. Starting difficulty and both thresholds are configurable. Each
module adapts separately; linked cases keep their difficulty and exhibit for all
four questions. The server persists the deadline and progress across reloads.
Results are raw practice scores, with no publisher percentile or IQ estimate.

New independent practice tracks are available at:

- `/practice/consulting/`: charts, business mathematics, evidence evaluation and
  short cases; adaptive by default.
- `/practice/watson_glaser/`: inference, assumptions, deduction, interpretation
  and argument evaluation; normal by default, optionally adaptive.
- `/practice/consulting_cases/`: BCG/Bain-style linked business cases with shared
  exhibits and four-question sequences; adaptive between cases by default.

Run migrations through `0018` and collect static assets before deployment.
Existing custom free-tier limits are carried into the central settings. Platform
tenants receive the new tracks; institution allocations remain administrator
controlled. Official resources are managed under **Assessment resources** and
linked from the relevant practice page. All playable new questions are original.
The historical McKinsey PST resource is an official practice paper, not a verified
previous-year exam paper or a representation of current Solve. Publisher
questions have not been copied into the bank.

Validation includes `python manage.py test
backend.apps.assessments.tests.test_adaptive_configuration` and
`node scripts/check_question_player.js` for case continuity and ordering.
