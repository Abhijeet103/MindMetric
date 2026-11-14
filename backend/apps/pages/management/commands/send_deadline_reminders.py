"""Email students two days before an assessment deadline they saved.

Run once a day, e.g. from cron: `python manage.py send_deadline_reminders`.
Each deadline gets at most one reminder.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone

from backend.apps.pages.emails import build_branded_email
from backend.apps.pages.models import ApplicationDeadline

REMINDER_DAYS_BEFORE = 2


class Command(BaseCommand):
    help = "Send one reminder email per saved application deadline that is two days away."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List reminders without sending them.")

    def handle(self, *args, **options):
        today = timezone.localdate()
        due = ApplicationDeadline.objects.filter(
            due_date__gte=today,
            due_date__lte=today + timedelta(days=REMINDER_DAYS_BEFORE),
            reminder_sent_at__isnull=True,
            user__is_active=True,
        ).select_related("user")
        site_url = settings.SITE_URL.rstrip("/")
        sent = 0
        for deadline in due:
            days = deadline.days_left
            when = "today" if days == 0 else ("tomorrow" if days == 1 else f"in {days} days")
            subject = f"Your {deadline.company} assessment is due {when}"
            body = (
                f"Your online assessment for {deadline.company} is due {when} ({deadline.due_date:%A %d %B}).\n\n"
                "A timed full test now shows whether your pace is ready, and your results will point to one last "
                "section to practice.\n\n"
                f"Open your plan: {site_url}{reverse('pages:dashboard')}#applications\n\n"
                "Good luck.\nMindMetric"
            )
            if options["dry_run"]:
                self.stdout.write(f"Would email {deadline.user.email}: {subject}")
                continue
            if not getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True):
                self.stdout.write("Email notifications are disabled; nothing sent.")
                return
            build_branded_email(subject=subject, body=body, recipient=deadline.user.email).send()
            deadline.reminder_sent_at = timezone.now()
            deadline.save(update_fields=["reminder_sent_at"])
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} reminder(s)."))
