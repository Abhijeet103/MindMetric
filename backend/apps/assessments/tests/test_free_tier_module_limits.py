from django.contrib.auth import get_user_model
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from backend.apps.assessments.models import (
    Attempt,
    AttemptMode,
    AttemptSection,
    FreeTierModuleLimit,
    SectionProgress,
)
from backend.apps.assessments.services import (
    can_start_attempt,
    get_module_free_tier_limits,
    record_practice_progress,
)
from backend.apps.tenants.models import Tenant, TenantType
from backend.apps.tenants.utils import reset_current_tenant_slug, set_current_tenant_slug

User = get_user_model()


class FreeTierModuleLimitTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Limits Platform",
            slug="limits-platform",
            primary_domain="limits.example.com",
            tenant_type=TenantType.PLATFORM,
            allowed_assessments=["prepgia", "ccat"],
        )
        self.user = User.objects.create_user(
            email="free-limits@example.com",
            password="password",
            tenant=self.tenant,
        )
        self.context_token = set_current_tenant_slug(self.tenant.slug)

    def tearDown(self):
        reset_current_tenant_slug(self.context_token)

    def configure(self, section_type, *, practice=3, tests=2):
        return FreeTierModuleLimit.objects.update_or_create(
            tenant=self.tenant,
            assessment_type="prepgia",
            section_type=section_type,
            defaults={
                "practice_question_limit": practice,
                "test_attempt_limit": tests,
            },
        )[0]

    def create_section_attempt(self, section_type):
        attempt = Attempt.objects.create(
            user=self.user,
            tenant=self.tenant,
            assessment_type="prepgia",
            mode=AttemptMode.SECTION,
        )
        AttemptSection.objects.create(
            attempt=attempt,
            tenant=self.tenant,
            section_type=section_type,
            time_limit_seconds=60,
        )
        return attempt

    def test_configured_limits_are_the_source_of_truth(self):
        self.configure("reasoning", practice=4, tests=3)

        limits = get_module_free_tier_limits(self.tenant, "prepgia", "reasoning")

        self.assertEqual(limits.practice_question_limit, 4)
        self.assertEqual(limits.test_attempt_limit, 3)

    def test_module_test_limits_are_counted_independently(self):
        self.configure("reasoning", tests=1)
        self.configure("perceptual_speed", tests=1)
        self.create_section_attempt("reasoning")

        reasoning = can_start_attempt(
            self.user,
            AttemptMode.SECTION,
            assessment_type="prepgia",
            section_type="reasoning",
        )
        perceptual = can_start_attempt(
            self.user,
            AttemptMode.SECTION,
            assessment_type="prepgia",
            section_type="perceptual_speed",
        )

        self.assertFalse(reasoning.allowed)
        self.assertTrue(perceptual.allowed)

    def test_practice_progress_cannot_exceed_configured_limit(self):
        self.configure("reasoning", practice=2)

        progress = record_practice_progress(self.user, "reasoning", solved_increment=2)

        self.assertEqual(progress.practice_questions_solved, 2)
        with self.assertRaises(PermissionError):
            record_practice_progress(self.user, "reasoning")
        self.assertEqual(
            SectionProgress.objects.get(
                tenant=self.tenant,
                user=self.user,
                assessment_type="prepgia",
                section_type="reasoning",
            ).practice_questions_solved,
            2,
        )

    def test_section_page_generates_only_remaining_free_questions(self):
        self.configure("reasoning", practice=3, tests=1)
        record_practice_progress(self.user, "reasoning", solved_increment=1)
        self.client.force_login(self.user)

        response = self.client.get(
            "/practice/prepgia/modules/reasoning/?mode=practice",
            HTTP_HOST=self.tenant.primary_domain,
        )

        self.assertEqual(response.status_code, 200)
        section = response.context["section"]
        self.assertEqual(section["practice_question_total"], 3)
        self.assertEqual(len(section["practice_previews"]), 2)

    def test_assessment_cards_show_admin_configured_values(self):
        self.configure("reasoning", practice=7, tests=4)

        response = self.client.get(
            "/practice/prepgia/",
            HTTP_HOST=self.tenant.primary_domain,
        )

        self.assertEqual(response.status_code, 200)
        reasoning = next(card for card in response.context["sections"] if card["key"] == "reasoning")
        self.assertEqual(reasoning["free_practice_question_limit"], 7)
        self.assertEqual(reasoning["free_test_attempt_limit"], 4)

    def test_guest_practice_save_returns_json_401_without_redirect(self):
        response = self.client.post(
            "/api/tests/practice-progress/",
            data={"section_type": "reasoning"},
            content_type="application/json",
            HTTP_HOST=self.tenant.primary_domain,
        )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("Location", response)
        self.assertIn("Sign in", response.json()["detail"])
        self.assertFalse(SectionProgress.objects.filter(user=self.user).exists())

    def test_authenticated_practice_save_persists_progress(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/tests/practice-progress/",
            data={"section_type": "reasoning", "solved_increment": 1},
            content_type="application/json",
            HTTP_HOST=self.tenant.primary_domain,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["practice_questions_solved"], 1)
        self.assertEqual(SectionProgress.objects.get(user=self.user).practice_questions_solved, 1)

    @override_settings(CSRF_COOKIE_NAME="__Host-mindmetric_csrf_v2")
    def test_module_setup_accepts_production_csrf_cookie_and_returns_save_urls(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        url = "/practice/prepgia/modules/reasoning/test-setup/"
        host = {"HTTP_HOST": self.tenant.primary_domain}
        self.assertEqual(client.post(url, **host).status_code, 403)
        token = "a" * 32
        client.cookies["__Host-mindmetric_csrf_v2"] = token
        attempt = self.create_section_attempt("reasoning")
        with patch("backend.apps.pages.views.get_or_create_section_attempt", return_value=attempt), patch(
            "backend.apps.pages.views.get_section_test_previews", return_value=[{"id": "question-1"}]
        ):
            response = client.post(url, HTTP_X_CSRFTOKEN=token, **host)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["attempt_id"], attempt.id)
        for field in ["submit_url", "progress_url", "end_url"]:
            self.assertTrue(payload[field].startswith("/api/tests/"))
