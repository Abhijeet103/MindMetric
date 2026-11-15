from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from backend.apps.pages.models import AdminEmail, AudienceContact


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_URL="https://mindmetric.test",
)
class AdminCampaignTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(email="admin@example.com", password="secret")
        self.admin.audience_contact.unsubscribe()
        self.client.force_login(self.admin)
        self.contact = AudienceContact.objects.create(email="reader@example.com")
        self.other = AudienceContact.objects.create(email="other@example.com")
        self.opted_out = AudienceContact.objects.create(email="unsubscribed@example.com", marketing_opt_in=False)
        self.changelist = reverse("admin:pages_audiencecontact_changelist")
        self.data = {"send_campaign": "1", "subject": "More practice tests", "body": "Visit https://mindmetric.test/"}

    def everyone_url(self, kind="product_update"):
        return reverse("admin:pages_audiencecontact_email_everyone", args=[kind])

    def test_everyone_buttons_and_editable_drafts_do_not_send(self):
        self.assertContains(self.client.get(self.changelist), "Email everyone: updates / new tests")
        updates = self.client.get(self.everyone_url())
        self.assertContains(updates, "https://mindmetric.test/practice/")
        self.assertContains(updates, "Add the new tests")
        feedback = self.client.get(self.everyone_url("feedback_request"))
        self.assertContains(feedback, "https://mindmetric.test/?feedback=open#feedback-modal")
        self.assertEqual(len(mail.outbox), 0)

    def test_everyone_sends_individually_and_records_only_subscribed_contacts(self):
        response = self.client.post(self.everyone_url(), self.data)
        self.assertRedirects(response, self.changelist)
        self.assertEqual({tuple(message.to) for message in mail.outbox}, {
            (self.contact.email,), (self.other.email,),
        })
        self.assertEqual(AdminEmail.objects.count(), 2)
        self.assertEqual(set(AdminEmail.objects.values_list("sent_by_id", flat=True)), {self.admin.pk})
        self.assertTrue(all(message.alternatives for message in mail.outbox))
        for contact in (self.contact, self.other, self.opted_out):
            contact.refresh_from_db()
            self.assertEqual(contact.last_campaign_sent_at is not None, contact != self.opted_out)

    def test_selected_feedback_action_keeps_selection(self):
        selection = {"action": "send_feedback_request", "_selected_action": [self.contact.pk]}
        response = self.client.post(self.changelist, selection)
        self.assertContains(response, "How can we make MindMetric better for you?")
        self.assertFalse(AdminEmail.objects.exists())
        self.client.post(self.changelist, {**selection, **self.data})
        self.assertEqual([message.to for message in mail.outbox], [[self.contact.email]])

    def test_select_across_pagination_survives_confirmation_and_respects_filters(self):
        url = self.changelist + "?source=admin"
        selection = {"action": "send_product_update", "_selected_action": [self.contact.pk], "select_across": "1"}
        response = self.client.post(url, selection)
        self.assertContains(response, 'name="select_across" value="1"')
        self.client.post(url, {**selection, **self.data})
        self.assertEqual(len(mail.outbox), 2)

    def test_update_placeholder_cannot_be_sent(self):
        from backend.apps.pages.emails import campaign_email_initial

        response = self.client.post(self.everyone_url(), {
            "send_campaign": "1", **campaign_email_initial("product_update"),
        })
        self.assertContains(response, "Replace the placeholder")
        self.assertFalse(AdminEmail.objects.exists())

    def test_empty_audience_does_not_open_email_connection(self):
        AudienceContact.objects.update(marketing_opt_in=False)
        with patch("backend.apps.pages.admin.get_connection") as connection:
            response = self.client.post(self.everyone_url(), self.data, follow=True)
        connection.assert_not_called()
        self.assertContains(response, "No subscribed contacts")

    def test_opt_out_after_composing_is_respected(self):
        self.client.get(self.everyone_url())
        self.contact.unsubscribe()
        self.client.post(self.everyone_url(), self.data)
        self.assertEqual([message.to for message in mail.outbox], [[self.other.email]])

    def test_timestamp_opt_out_is_respected(self):
        AudienceContact.objects.filter(pk=self.contact.pk).update(unsubscribed_at=timezone.now())
        self.client.post(self.everyone_url(), self.data)
        self.assertEqual([message.to for message in mail.outbox], [[self.other.email]])

    def test_invalid_draft_does_not_send(self):
        response = self.client.post(self.everyone_url(), {**self.data, "subject": ""})
        self.assertContains(response, "This field is required")
        self.assertContains(response, self.data["body"])
        self.assertFalse(AdminEmail.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_partial_failure_continues_and_only_success_is_logged(self):
        from backend.apps.pages.emails import build_branded_email

        def build(**kwargs):
            message = build_branded_email(**kwargs)
            if kwargs["recipient"] == self.contact.email:
                message.send = lambda **kw: 0
            return message

        with patch("backend.apps.pages.admin.build_branded_email", side_effect=build):
            response = self.client.post(self.everyone_url(), self.data, follow=True)
        self.assertContains(response, "accepted 1 email(s); failed for 1")
        self.assertEqual(AdminEmail.objects.get().recipient, self.other.email)
        self.contact.refresh_from_db()
        self.assertIsNone(self.contact.last_campaign_sent_at)

    def test_connection_failure_keeps_draft_and_does_not_record_success(self):
        with patch("django.core.mail.backends.locmem.EmailBackend.open", side_effect=OSError("SMTP offline")):
            response = self.client.post(self.everyone_url(), self.data)
        self.assertContains(response, "email service failed")
        self.assertContains(response, self.data["body"])
        self.assertFalse(AdminEmail.objects.exists())

    def test_staff_cannot_send_to_everyone_even_with_model_permissions(self):
        staff = get_user_model().objects.create_user(email="staff@example.com", password="secret", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename="change_audiencecontact"))
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.everyone_url(), self.data).status_code, 403)
        self.assertEqual(self.client.post(self.everyone_url("feedback_request"), self.data).status_code, 403)
        self.assertFalse(AdminEmail.objects.exists())

    def test_unknown_campaign_returns_404(self):
        self.assertEqual(self.client.get(self.everyone_url("unknown")).status_code, 404)
