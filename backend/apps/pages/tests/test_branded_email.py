from django.test import SimpleTestCase, override_settings

from backend.apps.pages.emails import build_branded_email


class BrandedEmailTests(SimpleTestCase):
    @override_settings(SITE_URL="https://mindmetric.store", STATIC_URL="/static/")
    def test_branding_plain_text_and_escaped_content(self):
        body = "Hello!\n\n<script>alert('test')</script>"
        email = build_branded_email(subject="Help & advice", body=body, recipient="test@example.com")
        self.assertEqual(email.body, body)
        self.assertEqual(email.to, ["test@example.com"])
        html, mime = email.alternatives[0]
        self.assertEqual(mime, "text/html")
        self.assertIn("MindMetric", html)
        self.assertIn("https://mindmetric.store/static/favicons/android-chrome-192x192.png", html)
        self.assertIn("Help &amp; advice", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
