from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from backend.apps.pages.models import AdminEmail, SaleInquiry
from backend.apps.tenants.models import Tenant


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AdminEmailTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(email="admin@example.com", password="secret")
        self.client.force_login(self.admin)
        self.inquiry = SaleInquiry.objects.create(email="sales@example.com", message="Please help")
        self.reply_url = reverse("admin:pages_saleinquiry_reply", args=[self.inquiry.pk])
        self.compose_url = reverse("admin:pages_adminemail_add")
        self.data = {"recipient": "direct@example.com", "subject": "Your enquiry", "body": "Happy to help."}

    def test_composer_sends_and_records_sender(self):
        self.assertContains(self.client.get(self.compose_url), "Send email")
        self.assertFalse(AdminEmail.objects.exists())
        response = self.client.post(self.compose_url, self.data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mail.outbox[0].to, ["direct@example.com"])
        self.assertEqual(AdminEmail.objects.get().sent_by, self.admin)

    def test_reply_uses_inquiry_recipient_and_records_history(self):
        self.assertContains(self.client.get(self.reply_url), "Please help")
        self.assertFalse(AdminEmail.objects.exists())
        response = self.client.post(self.reply_url, self.data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mail.outbox[0].to, [self.inquiry.email])
        self.assertEqual(AdminEmail.objects.get().inquiry, self.inquiry)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, SaleInquiry.Status.CONTACTED)
        self.assertIsNotNone(self.inquiry.contacted_at)
        response = self.client.get(reverse("admin:pages_saleinquiry_change", args=[self.inquiry.pk]))
        self.assertContains(response, "Happy to help.")
        self.assertContains(response, "Reply by email")

    def test_failed_delivery_preserves_message_and_status(self):
        with patch("backend.apps.pages.admin.EmailMessage.send", side_effect=OSError("SMTP failure")):
            response = self.client.post(self.reply_url, self.data)
        self.assertContains(response, "did not confirm sending")
        self.assertContains(response, "Happy to help.")
        self.assertFalse(AdminEmail.objects.exists())
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, SaleInquiry.Status.NEW)
        self.assertIsNone(self.inquiry.contacted_at)

    def test_zero_delivery_is_not_logged_as_sent(self):
        with patch("backend.apps.pages.admin.EmailMessage.send", return_value=0):
            self.assertEqual(self.client.post(self.compose_url, self.data).status_code, 200)
        self.assertFalse(AdminEmail.objects.exists())

    def test_invalid_recipient_does_not_send(self):
        self.data["recipient"] = "invalid"
        self.assertEqual(self.client.post(self.compose_url, self.data).status_code, 200)
        self.assertFalse(AdminEmail.objects.exists())

    def test_staff_cannot_compose_or_access_unscoped_inquiry(self):
        staff = get_user_model().objects.create_user(email="staff@example.com", password="secret", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename="change_saleinquiry"))
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.compose_url, self.data).status_code, 403)
        self.assertEqual(self.client.post(self.reply_url, self.data).status_code, 404)
        self.assertFalse(AdminEmail.objects.exists())

    def test_closed_inquiry_stays_closed_after_reply(self):
        self.inquiry.status = SaleInquiry.Status.CLOSED
        self.inquiry.save()
        self.client.post(self.reply_url, self.data)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, SaleInquiry.Status.CLOSED)

    def test_tenant_staff_can_reply_only_to_own_inquiries(self):
        tenant = Tenant.objects.create(name="School", slug="school", primary_domain="school.example.com")
        staff = get_user_model().objects.create_user(email="tenant@example.com", password="secret", is_staff=True, tenant=tenant)
        staff.user_permissions.add(Permission.objects.get(codename="change_saleinquiry"))
        own = SaleInquiry.objects.create(tenant=tenant, email="own@example.com", message="Own enquiry")
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.reply_url, self.data).status_code, 404)
        response = self.client.post(reverse("admin:pages_saleinquiry_reply", args=[own.pk]), self.data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mail.outbox[0].to, [own.email])
        self.assertContains(self.client.get(reverse("admin:pages_saleinquiry_change", args=[own.pk])), "Happy to help.")
