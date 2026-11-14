# Activation hotfix — 14 November 2026

Local changes only. No production deployment, PayPal configuration change, payment capture, refund, or customer access change was performed.

## Changes

- Retain the existing local CSRF-cookie and snake_case setup-field compatibility fixes in `static/js/site.js`; release both together.
- Practice-save API returns JSON 401 when authentication is missing, instead of redirecting to HTML login.
- Both section-player templates disclose guest practice and offer login with the current page as `next`. Guests do not send saves. Expired sessions and failed saves display a persistent notice; answering can continue. Failed answers are not automatically retried or backfilled, avoiding duplicate increments with the current non-idempotent API.
- `/billing/paypal/webhook/` now invokes the same signature-verified view as `/api/billing/paypal/webhook/`, without a POST redirect. Canonical URL reversing remains unchanged.

## Validation

Run:

```sh
node scripts/check_activation_flows.js
node --check static/js/site.js
DJANGO_SETTINGS_MODULE=backend.config.test_settings python manage.py test backend.apps.billing.tests.test_paypal backend.apps.assessments.tests.test_free_tier_module_limits --noinput
```

Checks cover production CSRF-cookie handling, setup response fields, rejected/redirected/offline saves, persisted authenticated progress, guest JSON 401, both webhook paths rejecting invalid signatures, and duplicate verified delivery preserving subscription expiry. Provider calls are mocked; this does not validate live PayPal credentials or dashboard configuration.

## Release and payment investigation

The checkout contains substantial unrelated unfinished assessment work. Prepare a reviewed release containing only the activation changes; do not run the existing deployment script against all local work merely to release these fixes. That script resets the server to `origin/main`, migrates, collects static files, and restarts services.

After release, verify that the actual rendered page references the new hashed JavaScript produced by `collectstatic`. Test module setup, saved answer progress, completion, and dashboard persistence in a real browser. Verify guest and expired-session notices on desktop and mobile.

Inspect the live PayPal app's webhook configuration, event subscriptions, webhook ID, and the affected order's delivery history. The canonical handler is `https://mindmetric.store/api/billing/paypal/webhook/`; the alias allows deliveries to the previously observed path after deployment. Compare the configured webhook ID with the server setting privately. Reconcile only a provider-confirmed completed capture, and inspect existing manually granted access before applying any activation: the current shared activation service can cancel other active subscriptions. Do not replay events blindly over manual grants.

The reported paid customer needed manual activation. The webhook 404s are a plausible contributor, but they have not been identified as verified deliveries for that order. A browser-return 302 alone does not establish successful activation. Historical unsaved guest practice cannot be reconstructed from aggregate logs.
