# PrepGIA

PrepGIA is a Django application for Thomas GIA practice with:

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
- Python question generators for all 5 sections
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
