"""Provision the synthetic account used for marketing recordings, without sending mail."""
from __future__ import annotations

import json
import os
import secrets
from datetime import timedelta
from pathlib import Path

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from backend.apps.accounts.gifts import grant_one_month_gift
from backend.apps.accounts.models import User
from backend.apps.tenants.models import Tenant

DEMO_EMAIL = "marketing-demo@mindmetric.invalid"


class Command(BaseCommand):
    help = "Create/reuse a non-admin marketing demo account; save credentials privately."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", default=settings.DEFAULT_TENANT_SLUG)
        parser.add_argument(
            "--credentials-file", type=Path,
            default=Path(settings.ROOT_DIR) / ".local" / "marketing-demo.json",
        )

    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(slug=options["tenant"], is_active=True).first()
        if not tenant or not tenant.is_platform_tenant:
            raise CommandError("Choose an active platform tenant for the marketing demo.")
        path = options["credentials_file"].expanduser().absolute()
        if path.is_symlink():
            raise CommandError("The credentials file must not be a symbolic link.")
        credentials = None
        if path.exists():
            try:
                credentials = json.loads(path.read_text())
            except (OSError, ValueError) as error:
                raise CommandError("Cannot read the existing credentials file.") from error
            if not isinstance(credentials, dict) or credentials.get("purpose") != "mindmetric-marketing-demo":
                raise CommandError("The existing file is not a marketing demo credential file.")

        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=DEMO_EMAIL).first()
            created = user is None
            if user is not None:
                if (
                    not credentials or credentials.get("user_id") != user.pk
                    or user.tenant_id != tenant.pk or user.is_staff or user.is_superuser
                    or user.is_tenant_admin or not user.is_active
                    or not user.check_password(credentials.get("password", ""))
                ):
                    raise CommandError("Existing account is not managed by this credential file; refusing to change it.")
            else:
                if credentials is not None:
                    raise CommandError("Credentials exist but their account is missing; refusing to replace them.")
                password = secrets.token_urlsafe(32)
                user = User.objects.create_user(
                    email=DEMO_EMAIL, password=password, tenant=tenant,
                    first_name="MindMetric", last_name="Demo",
                    # This synthetic, non-deliverable identity must not queue a welcome email on login.
                    welcome_email_sent_at=timezone.now(),
                )
                credentials = {
                    "purpose": "mindmetric-marketing-demo", "user_id": user.pk,
                    "email": user.email, "password": password, "tenant": tenant.slug,
                }
            EmailAddress.objects.update_or_create(
                user=user, email=user.email, defaults={"verified": True, "primary": True},
            )
            user.audience_contact.unsubscribe()
            if not user.subscription_expires_at or user.subscription_expires_at <= timezone.now() + timedelta(days=2):
                grant_one_month_gift(user)
            if created:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w") as output:
                    json.dump(credentials, output, indent=2)
                    output.write("\n")
            else:
                path.chmod(0o600)
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Reused'} demo account {user.email} on tenant {tenant.slug}. "
            f"Credentials saved privately to {path}. No email sent."
        ))
