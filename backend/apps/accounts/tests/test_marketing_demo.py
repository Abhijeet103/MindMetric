import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from backend.apps.accounts.management.commands.create_marketing_demo import DEMO_EMAIL
from backend.apps.accounts.models import User
from backend.apps.billing.models import Subscription


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class MarketingDemoTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "demo.json"

    def create(self):
        call_command("create_marketing_demo", credentials_file=self.path, stdout=StringIO())

    def test_account_has_access_without_admin_or_email_and_credentials_are_private(self):
        self.create()
        user = User.objects.get(email=DEMO_EMAIL)
        credentials = json.loads(self.path.read_text())
        self.assertTrue(user.check_password(credentials["password"]))
        self.assertFalse(user.is_staff or user.is_superuser or user.is_tenant_admin)
        self.assertTrue(user.has_active_subscription)
        self.assertTrue(user.is_paid_user)
        self.assertFalse(user.audience_contact.marketing_opt_in)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(mail.outbox), 0)

    def test_rerun_keeps_password_and_does_not_extend_or_duplicate_access(self):
        self.create()
        before = self.path.read_text()
        user = User.objects.get(email=DEMO_EMAIL)
        expiry = user.subscription_expires_at
        self.create()
        user.refresh_from_db()
        self.assertEqual(self.path.read_text(), before)
        self.assertEqual(user.subscription_expires_at, expiry)
        self.assertEqual(Subscription.objects.filter(user=user).count(), 1)

    def test_existing_unmanaged_account_is_untouched(self):
        user = User.objects.create_user(email=DEMO_EMAIL, password="existing-password")
        with self.assertRaisesMessage(CommandError, "refusing to change"):
            self.create()
        user.refresh_from_db()
        self.assertTrue(user.check_password("existing-password"))
        self.assertFalse(self.path.exists())
        self.assertFalse(Subscription.objects.filter(user=user).exists())

    def test_symlink_file_is_rejected(self):
        target = Path(self.directory.name) / "target.json"
        target.write_text("{}")
        self.path.symlink_to(target)
        with self.assertRaisesMessage(CommandError, "symbolic link"):
            self.create()
        self.assertFalse(User.objects.filter(email=DEMO_EMAIL).exists())

    def test_stale_credentials_are_not_replaced(self):
        self.path.write_text(json.dumps({"purpose": "mindmetric-marketing-demo", "user_id": 999}))
        with self.assertRaisesMessage(CommandError, "account is missing"):
            self.create()
        self.assertFalse(User.objects.filter(email=DEMO_EMAIL).exists())
