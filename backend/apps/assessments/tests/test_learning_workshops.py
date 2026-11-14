import itertools
import json
from dataclasses import asdict
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, SimpleTestCase, Client
from django.urls import reverse
from backend.apps.assessments.config import ASSESSMENT_CONFIG
from backend.apps.assessments.learning import (
    start_workshop,
    update_workshop,
    session_payload,
    check_answer,
)
from backend.apps.assessments.models import (
    EditorialReview,
    ItemExposure,
    ItemReport,
    TestConfiguration,
)
from backend.apps.assessments.quality import (
    issue_question,
    resolve_receipt,
    observe_answer,
    item_signature,
)
from backend.apps.assessments.services import _build_question_batch
from backend.apps.tenants.models import Tenant, TenantType
from backend.apps.tenants.utils import set_current_tenant_slug, reset_current_tenant_slug
from prepgia.generators import GENERATOR_MAP
from prepgia.learning_content import WORKSHOPS, make_workshop
from prepgia.passage_bank import PASSAGES


class WorkshopContentTests(SimpleTestCase):
    def test_all_workshops_have_valid_objective_answers_and_meaningful_rubrics(self):
        for assessment, kinds in WORKSHOPS.items():
            for kind, _ in kinds:
                for i in range(20):
                    content = make_workshop(kind, f"workshop:{i}")
                    self.assertTrue(content["stages"])
                    for stage in content["stages"]:
                        if stage["kind"] == "schedule":
                            valid = [
                                list(p)
                                for p in itertools.permutations(stage["options"])
                                if check_answer(stage, list(p))[1]
                            ]
                            self.assertGreater(len(valid), 1)
                            self.assertLess(len(valid), 24)
                        elif stage["kind"] in {"written", "estimate"}:
                            self.assertGreaterEqual(len(stage["rubric"]), 2)
                            _, score = check_answer(
                                stage,
                                {
                                    "text": "My reasoned answer discusses assumptions and supporting evidence.",
                                    "estimate": 1000,
                                },
                            )
                            self.assertIsNone(score)
                        else:
                            _, score = check_answer(stage, stage["answer"])
                            self.assertTrue(score)

    def test_original_passages_have_five_distinct_skills_and_consistent_keys(self):
        self.assertEqual(len({p["key"] for p in PASSAGES}), 6)
        for passage in PASSAGES:
            self.assertGreater(len(passage["body"].split()), 120)
            self.assertEqual(
                {q["skill"] for q in passage["items"]},
                {"inference", "assumptions", "deduction", "interpretation", "arguments"},
            )
            for item in passage["items"]:
                self.assertIn(item["answer"], item["options"])
                self.assertTrue(item["explanation"])

    def test_numeric_and_interactive_validation_rejects_malformed_values(self):
        for answer in ("NaN", "Infinity", "", None, True, 1e20):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                check_answer({"kind": "numeric", "answer": 2}, answer)
        schedule = make_workshop("schedule", "constraints")["stages"][0]
        with self.assertRaises(ValueError):
            check_answer(schedule, [schedule["options"][0]] * 4)
        path = make_workshop("node_path", "sequence")["stages"][0]
        with self.assertRaises(ValueError):
            check_answer(path, path["answer"] + ["invalid"])

    def test_case_signatures_ignore_session_ids_but_keep_exhibit_content(self):
        question = asdict(GENERATOR_MAP["linked_case"].generate("medium", "same:0"))
        changed = json.loads(json.dumps(question))
        changed["payload"]["prompt"]["case_study"]["id"] = "a-different-session-id"
        self.assertEqual(item_signature(question), item_signature(changed))
        changed["payload"]["prompt"]["data_table"]["rows"][0][1] += 1
        self.assertNotEqual(item_signature(question), item_signature(changed))


class WorkshopFlowTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Workshop",
            slug="workshop",
            primary_domain="workshop.example.com",
            tenant_type=TenantType.PLATFORM,
            allowed_assessments=list(ASSESSMENT_CONFIG),
        )
        self.user = get_user_model().objects.create_user(
            email="workshop@example.test", password="test-password", tenant=self.tenant
        )
        self.other = get_user_model().objects.create_user(
            email="other-workshop@example.test", password="test-password", tenant=self.tenant
        )
        token = set_current_tenant_slug(self.tenant.slug)
        self.addCleanup(reset_current_tenant_slug, token)
        self.client.force_login(self.user)
        self.host = {"HTTP_HOST": self.tenant.primary_domain}

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json", **self.host)

    def advance(self, session, action, **data):
        session.refresh_from_db()
        return update_workshop(
            session.id,
            self.user,
            self.tenant,
            {"action": action, "stage_index": session.state["index"], **data},
        )

    def test_start_and_resume_and_central_practice_allowance(self):
        session = start_workshop(self.user, self.tenant, "shl_verify", "schedule")
        self.assertEqual(
            start_workshop(self.user, self.tenant, "shl_verify", "schedule").id, session.id
        )
        TestConfiguration.objects.create(
            tenant=self.tenant, assessment_type="consulting", free_practice_questions=1
        )
        with self.assertRaises(PermissionError):
            start_workshop(self.user, self.tenant, "consulting", "case")
        TestConfiguration.objects.create(
            tenant=self.tenant, assessment_type="shl_verify", free_practice_questions=0
        )
        with self.assertRaises(PermissionError):
            start_workshop(self.user, self.tenant, "shl_verify", "chart_builder")
        with patch(
            "backend.apps.assessments.services.has_unlimited_module_access", return_value=True
        ):
            self.assertIsNotNone(start_workshop(self.user, self.tenant, "consulting", "case"))

    def test_progressive_case_hides_future_exhibits_and_answers(self):
        session = start_workshop(self.user, self.tenant, "consulting_cases", "case")
        public = session_payload(session)
        self.assertNotIn("Exhibit 2", json.dumps(public))
        self.assertNotIn("answer", public["stage"])
        self.assertNotIn("rubric", public["stage"])
        self.assertNotIn("reference", public["stage"])
        first = self.advance(
            session,
            "answer",
            answer={
                "text": "I would compare incremental profit, volume, unit costs and quality risks."
            },
        )
        self.assertIsNone(first["feedback"]["correct"])
        self.assertNotIn("Exhibit 2", json.dumps(first))
        second = self.advance(session, "next")
        self.assertIn("Exhibit 1", json.dumps(second))
        self.assertNotIn("Exhibit 2", json.dumps(second))
        session.refresh_from_db()
        self.advance(session, "answer", answer=session.content["stages"][1]["answer"])
        third = self.advance(session, "next")
        self.assertIn("Exhibit 2", json.dumps(third))

    def test_full_case_saves_drafts_writing_rubrics_and_separate_objective_score(self):
        session = start_workshop(self.user, self.tenant, "consulting_cases", "case")
        self.advance(
            session, "draft", text="My first draft covers revenue, costs and service risks."
        )
        session.refresh_from_db()
        self.assertEqual(
            session_payload(session)["draft"],
            "My first draft covers revenue, costs and service risks.",
        )
        for i, stage in enumerate(session.content["stages"]):
            answer = (
                {
                    "text": "My recommendation compares incremental operating profit, quality and demand risk with a controlled pilot."
                }
                if stage["kind"] == "written"
                else stage["answer"]
            )
            response = self.advance(session, "answer", answer=answer)
            if stage["kind"] == "written":
                self.assertTrue(response["feedback"]["rubric"])
                self.advance(session, "self_review", scores=[2] * len(stage["rubric"]))
            response = self.advance(session, "next")
        self.assertTrue(response["complete"])
        self.assertEqual((response["correct"], response["graded"], response["written"]), (4, 4, 2))
        self.assertEqual(len(response["responses"]), 6)
        self.assertEqual(len(response["self_reviews"]), 2)

    def test_estimate_draft_preserves_numeric_estimate_and_reasoning(self):
        session = start_workshop(self.user, self.tenant, "consulting", "market_estimate")
        response = self.advance(
            session,
            "draft",
            text="Population times ownership, repairs, share and ticket price.",
            estimate="12500",
        )
        self.assertEqual(response["draft"]["estimate"], 12500)
        self.assertIn("Population", response["draft"]["text"])
        response = self.advance(
            session,
            "answer",
            answer={
                "text": "My range is £10–20k, based on population, bicycle ownership, paid repair frequency and a local pilot.",
                "estimate": 12500,
            },
        )
        self.assertIsNone(response["feedback"]["correct"])
        self.assertTrue(response["feedback"]["reference"])

    def test_answer_and_next_retries_are_idempotent_and_answers_lock(self):
        session = start_workshop(self.user, self.tenant, "consulting", "chart_insight")
        answer = session.content["stages"][0]["answer"]
        first = self.advance(session, "answer", answer=answer)
        second = self.advance(session, "answer", answer=str(answer))
        self.assertEqual(first, second)
        with self.assertRaises(ValueError):
            self.advance(session, "answer", answer=answer + 1)
        response = self.advance(session, "next")
        retry = update_workshop(
            session.id, self.user, self.tenant, {"action": "next", "stage_index": 0}
        )
        self.assertEqual(response, retry)
        with self.assertRaises(ValueError):
            self.advance(session, "next")

    def test_passage_reuse_avoids_recent_topics_and_shares_body(self):
        keys = []
        for _ in range(6):
            session = start_workshop(self.user, self.tenant, "watson_glaser", "passage")
            keys.append(session.content["key"])
            self.assertEqual(len({s["passage"] for s in session.content["stages"]}), 1)
            for stage in session.content["stages"]:
                self.advance(session, "answer", answer=stage["answer"])
                self.advance(session, "next")
        self.assertEqual(len(set(keys)), 6)

    def test_approved_edited_passage_is_used_and_withdrawal_stops_resume(self):
        review = EditorialReview.objects.get(content_key=PASSAGES[0]["key"])
        review.content["body"] += " This additional sentence was reviewed."
        review.status = "approved"
        review.reviewer = self.other
        review.reviewer_notes = "Checked wording, every key and alternative interpretations."
        review.full_clean()
        review.save()
        session = start_workshop(self.user, self.tenant, "watson_glaser", "passage")
        self.assertIn("additional sentence", session.content["stages"][0]["passage"])
        self.assertIn("approved", session_payload(session)["review_status"])
        review.status = "withdrawn"
        review.save()
        response = self.client.get(reverse("workshop-session", args=[session.id]), **self.host)
        self.assertEqual(response.status_code, 403)
        new = start_workshop(self.user, self.tenant, "watson_glaser", "passage")
        self.assertNotEqual(new.content["key"], review.content_key)

    def test_editorial_approval_requires_identity_notes_and_valid_content(self):
        review = EditorialReview.objects.first()
        review.status = "approved"
        with self.assertRaises(ValidationError):
            review.full_clean()
        review.reviewer = self.other
        review.reviewer_notes = "Reviewed independently."
        review.content["items"][0]["answer"] = "unoffered answer"
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_endpoints_require_owner_tenant_access_csrf_and_valid_json(self):
        session = start_workshop(self.user, self.tenant, "shl_verify", "schedule")
        url = reverse("workshop-session", args=[session.id])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url, **self.host).status_code, 404)
        self.client.force_login(self.user)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(
            csrf_client.post(url, "{}", content_type="application/json", **self.host).status_code,
            403,
        )
        for payload in ([], None, "invalid"):
            self.assertEqual(self.post(url, payload).status_code, 400)
        self.tenant.allowed_assessments = ["ccat"]
        self.tenant.save()
        self.assertEqual(self.client.get(url, **self.host).status_code, 403)
        self.assertEqual(
            self.client.get(
                reverse("pages:assessment-workshop", args=["shl_verify"]), **self.host
            ).status_code,
            403,
        )

    def test_reports_are_scoped_and_cannot_reference_future_stages(self):
        session = start_workshop(self.user, self.tenant, "consulting_cases", "case")
        data = {
            "action": "report",
            "session_id": session.id,
            "stage_index": 4,
            "reason": "ambiguous",
            "detail": "Please check the wording.",
        }
        self.assertEqual(self.post(reverse("item-event"), data).status_code, 400)
        data["stage_index"] = 0
        self.assertEqual(self.post(reverse("item-event"), data).status_code, 200)
        self.assertEqual(self.post(reverse("item-event"), data).status_code, 200)
        self.assertEqual(ItemReport.objects.count(), 1)
        self.client.force_login(self.other)
        self.assertEqual(self.post(reverse("item-event"), data).status_code, 404)

    def test_item_receipts_are_scoped_and_observations_checked_on_server(self):
        q = asdict(GENERATOR_MAP["consulting_math"].generate("medium", "receipt:1"))
        token = issue_question(self.user, self.tenant, q)
        exposure = resolve_receipt(token, self.user, self.tenant)
        with self.assertRaises(ItemExposure.DoesNotExist):
            resolve_receipt(token, self.other, self.tenant)
        answer = str(q["correct_answer"]["answer"])
        saved = observe_answer(exposure, answer, 1250)
        self.assertTrue(saved.is_correct)
        self.assertEqual(saved.response_ms, 1250)
        self.assertEqual(observe_answer(exposure, answer).id, saved.id)
        with self.assertRaises(ValueError):
            observe_answer(
                exposure, next(str(o) for o in q["payload"]["options"] if str(o) != answer)
            )
        q2 = asdict(GENERATOR_MAP["consulting_math"].generate("medium", "receipt:2"))
        test_token = issue_question(self.user, self.tenant, q2, allow_observation=False)
        self.assertEqual(
            self.post(
                reverse("item-event"),
                {"action": "answer", "token": test_token, "answer": q2["correct_answer"]["answer"]},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post(
                reverse("item-event"),
                {
                    "action": "report",
                    "token": test_token,
                    "reason": "answer",
                    "detail": "Check this key.",
                },
            ).status_code,
            200,
        )

    def test_recent_questions_are_avoided_without_breaking_generation(self):
        initial = _build_question_batch(
            "same-seed",
            "consulting_math",
            "practice",
            8,
            "medium",
            user=self.user,
            tenant=self.tenant,
        )
        for q in initial:
            issue_question(self.user, self.tenant, q)
        second = _build_question_batch(
            "same-seed",
            "consulting_math",
            "practice",
            8,
            "medium",
            user=self.user,
            tenant=self.tenant,
        )
        self.assertFalse(
            {item_signature(q) for q in initial}.intersection(item_signature(q) for q in second)
        )

    def test_withdrawn_template_families_are_not_generated_for_learners(self):
        EditorialReview.objects.create(
            content_key="template:consulting_math:market_funnel",
            title="Market funnel",
            status="withdrawn",
        )
        batch = _build_question_batch(
            "withdraw-test",
            "consulting_math",
            "practice",
            24,
            "medium",
            user=self.user,
            tenant=self.tenant,
        )
        self.assertNotIn("market_funnel", {q["payload"]["metadata"]["subtype"] for q in batch})

    def test_refresh_review_snapshots_is_idempotent_and_does_not_approve_content(self):
        from django.core.management import call_command
        from io import StringIO

        call_command("refresh_question_reviews", stdout=StringIO())
        row = EditorialReview.objects.filter(content_key__startswith="template:").first()
        self.assertEqual(row.status, "needs_review")
        row.status = "approved"
        row.reviewer = self.other
        row.reviewer_notes = "I checked the representative examples, units, keys and distractors."
        row.full_clean()
        row.save()
        count = EditorialReview.objects.count()
        call_command("refresh_question_reviews", stdout=StringIO())
        row.refresh_from_db()
        self.assertEqual(row.status, "approved")
        self.assertEqual(EditorialReview.objects.count(), count)
        row.content["title"] = "An outdated snapshot"
        row.save()
        call_command("refresh_question_reviews", stdout=StringIO())
        row.refresh_from_db()
        self.assertEqual(row.status, "needs_review")

    def test_workshop_api_unauthenticated_requests_return_json(self):
        self.client.logout()
        response = self.post(
            reverse("workshop-start"), {"assessment_type": "shl_verify", "kind": "schedule"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Sign in to continue.")

    def test_workshop_pages_and_start_api_cover_every_published_kind(self):
        for assessment, choices in WORKSHOPS.items():
            response = self.client.get(
                reverse("pages:assessment-workshop", args=[assessment]), **self.host
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Applied practice workshop")
            for kind, _ in choices:
                started = self.post(
                    reverse("workshop-start"), {"assessment_type": assessment, "kind": kind}
                )
                self.assertEqual(started.status_code, 200)
                data = started.json()
                self.assertEqual(data["assessment_type"], assessment)
                self.assertNotIn("answer", data["stage"])
                self.assertNotIn("reference", data["stage"])

    def test_existing_passage_is_not_marked_approved_for_a_different_revision(self):
        session = start_workshop(self.user, self.tenant, "watson_glaser", "passage")
        review = EditorialReview.objects.get(content_key=session.content["key"])
        review.content["body"] += " A later editor added a new fact."
        review.status = "approved"
        review.reviewer = self.other
        review.reviewer_notes = "Reviewed the later revision."
        review.full_clean()
        review.save()
        self.assertIn("pending", session_payload(session)["review_status"])

    def test_peer_review_links_require_owner_consent_and_can_be_revoked(self):
        from urllib.parse import urlparse

        session = start_workshop(self.user, self.tenant, "consulting", "market_estimate")
        url = reverse("workshop-review-invite", args=[session.id])
        self.assertEqual(self.post(url, {}).status_code, 404)
        self.advance(
            session,
            "answer",
            answer={
                "text": "My estimate uses population, bicycle ownership, repair frequency, captured share and a sensitivity range.",
                "estimate": 12000,
            },
        )
        self.advance(session, "next")
        response = self.post(url, {})
        self.assertEqual(response.status_code, 200)
        review_url = urlparse(response.json()["url"]).path
        self.assertEqual(self.client.get(review_url, **self.host).status_code, 200)
        self.assertEqual(
            self.client.post(
                review_url,
                {
                    "feedback": "This is self feedback and should use the self-review rubric instead."
                },
                **self.host,
            ).status_code,
            403,
        )
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(review_url, **self.host).status_code, 200)
        response = self.client.post(
            review_url,
            {
                "feedback": "The structure is clear. Add a low/high range and validate paid repair demand with a representative pilot."
            },
            **self.host,
        )
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(len(session_payload(session)["peer_reviews"]), 1)
        self.client.force_login(self.user)
        self.assertEqual(self.post(url, {"revoke": True}).status_code, 200)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(review_url, **self.host).status_code, 404)
        self.assertEqual(len(session_payload(session)["peer_reviews"]), 1)

    def test_peer_review_links_reject_unrelated_tenants_and_expire(self):
        from datetime import timedelta
        from urllib.parse import urlparse
        from django.utils import timezone

        session = start_workshop(self.user, self.tenant, "consulting", "market_estimate")
        self.advance(
            session,
            "answer",
            answer={
                "text": "Population times ownership, repair frequency, captured share and price; validate assumptions in a pilot.",
                "estimate": 12000,
            },
        )
        self.advance(session, "next")
        response = self.post(reverse("workshop-review-invite", args=[session.id]), {})
        path = urlparse(response.json()["url"]).path
        other_tenant = Tenant.objects.create(
            name="Unrelated",
            slug="unrelated-workshop",
            primary_domain="unrelated.example.com",
            tenant_type=TenantType.PLATFORM,
            allowed_assessments=list(ASSESSMENT_CONFIG),
        )
        outsider = get_user_model().objects.create_user(
            email="outsider@example.test", password="test-password", tenant=other_tenant
        )
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(path, **self.host).status_code, 404)
        session.peer_invites.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(path, **self.host).status_code, 404)
