import json

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from backend.apps.pages.models import PortalFeedback

JSON = {"HTTP_ACCEPT": "application/json"}


@override_settings(EMAIL_NOTIFICATIONS_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class FeedbackTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("pages:feedback")

    def post(self, **data):
        payload = {"category": "general", "message": "The timer looks great.", "source_page": "/practice/"}
        payload.update(data)
        return self.client.post(self.url, payload, **JSON)

    def test_popup_is_on_every_page_for_guests_and_users(self):
        for url in ("/", "/pricing/", "/practice/prepgia/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'id="feedback-modal"', html=False)
                self.assertContains(response, "data-feedback-open", html=False)
                self.assertContains(response, 'name="email"', html=False)
        user = get_user_model().objects.create_user(email="student@example.com", password="secret-pass-123")
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.content.decode().count('id="feedback-modal"'), 1)
        self.assertNotContains(response, 'name="email"', html=False)

    def test_guest_needs_an_email_then_feedback_is_saved(self):
        response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["errors"])
        response = self.post(email="guest@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        feedback = PortalFeedback.objects.get()
        self.assertEqual(feedback.email, "guest@example.com")
        self.assertIsNone(feedback.user)

    def test_signed_in_user_uses_account_email(self):
        user = get_user_model().objects.create_user(email="student@example.com", password="secret-pass-123")
        self.client.force_login(user)
        self.assertEqual(self.post(email="other@example.com").status_code, 200)
        feedback = PortalFeedback.objects.get()
        self.assertEqual((feedback.user, feedback.email), (user, "student@example.com"))

    def test_problem_report_keeps_known_context_and_emails_the_team(self):
        context = {"error": "Could not load the full test section.", "page": "/practice/prepgia/full-test/", "browser": "Firefox", "password": "nope"}
        response = self.post(category="issue", email="guest@example.com", context=json.dumps(context))
        self.assertEqual(response.status_code, 200)
        feedback = PortalFeedback.objects.get()
        self.assertEqual(feedback.context["error"], "Could not load the full test section.")
        self.assertNotIn("password", feedback.context)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Could not load the full test section.", mail.outbox[0].body)

    def test_general_feedback_does_not_email(self):
        self.post(email="guest@example.com")
        self.assertEqual(len(mail.outbox), 0)

    def test_honeypot_and_rate_limit(self):
        self.assertTrue(self.post(email="bot@example.com", website="spam.example").json()["ok"])
        self.assertEqual(PortalFeedback.objects.count(), 0)
        statuses = [self.post(email="guest@example.com").status_code for _ in range(8)]
        self.assertEqual(statuses.count(200), 6)
        self.assertEqual(statuses[-1], 429)

    def test_plain_form_post_redirects_back_to_the_page(self):
        response = self.client.post(self.url, {"category": "general", "message": "Nice site", "email": "g@example.com", "source_page": "/pricing/"})
        self.assertRedirects(response, "/pricing/", fetch_redirect_response=False)
        response = self.client.post(self.url, {"category": "general", "message": "Nice site", "email": "g@example.com", "source_page": "https://evil.example/"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
