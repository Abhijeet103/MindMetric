from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from backend.apps.pages.models import AudienceContact, SaleInquiry, TestSuggestion

User = get_user_model()


class AudienceContactTests(TestCase):
    def test_user_and_inquiry_emails_are_collected_once(self):
        user = User.objects.create_user(
            email="Candidate@Example.com",
            password="secret",
            first_name="Ada",
            last_name="Lovelace",
        )
        inquiry = SaleInquiry.objects.create(
            email="candidate@example.com",
            message="I need group access.",
            marketing_opt_in=True,
        )
        TestSuggestion.objects.create(
            email="another@example.com",
            requested_test="Watson-Glaser",
        )

        contact = AudienceContact.objects.get(email="candidate@example.com")
        self.assertEqual(contact.user, user)
        self.assertEqual(contact.full_name, "Ada Lovelace")
        self.assertTrue(contact.marketing_opt_in)
        self.assertEqual(contact.source, AudienceContact.Source.USER_ACCOUNT)
        self.assertEqual(AudienceContact.objects.count(), 2)
        self.assertEqual(inquiry.email.lower(), contact.email)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_campaign_sends_only_to_consented_selected_contacts(self):
        admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="secret",
        )
        subscribed = AudienceContact.objects.create(
            email="subscribed@example.com",
            marketing_opt_in=True,
        )
        unsubscribed = AudienceContact.objects.create(
            email="not-subscribed@example.com",
            marketing_opt_in=False,
        )
        self.client.force_login(admin_user)
        changelist_url = reverse("admin:pages_audiencecontact_changelist")

        response = self.client.post(
            changelist_url,
            {
                "action": "send_marketing_email",
                "_selected_action": [subscribed.pk, unsubscribed.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "subscribed contact selected")

        response = self.client.post(
            changelist_url,
            {
                "action": "send_marketing_email",
                "_selected_action": [subscribed.pk, unsubscribed.pk],
                "send_campaign": "1",
                "subject": "New practice questions",
                "body": "New CCAT questions are available.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["subscribed@example.com"])
        subscribed.refresh_from_db()
        self.assertIsNotNone(subscribed.last_campaign_sent_at)
