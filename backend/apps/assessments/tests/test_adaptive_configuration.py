import json
from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from backend.apps.assessments import services
from backend.apps.assessments.adaptive import advance_adaptive, AdaptiveInputError
from backend.apps.assessments.admin import TestConfigurationAdmin
from backend.apps.assessments.config import ASSESSMENT_CONFIG
from backend.apps.assessments.models import (
    AdaptiveSession,
    AssessmentResource,
    Attempt,
    AttemptMode,
    FreeTierModuleLimit,
    SectionProgress,
    TestConfiguration,
)
from backend.apps.assessments.policies import resolve_test_configuration
from backend.apps.assessments.tests.test_shl_and_quality_release import MemoryRedis
from backend.apps.tenants.models import Tenant, TenantType
from backend.apps.tenants.utils import set_current_tenant_slug, reset_current_tenant_slug
from prepgia.generators import GENERATOR_MAP
from prepgia.consulting_generators import LinkedCaseGenerator


class CentralConfigurationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Central test",
            slug="central-test",
            primary_domain="central.example.com",
            tenant_type=TenantType.PLATFORM,
            allowed_assessments=list(ASSESSMENT_CONFIG),
        )
        self.user = get_user_model().objects.create_user(
            email="central@example.com", password="testing-only", tenant=self.tenant
        )
        self.token = set_current_tenant_slug(self.tenant.slug)
        self.addCleanup(reset_current_tenant_slug, self.token)
        self.client.force_login(self.user)
        self.host = {"HTTP_HOST": self.tenant.primary_domain}
        self.redis = MemoryRedis()
        redis_patch = patch(
            "backend.apps.assessments.services._get_redis_client", return_value=self.redis
        )
        redis_patch.start()
        self.addCleanup(redis_patch.stop)

    def test_global_and_tenant_module_inheritance_and_zero_limits(self):
        global_row = TestConfiguration.objects.get(tenant=None, assessment_type="", section_type="")
        global_row.free_practice_questions = 6
        global_row.module_test_questions = 9
        global_row.save()
        TestConfiguration.objects.create(assessment_type="ccat", free_practice_questions=8)
        TestConfiguration.objects.create(
            tenant=self.tenant, assessment_type="ccat", paid_practice_questions=18
        )
        TestConfiguration.objects.create(
            tenant=self.tenant,
            assessment_type="ccat",
            section_type="ccat_verbal",
            free_practice_questions=0,
        )
        math = resolve_test_configuration(self.tenant, "ccat", "ccat_numerical")
        verbal = resolve_test_configuration(self.tenant, "ccat", "ccat_verbal")
        self.assertEqual(math["free_practice_questions"], 8)
        self.assertEqual(math["paid_practice_questions"], 18)
        self.assertEqual(math["module_test_questions"], 9)
        self.assertEqual(verbal["free_practice_questions"], 0)
        self.assertEqual(
            resolve_test_configuration(self.tenant, "prepgia", "reasoning")[
                "free_practice_questions"
            ],
            6,
        )

    def test_global_edit_is_not_masked_by_old_default_rows(self):
        FreeTierModuleLimit.objects.create(
            tenant=self.tenant, assessment_type="ccat", section_type="ccat_verbal"
        )
        row = TestConfiguration.objects.get(tenant=None, assessment_type="", section_type="")
        row.free_practice_questions = 4
        row.save()
        self.assertEqual(
            services.get_module_free_tier_limits(
                self.tenant, "ccat", "ccat_verbal"
            ).practice_question_limit,
            4,
        )

    def test_admin_validation_counts_and_scope(self):
        for kwargs in [
            {"module_test_questions": 0},
            {"module_time_seconds": 0},
            {"correct_to_increase": 0},
            {"assessment_type": "unknown"},
            {"assessment_type": "ccat", "section_type": "linked_case"},
            {
                "assessment_type": "consulting_cases",
                "section_type": "linked_case",
                "module_test_questions": 5,
            },
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                TestConfiguration(**kwargs).full_clean()
        TestConfiguration(
            tenant=self.tenant,
            assessment_type="consulting_cases",
            section_type="linked_case",
            module_test_questions=8,
        ).full_clean()

    def test_complete_case_rounding_for_global_counts(self):
        row = TestConfiguration.objects.get(tenant=None, assessment_type="", section_type="")
        row.module_test_questions = 9
        row.free_practice_questions = 5
        row.save()
        config = resolve_test_configuration(self.tenant, "consulting_cases", "linked_case")
        self.assertEqual(config["module_test_questions"], 12)
        self.assertEqual(config["free_practice_questions"], 8)

    def test_free_and_paid_pages_and_progress_use_central_counts(self):
        TestConfiguration.objects.create(
            tenant=self.tenant,
            assessment_type="ccat",
            section_type="ccat_numerical",
            free_practice_questions=3,
            paid_practice_questions=7,
            module_test_questions=5,
            module_time_seconds=91,
        )
        url = reverse("pages:assessment-section-detail", args=["ccat", "ccat_numerical"])
        response = self.client.get(url, **self.host)
        self.assertEqual(response.context["section"]["practice_question_total"], 3)
        self.assertEqual(len(response.context["section"]["practice_previews"]), 3)
        self.assertEqual(response.context["section"]["time_limit_seconds"], 91)
        services.record_practice_progress(self.user, "ccat_numerical", solved_increment=3)
        with self.assertRaises(PermissionError):
            services.record_practice_progress(self.user, "ccat_numerical")
        self.user.role = "paid"
        self.user.save(update_fields=["role"])
        with patch("backend.apps.pages.views.has_unlimited_module_access", return_value=True):
            response = self.client.get(url, **self.host)
        self.assertEqual(len(response.context["section"]["practice_previews"]), 7)
        self.assertEqual(response.context["section"]["practice_question_total"], 7)

    def test_normal_attempt_snapshot_and_setup_urls(self):
        row = TestConfiguration.objects.create(
            tenant=self.tenant,
            assessment_type="ccat",
            section_type="ccat_numerical",
            module_test_questions=5,
            module_time_seconds=91,
            test_type="normal",
        )
        url = reverse("pages:assessment-section-test-setup", args=["ccat", "ccat_numerical"])
        response = self.client.post(url, **self.host)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["previews"]), 5)
        self.assertEqual(response.json()["time_limit_seconds"], 91)
        attempt = Attempt.objects.get(pk=response.json()["attempt_id"])
        row.module_test_questions = 20
        row.module_time_seconds = 200
        row.save()
        self.assertEqual(attempt.configuration["module_test_questions"], 5)
        self.assertEqual(attempt.sections.get().time_limit_seconds, 91)
        self.assertEqual(len(self.client.post(url, **self.host).json()["previews"]), 5)

    def test_free_full_limit_is_configurable(self):
        TestConfiguration.objects.create(
            tenant=self.tenant, assessment_type="ccat", free_full_test_attempts=0
        )
        self.assertFalse(
            services.can_start_attempt(self.user, AttemptMode.FULL_TEST, "ccat").allowed
        )
        response = self.client.get("/practice/ccat/", **self.host)
        self.assertEqual(response.context["full_test_attempts_left"], 0)

    def test_admin_queryset_is_tenant_scoped(self):
        other = Tenant.objects.create(
            name="Other",
            slug="other-central",
            primary_domain="other.example.com",
            tenant_type=TenantType.PLATFORM,
        )
        ours = TestConfiguration.objects.create(tenant=self.tenant)
        TestConfiguration.objects.create(tenant=other)
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        request = RequestFactory().get("/admin/")
        request.user = self.user
        config_admin = TestConfigurationAdmin(TestConfiguration, admin.site)
        self.assertEqual(list(config_admin.get_queryset(request)), [ours])

    def test_superuser_can_edit_central_configuration_in_admin(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        row = TestConfiguration.objects.create(
            tenant=self.tenant, assessment_type="ccat", section_type="ccat_numerical"
        )
        url = reverse("admin:assessments_testconfiguration_change", args=[row.pk])
        response = self.client.get(url, **self.host)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Effective settings after inheritance")
        self.assertContains(response, "Normal")
        response = self.client.post(
            url,
            {
                "tenant": self.tenant.pk,
                "assessment_type": "ccat",
                "section_type": "ccat_numerical",
                "free_practice_questions": 4,
                "paid_practice_questions": 15,
                "module_test_questions": 7,
                "test_type": "adaptive",
                "starting_difficulty": "easy",
                "correct_to_increase": 2,
                "incorrect_to_decrease": 1,
                "_save": "Save",
            },
            **self.host,
        )
        self.assertEqual(response.status_code, 302)
        row.refresh_from_db()
        self.assertEqual(row.test_type, "adaptive")
        self.assertEqual(
            resolve_test_configuration(self.tenant, "ccat", "ccat_numerical")[
                "free_practice_questions"
            ],
            4,
        )

    def test_release_preserves_institution_allocation_and_imports_legacy_limits(self):
        institution = Tenant.objects.create(
            name="Institution",
            slug="central-institution",
            subdomain_prefix="central-institution",
            tenant_type=TenantType.INSTITUTION,
            allowed_assessments=["ccat"],
        )
        FreeTierModuleLimit.objects.create(
            tenant=institution,
            assessment_type="ccat",
            section_type="ccat_verbal",
            practice_question_limit=4,
            test_attempt_limit=1,
        )
        migration = import_module(
            "backend.apps.assessments.migrations.0018_seed_configuration_and_consulting_tracks"
        )
        migration.seed(apps, SimpleNamespace(connection=connection))
        institution.refresh_from_db()
        self.assertEqual(institution.allowed_assessments, ["ccat"])
        policy = TestConfiguration.objects.get(
            tenant=institution, assessment_type="ccat", section_type="ccat_verbal"
        )
        self.assertEqual(policy.free_practice_questions, 4)
        self.assertEqual(policy.free_module_test_attempts, 1)
        self.assertTrue(
            AssessmentResource.objects.filter(
                resource_type="historical_practice", rights_status="link_only"
            ).exists()
        )

    def test_all_new_practice_routes_and_external_resources(self):
        for key in ["consulting", "watson_glaser", "consulting_cases"]:
            response = self.client.get(f"/practice/{key}/", **self.host)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Official samples")
            for module in ASSESSMENT_CONFIG[key]["modules"]:
                response = self.client.get(
                    reverse("pages:assessment-section-detail", args=[key, module["key"]]),
                    **self.host,
                )
                self.assertEqual(response.status_code, 200)
                previews = response.context["section"]["practice_previews"]
                self.assertTrue(previews)
                self.assertTrue(all(q["explanation"] for q in previews))
        resource = AssessmentResource(
            title="Unverified past paper",
            assessment_type="consulting",
            url="https://example.com/paper",
            publisher="Example",
            resource_type="licensed_paper",
            rights_status="permission_granted",
        )
        with self.assertRaises(ValidationError):
            resource.full_clean()


class AdaptiveEngineTests(CentralConfigurationTests):
    # Keep this fixture independent of the central suite's tests.
    def create_adaptive(self, section="shl_numerical", count=6, **overrides):
        assessment = "consulting_cases" if section == "linked_case" else "shl_verify"
        TestConfiguration.objects.update_or_create(
            tenant=self.tenant,
            assessment_type=assessment,
            section_type=section,
            defaults={
                "test_type": "adaptive",
                "module_test_questions": count,
                "starting_difficulty": "medium",
                "correct_to_increase": 1,
                "incorrect_to_decrease": 1,
                **overrides,
            },
        )
        return services.get_or_create_section_attempt(
            self.user, section, assessment_type=assessment
        )

    def submit_current(self, attempt, correct=True):
        session = AdaptiveSession.objects.get(attempt=attempt)
        index = len(session.state["answers"])
        q = session.state["questions"][index]
        answer = str(q["correct_answer"]["answer"])
        if not correct:
            answer = next(str(value) for value in q["payload"]["options"] if str(value) != answer)
        return advance_adaptive(
            attempt.id, self.user, {"question_index": index, "selected_option": answer}
        )

    def test_staircase_changes_next_question_and_hides_answers(self):
        attempt = self.create_adaptive()
        response = advance_adaptive(attempt.id, self.user, {})
        self.assertNotIn("correct_answer", response["question"])
        self.assertNotIn("explanation", response["question"])
        self.assertEqual(response["question"]["seed"], "")
        self.submit_current(attempt, True)
        session = AdaptiveSession.objects.get(attempt=attempt)
        self.assertEqual(session.state["questions"][1]["difficulty"], "hard")
        self.submit_current(attempt, False)
        session.refresh_from_db()
        self.assertEqual(session.state["questions"][2]["difficulty"], "medium")
        self.submit_current(attempt, False)
        session.refresh_from_db()
        self.assertEqual(session.state["questions"][3]["difficulty"], "easy")

    def test_retry_resume_locks_answer_and_does_not_duplicate_progress(self):
        attempt = self.create_adaptive(count=2)
        first = advance_adaptive(attempt.id, self.user, {})
        self.assertEqual(first, advance_adaptive(attempt.id, self.user, {}))
        state = AdaptiveSession.objects.get(attempt=attempt).state
        answer = str(state["questions"][0]["correct_answer"]["answer"])
        body = {"question_index": 0, "selected_option": answer}
        next_response = advance_adaptive(attempt.id, self.user, body)
        self.assertEqual(next_response, advance_adaptive(attempt.id, self.user, body))
        changed = next(
            str(x) for x in state["questions"][0]["payload"]["options"] if str(x) != answer
        )
        with self.assertRaises(AdaptiveInputError):
            advance_adaptive(
                attempt.id, self.user, {"question_index": 0, "selected_option": changed}
            )
        result = self.submit_current(attempt, True)
        self.assertTrue(result["complete"])
        self.assertEqual(result["score"], 2)
        self.assertEqual(advance_adaptive(attempt.id, self.user, {})["score"], 2)
        self.assertEqual(
            SectionProgress.objects.get(user=self.user, section_type="shl_numerical").tests_taken, 1
        )
        self.assertEqual(attempt.sections.get().answers.count(), 2)

    def test_deadline_rejects_late_answer(self):
        attempt = self.create_adaptive(count=2)
        advance_adaptive(attempt.id, self.user, {})
        session = AdaptiveSession.objects.get(attempt=attempt)
        session.state["deadline"] = (timezone.now() - timedelta(seconds=1)).isoformat()
        session.save()
        result = self.submit_current(attempt, True)
        self.assertTrue(result["complete"])
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["answered"], 0)

    def test_question_order_and_case_exhibits_stay_together(self):
        attempt = self.create_adaptive(section="linked_case", count=8)
        advance_adaptive(attempt.id, self.user, {})
        ids = []
        for _ in range(8):
            state = AdaptiveSession.objects.get(attempt=attempt).state
            i = len(state["answers"])
            ids.append(state["questions"][i]["payload"]["prompt"]["case_study"]["id"])
            self.submit_current(attempt, True)
        self.assertEqual(len(set(ids[:4])), 1)
        self.assertEqual(len(set(ids[4:])), 1)
        self.assertNotEqual(ids[0], ids[4])

    def test_future_linked_question_cannot_be_answered_early(self):
        attempt = self.create_adaptive(section="linked_case", count=4)
        advance_adaptive(attempt.id, self.user, {})
        state = AdaptiveSession.objects.get(attempt=attempt).state
        answer = state["questions"][3]["correct_answer"]["answer"]
        with self.assertRaises(AdaptiveInputError):
            advance_adaptive(
                attempt.id, self.user, {"question_index": 3, "selected_option": answer}
            )
        self.assertEqual(len(AdaptiveSession.objects.get(attempt=attempt).state["answers"]), 0)

    def test_configuration_snapshot_survives_admin_edits(self):
        attempt = self.create_adaptive(count=3)
        TestConfiguration.objects.filter(tenant=self.tenant, section_type="shl_numerical").update(
            test_type="normal", starting_difficulty="hard", module_test_questions=20
        )
        result = advance_adaptive(attempt.id, self.user, {})
        self.assertEqual(result["total"], 3)
        self.assertEqual(
            AdaptiveSession.objects.get(attempt=attempt).state["questions"][0]["difficulty"],
            "medium",
        )
        self.assertEqual(
            services.get_or_create_section_attempt(self.user, "shl_numerical").id, attempt.id
        )

    def test_api_authorization_csrf_and_invalid_answers(self):
        attempt = self.create_adaptive()
        url = reverse("adaptive-advance", args=[attempt.id])
        self.assertEqual(
            self.client.post(
                url, data=json.dumps({}), content_type="application/json", **self.host
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                url,
                data=json.dumps({"question_index": 0, "selected_option": "not an option"}),
                content_type="application/json",
                **self.host,
            ).status_code,
            400,
        )
        other = get_user_model().objects.create_user(
            email="another-central@example.com", password="testing-only", tenant=self.tenant
        )
        self.client.force_login(other)
        self.assertEqual(
            self.client.post(
                url, data="{}", content_type="application/json", **self.host
            ).status_code,
            404,
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(
            csrf_client.post(
                url, data="{}", content_type="application/json", **self.host
            ).status_code,
            403,
        )

    def test_full_adaptive_flow_and_normal_endpoints_cannot_inject_answers(self):
        TestConfiguration.objects.create(
            tenant=self.tenant,
            assessment_type="shl_verify",
            test_type="adaptive",
            full_test_module_questions=2,
        )
        attempt = services.get_or_create_full_test_attempt(self.user, "shl_verify")
        result = advance_adaptive(attempt.id, self.user, {})
        self.assertEqual(result["total"], 6)
        with self.assertRaises(services.FullTestSessionError):
            services.get_full_test_section_payload(attempt, 0)
        for _ in range(6):
            result = self.submit_current(attempt, True)
        self.assertEqual(result["score"], 6)
        self.assertTrue(result["complete"])
        services.save_attempt_progress(attempt, {"sections": []})
        attempt.refresh_from_db()
        self.assertEqual(attempt.overall_adjusted_score, 6)

    def test_full_test_resume_preserves_snapshot_and_does_not_consume_an_attempt(self):
        policy = TestConfiguration.objects.create(
            tenant=self.tenant,
            assessment_type="shl_verify",
            test_type="adaptive",
            full_test_module_questions=2,
            free_full_test_attempts=1,
        )
        attempt = services.get_or_create_full_test_attempt(self.user, "shl_verify")
        policy.full_test_module_questions = 10
        policy.test_type = "normal"
        policy.save()
        resumed = services.get_or_create_full_test_attempt(self.user, "shl_verify")
        self.assertEqual(resumed.pk, attempt.pk)
        self.assertEqual(
            Attempt.objects.filter(user=self.user, mode=AttemptMode.FULL_TEST).count(), 1
        )
        self.assertEqual(sum(s.question_count for s in resumed.sections.all()), 6)
        response = self.client.get("/practice/shl_verify/full-test/", **self.host)
        self.assertRedirects(
            response,
            reverse("pages:adaptive-test", args=[attempt.id]),
            fetch_redirect_response=False,
        )

    def test_adaptive_finalization_from_admin_is_idempotent_and_keeps_raw_scores(self):
        attempt = self.create_adaptive(count=3)
        advance_adaptive(attempt.id, self.user, {})
        self.submit_current(attempt, True)
        ended = services.finalize_attempt_from_saved_progress(attempt)
        self.assertEqual(ended.status, "completed")
        self.assertEqual(ended.overall_adjusted_score, 1)
        services.finalize_attempt_from_saved_progress(ended)
        self.assertEqual(
            SectionProgress.objects.get(user=self.user, section_type="shl_numerical").tests_taken, 1
        )
        response = self.client.get("/dashboard/", **self.host)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Practice raw score")

    def test_setup_redirect_and_adaptive_page_render(self):
        attempt = self.create_adaptive()
        response = self.client.post(
            reverse("pages:assessment-section-test-setup", args=["shl_verify", "shl_numerical"]),
            **self.host,
        )
        self.assertEqual(
            response.json()["adaptive_url"], reverse("pages:adaptive-test", args=[attempt.id])
        )
        response = self.client.get(response.json()["adaptive_url"], **self.host)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start or resume test")


class NewContentTests(SimpleTestCase):
    def test_linked_calculations_match_exhibits_and_continuity(self):
        for difficulty in ("easy", "medium", "hard"):
            for i in range(80):
                questions = [
                    LinkedCaseGenerator().generate(difficulty, f"case-{i}:{step}")
                    for step in range(4)
                ]
                self.assertEqual(
                    len({q.payload["prompt"]["case_study"]["id"] for q in questions}), 1
                )
                exhibits = [q.payload["prompt"]["data_table"] for q in questions]
                self.assertTrue(all(table == exhibits[0] for table in exhibits))
                for q in questions:
                    self.assertIn(q.correct_answer["answer"], q.payload["options"])
                    self.assertTrue(q.payload["prompt"]["explanation"])

    def test_all_critical_families_have_reviewable_answers_and_reproducible_prompts(self):
        for key in [
            "wg_inference",
            "wg_assumptions",
            "wg_deduction",
            "wg_interpretation",
            "wg_arguments",
            "consulting_evidence",
        ]:
            for difficulty in ("easy", "medium", "hard"):
                for i in range(50):
                    q = GENERATOR_MAP[key].generate(difficulty, f"critical:{i}")
                    self.assertIn(q.correct_answer["answer"], q.payload["options"])
                    self.assertEqual(len(q.payload["options"]), len(set(q.payload["options"])))
                    self.assertTrue(q.payload["prompt"]["explanation"])
                    self.assertEqual(
                        q.payload["prompt"],
                        GENERATOR_MAP[key].generate(difficulty, f"critical:{i}").payload["prompt"],
                    )
