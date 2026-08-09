import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve, reverse

from backend.apps.pages.seo import seo_context
from backend.apps.pages.sitemaps import PublicPageSitemap


@override_settings(
    SITE_URL="https://mindmetric.store",
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class GuidePageTests(SimpleTestCase):
    def setUp(self):
        self.tenant_resolver = patch(
            "backend.apps.tenants.middleware.resolve_tenant_from_host",
            return_value=None,
        )
        self.tenant_resolver.start()
        self.addCleanup(self.tenant_resolver.stop)

    def test_thomas_gia_guide_renders_format_and_modules(self):
        response = self.client.get(reverse("pages:assessment-guide", args=["thomas-gia"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<strong>5</strong>", html=True)
        self.assertContains(response, "<span>timed tests</span>", html=True)
        self.assertContains(response, "30-45 min")
        self.assertContains(
            response,
            reverse("pages:module-guide", args=["thomas-gia", "reasoning"]),
        )
        self.assertContains(response, "Read section guide")

    def test_ccat_guide_renders_official_timing(self):
        response = self.client.get(reverse("pages:assessment-guide", args=["ccat"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "50")
        self.assertContains(response, "15 min")
        self.assertContains(response, "No")

    def test_module_guide_renders_pattern_and_example(self):
        response = self.client.get(
            reverse("pages:module-guide", args=["ccat", "spatial-reasoning"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Typical question pattern")
        self.assertContains(response, "hexagon")
        self.assertContains(response, "Start this module")

    def test_unknown_guides_return_404(self):
        response = self.client.get(
            reverse("pages:assessment-guide", args=["unknown-assessment"])
        )

        self.assertEqual(response.status_code, 404)

    def test_sitemap_contains_assessment_and_module_guides(self):
        locations = [PublicPageSitemap().location(item) for item in PublicPageSitemap().items()]

        self.assertIn("/guides/thomas-gia/", locations)
        self.assertIn("/guides/ccat/spatial-reasoning/", locations)

    def test_assessment_guide_has_article_and_faq_schema(self):
        request = RequestFactory().get("/guides/ccat/")
        request.resolver_match = resolve(request.path)
        schema = json.loads(seo_context(request)["seo_schema_json"])
        schema_types = {item["@type"] for item in schema["@graph"]}

        self.assertIn("Article", schema_types)
        self.assertIn("FAQPage", schema_types)
