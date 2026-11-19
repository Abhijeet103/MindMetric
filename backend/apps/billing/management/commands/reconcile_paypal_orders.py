"""Settle PayPal checkouts that PayPal reports as paid but we still show as pending.

Run from cron as a safety net behind the return URL and webhooks, e.g. every 10 minutes:
    python manage.py reconcile_paypal_orders --hours 48
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from backend.apps.billing.recruiter_credits import reconcile_pending_credit_orders
from backend.apps.billing.services import paypal_is_configured, reconcile_pending_paypal_orders


class Command(BaseCommand):
    help = "Activate pending PayPal checkouts that PayPal reports as paid."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=48, help="Look back this many hours (default 48).")
        parser.add_argument("--dry-run", action="store_true", help="Report what would change without changing anything.")

    def handle(self, *args, hours, dry_run, **options):
        if not paypal_is_configured():
            self.stdout.write("PayPal is not configured; nothing to do.")
            return
        since = timezone.now() - timedelta(hours=hours)
        outcomes = reconcile_pending_paypal_orders(since=since, dry_run=dry_run)
        if not dry_run:
            outcomes += reconcile_pending_credit_orders(since=since)
        for item in outcomes:
            if item["action"] != "skipped" or options.get("verbosity", 1) > 1:
                self.stdout.write(f"{item['order_id']}: PayPal {item['paypal_status']} -> {item['action']} {item.get('detail', '')}".rstrip())
        settled = sum(1 for item in outcomes if item["action"] in {"activated", "would activate"})
        self.stdout.write(f"Checked {len(outcomes)} pending PayPal checkout(s); {settled} {'would be ' if dry_run else ''}activated.")
