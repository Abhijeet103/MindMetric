import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from backend.apps.accounts.forms import CustomSignupForm
from backend.apps.assessments.config import ASSESSMENT_CONFIG
from backend.apps.billing.recruiter_credits import grant_welcome_credits
from backend.apps.pages.models import RecruiterAssessment, RecruiterSubmission
from backend.apps.tenants.models import Tenant

User = get_user_model()


class RecruiterFlowTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Recruiter tests", slug="recruiter-tests", primary_domain="recruiter.example.com", tenant_type="platform", allowed_assessments=list(ASSESSMENT_CONFIG))
        self.host = {"HTTP_HOST": self.tenant.primary_domain}
        self.owner = User.objects.create_user(email="owner@example.com", password="password123", account_type="recruiter", organization="Example hiring", tenant=self.tenant)
        self.other = User.objects.create_user(email="other@example.com", password="password123", account_type="recruiter", tenant=self.tenant)
        self.student = User.objects.create_user(email="student@example.com", password="password123", tenant=self.tenant)
        grant_welcome_credits(self.owner)
        grant_welcome_credits(self.other)
        self.client.force_login(self.owner)
        self.dashboard = reverse("pages:recruiter-dashboard")
        self.create = reverse("pages:recruiter-create")
        self.data = {"title": "Graduate screening", "organization": "Example hiring", "role_title": "Analyst", "modules": ["sjt_workplace", "work_simulation", "verbal_passages"], "difficulty": "medium", "questions_per_module": 4, "duration_minutes": 10, "open_days": 7, "max_candidates": 10, "allowed_emails": "", "instructions": "Work independently."}

    def make_assessment(self, **changes):
        data = {**self.data, **changes}
        self.client.force_login(self.owner)
        response = self.client.post(self.create, data, **self.host)
        self.assertEqual(response.status_code, 302)
        return RecruiterAssessment.objects.latest("created_at")

    def start(self, assessment, client=None, **changes):
        client = client or self.client
        client.force_login(self.student)
        return client.post(reverse("pages:recruiter-candidate-start", args=[assessment.share_token]), json.dumps({"consent": True, **changes}), content_type="application/json", **self.host)

    def post_session(self, submission, data, client=None):
        if "answers" in data and "revision" not in data:
            submission.refresh_from_db()
            data["revision"] = submission.answer_revision + 1
        return (client or self.client).post(reverse("pages:recruiter-candidate-session", args=[submission.pk]), json.dumps(data), content_type="application/json", **self.host)

    def test_signup_role_is_separate_from_subscription_and_admin(self):
        form = CustomSignupForm({"first_name": "Recruiter", "account_type": "recruiter"})
        self.assertTrue(form.is_valid())
        request = RequestFactory().post("/accounts/signup/")
        request.tenant = self.tenant
        form.signup(request, self.student)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_recruiter)
        self.assertEqual(self.student.role, "free")
        self.assertFalse(self.student.is_staff)
        self.assertFalse(self.student.is_superuser)
        invalid = CustomSignupForm({"first_name": "Bad", "account_type": "admin"})
        self.assertFalse(invalid.is_valid())

    def test_login_and_signup_offer_recruiter_option(self):
        self.client.logout()
        page = self.client.get(reverse("pages:login"), {"as": "recruiter"}, **self.host)
        self.assertContains(page, "Recruiter sign in")
        self.assertContains(page, 'name="next" value="/recruiter/"')
        self.assertContains(self.client.get("/accounts/signup/", **self.host), "I am joining as")
        response = self.client.post(reverse("pages:login")+"?as=recruiter", {"login": self.owner.email, "password": "password123"}, **self.host)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.dashboard)

    def test_recruiter_dashboard_and_students_are_kept_out(self):
        self.assertContains(self.client.get(self.dashboard, **self.host), "Your assessments")
        # Recruiters can also use the student practice space.
        self.assertEqual(self.client.get(reverse("pages:dashboard"), **self.host).status_code, 200)
        self.client.force_login(self.student)
        for url in (self.dashboard, self.create, reverse("pages:recruiter-credits"), reverse("pages:recruiter-upload")):
            response = self.client.get(url, **self.host)
            self.assertEqual(response.status_code, 403, url)
            self.assertContains(response, "100 free candidate credits", status_code=403)
        # Students can no longer switch themselves into a recruiter workspace.
        self.assertEqual(self.client.post(self.dashboard, {"organization": "New company", "confirm": "on"}, **self.host).status_code, 403)
        self.assertEqual(self.client.post(self.create, self.data, **self.host).status_code, 403)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_recruiter)
        self.assertFalse(RecruiterAssessment.objects.exists())

    def test_create_share_and_close_preserves_started_attempt(self):
        assessment = self.make_assessment()
        detail = reverse("pages:recruiter-assessment", args=[assessment.pk])
        page = self.client.get(detail, **self.host)
        self.assertContains(page, str(assessment.share_token))
        self.assertContains(page, "Copy link")
        self.assertIn("no-store", page.headers["Cache-Control"])
        response = self.start(assessment)
        self.assertEqual(response.status_code, 201)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(detail, {"action": "close"}, **self.host).status_code, 302)
        self.assertEqual(self.start(assessment).status_code, 200)
        newcomer = User.objects.create_user(email="new@example.com", password="x", tenant=self.tenant)
        self.client.force_login(newcomer)
        self.assertEqual(self.client.post(reverse("pages:recruiter-candidate-start", args=[assessment.share_token]), '{"consent":true}', content_type="application/json", **self.host).status_code, 400)

    def test_candidate_payload_has_no_keys_explanations_or_seeds(self):
        assessment = self.make_assessment()
        result = self.start(assessment)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(len(result.json()["questions"]), 12)
        raw = result.content.decode()
        self.assertNotIn("correct_answer", raw)
        self.assertNotIn("explanation", raw)
        self.assertNotIn("metadata", raw)
        for question in result.json()["questions"]:
            self.assertEqual(question["seed"], "")
            self.assertTrue(question["question_text"])
        for question in result.json()["questions"]:
            if question.get("case_study"):
                self.assertNotIn("id", question["case_study"])
        for item in assessment.submissions.get().questions:
            self.assertNotIn(item["seed"], raw)
        self.assertIn("no-store", result.headers["Cache-Control"])

    def test_start_is_idempotent_and_requires_consent(self):
        assessment = self.make_assessment()
        self.assertEqual(self.start(assessment, consent=False).status_code, 400)
        first = self.start(assessment)
        again = self.start(assessment)
        self.assertEqual(first.json()["id"], again.json()["id"])
        self.assertEqual(assessment.submissions.count(), 1)
        self.assertEqual(first.json()["deadline"], again.json()["deadline"])

    def test_answers_save_score_and_complete_idempotently(self):
        assessment = self.make_assessment()
        self.start(assessment)
        submission = assessment.submissions.get()
        answers = {str(i): str(q["correct_answer"]["answer"]) for i, q in enumerate(submission.questions)}
        self.assertEqual(self.post_session(submission, {"answers": answers, "events": ["tab_hidden", "fullscreen_exit"]}).status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(len(submission.answers), 12)
        done = self.post_session(submission, {"submit": True})
        self.assertEqual(done.json()["status"], "submitted")
        self.assertNotIn("questions", done.json())
        submission.refresh_from_db()
        self.assertEqual(submission.score, 12)
        self.assertEqual(submission.percentage, 100)
        self.assertEqual(len(submission.section_scores), 3)
        self.post_session(submission, {"answers": {"0": "tamper"}, "submit": True})
        submission.refresh_from_db()
        self.assertEqual(submission.score, 12)
        self.assertEqual(self.start(assessment).json()["status"], "submitted")
        self.assertEqual(assessment.submissions.count(), 1)

    def test_server_deadline_rejects_late_answers_and_does_not_restart(self):
        assessment = self.make_assessment()
        self.start(assessment)
        submission = assessment.submissions.get()
        self.post_session(submission, {"answers": {"0": str(submission.questions[0]["correct_answer"]["answer"])}})
        submission.deadline_at = timezone.now() - timedelta(seconds=1)
        submission.save(update_fields=["deadline_at"])
        late = {str(i): str(q["correct_answer"]["answer"]) for i, q in enumerate(submission.questions)}
        response = self.post_session(submission, {"answers": late, "deadline": "2099-01-01", "submit": True})
        self.assertEqual(response.json()["status"], "expired")
        submission.refresh_from_db()
        self.assertEqual(submission.score, 1)
        self.assertEqual(len(submission.answers), 1)
        self.assertEqual(self.start(assessment).json()["status"], "expired")

    def test_owner_dashboard_finalizes_abandoned_attempts(self):
        assessment = self.make_assessment()
        self.start(assessment)
        RecruiterSubmission.objects.update(deadline_at=timezone.now()-timedelta(seconds=1))
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.dashboard, **self.host).status_code, 200)
        self.assertEqual(assessment.submissions.get().status, "expired")

    def test_invalid_answers_and_events_are_rejected_without_mutating(self):
        assessment = self.make_assessment()
        self.start(assessment)
        submission = assessment.submissions.get()
        for payload in ({"answers": {"-1": "A"}}, {"answers": {"00": "A"}}, {"answers": {"0": "made up"}}, {"answers": []}, {"events": ["fabricated"]}, {"events": ["tab_hidden"]*21}, {"submit": "yes"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.post_session(submission, payload).status_code, 400)
        submission.refresh_from_db()
        self.assertEqual(submission.answers, {})
        self.assertEqual(submission.monitoring_events, [])

    def test_monitoring_events_have_server_timestamps_and_bounded_log(self):
        assessment = self.make_assessment()
        self.start(assessment)
        submission = assessment.submissions.get()
        submission.last_seen_at = timezone.now()-timedelta(seconds=70)
        submission.save(update_fields=["last_seen_at"])
        self.post_session(submission, {"events": ["window_blur"], "at": "2099"})
        submission.refresh_from_db()
        self.assertEqual(submission.monitoring_events[0]["source"], "browser")
        self.assertEqual(submission.monitoring_events[1]["kind"], "connection_gap")
        self.assertGreaterEqual(submission.monitoring_events[1]["seconds"], 70)
        self.assertNotIn("2099", str(submission.monitoring_events))
        for _ in range(11):
            self.post_session(submission, {"events": ["tab_hidden"]*20})
        submission.refresh_from_db()
        self.assertEqual(len(submission.monitoring_events), 200)

    def test_other_recruiters_and_candidates_cannot_read_results_or_sessions(self):
        assessment = self.make_assessment()
        self.start(assessment)
        submission = assessment.submissions.get()
        result = reverse("pages:recruiter-result", args=[submission.pk])
        session = reverse("pages:recruiter-candidate-session", args=[submission.pk])
        self.client.force_login(self.other)
        for url in (result, reverse("pages:recruiter-assessment", args=[assessment.pk]), session):
            self.assertEqual(self.client.get(url, **self.host).status_code, 404)
        self.assertEqual(self.post_session(submission, {"submit": True}).status_code, 404)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(result, **self.host).status_code, 403)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(result, **self.host), "Session review")
        self.assertNotIn("correct_answer", self.client.get(result, **self.host).content.decode())

    def test_cross_tenant_share_and_ownership_are_isolated(self):
        assessment = self.make_assessment()
        foreign = Tenant.objects.create(name="Other site", slug="foreign-site", primary_domain="foreign.example.com", tenant_type="platform", allowed_assessments=list(ASSESSMENT_CONFIG))
        self.client.logout()
        self.assertEqual(self.client.get(reverse("pages:recruiter-invite", args=[assessment.share_token]), HTTP_HOST=foreign.primary_domain).status_code, 404)

    def test_restrictions_capacity_and_expiry_before_start(self):
        assessment = self.make_assessment(allowed_emails="invited@example.com", max_candidates=1)
        self.assertEqual(self.start(assessment).status_code, 403)
        assessment.allowed_emails = []
        assessment.closes_at = timezone.now()-timedelta(seconds=1)
        assessment.save()
        self.assertEqual(self.start(assessment).status_code, 400)
        assessment.closes_at = timezone.now()+timedelta(days=1)
        assessment.save()
        self.assertEqual(self.start(assessment).status_code, 201)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("pages:recruiter-candidate-start", args=[assessment.share_token]), '{"consent":true}', content_type="application/json", **self.host).status_code, 400)

    def test_form_limits_and_skill_allocation(self):
        for changes in ({"duration_minutes": 0}, {"modules": ["not-a-module"]}, {"max_candidates": 999}, {"allowed_emails": "invalid"}, {"modules": [module["key"] for config in ASSESSMENT_CONFIG.values() for module in config["modules"]], "questions_per_module": 12}):
            response = self.client.post(self.create, {**self.data, **changes}, **self.host)
            self.assertEqual(response.status_code, 400)
        self.assertFalse(RecruiterAssessment.objects.exists())
        self.tenant.allowed_assessments = ["ccat"]
        self.tenant.save(update_fields=["allowed_assessments"])
        self.assertEqual(self.client.post(self.create, self.data, **self.host).status_code, 400)

    def test_anonymous_access_and_csrf_protection(self):
        assessment = self.make_assessment()
        self.client.logout()
        self.assertEqual(self.client.get(self.dashboard, **self.host).status_code, 302)
        self.assertContains(self.client.get(reverse("pages:recruiter-invite", args=[assessment.share_token]), **self.host), "Sign in to continue")
        self.assertEqual(self.client.post(reverse("pages:recruiter-candidate-start", args=[assessment.share_token]), '{"consent":true}', content_type="application/json", **self.host).status_code, 401)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.owner)
        self.assertEqual(protected.post(self.create, self.data, **self.host).status_code, 403)
        protected.force_login(self.student)
        self.assertEqual(protected.post(reverse("pages:recruiter-candidate-start", args=[assessment.share_token]), '{"consent":true}', content_type="application/json", **self.host).status_code, 403)

    def test_public_invitation_has_no_answers_and_escapes_recruiter_text(self):
        assessment = self.make_assessment(title='<script>alert("x")</script>')
        self.client.logout()
        page = self.client.get(reverse("pages:recruiter-invite", args=[assessment.share_token]), **self.host)
        self.assertContains(page, "&lt;script&gt;")
        self.assertNotContains(page, '<script>alert("x")</script>')
        self.assertNotContains(page, "correct_answer")
        self.assertNotContains(page, self.student.email)


    def test_existing_recruiter_normal_login_uses_recruiter_dashboard(self):
        self.client.logout()
        response = self.client.post(reverse("pages:login"), {"login": self.owner.email, "password": "password123"}, **self.host)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.dashboard)

    def test_invite_login_destination_is_preserved_for_email_and_google(self):
        assessment = self.make_assessment()
        self.client.logout()
        next_url = reverse("pages:recruiter-invite", args=[assessment.share_token])
        page = self.client.get(reverse("pages:login"), {"next": next_url}, **self.host)
        self.assertIn("next=", page.context["google_login_path"])
        self.assertEqual(page.context["next_value"], next_url)
        response = self.client.post(reverse("pages:login"), {"login": self.student.email, "password": "password123", "next": next_url}, **self.host)
        self.assertEqual(response.url, next_url)


    def test_out_of_order_autosave_cannot_replace_newer_answer(self):
        assessment = self.make_assessment()
        self.start(assessment)
        submission = assessment.submissions.get()
        options = [str(value) for value in submission.questions[0]["payload"]["options"]]
        self.post_session(submission, {"answers": {"0": options[1]}, "revision": 2})
        self.post_session(submission, {"answers": {"0": options[0]}, "revision": 1})
        submission.refresh_from_db()
        self.assertEqual(submission.answers["0"], options[1])
        self.assertEqual(submission.answer_revision, 2)
        resumed = self.client.get(reverse("pages:recruiter-candidate-session", args=[submission.pk]), **self.host)
        self.assertEqual(resumed.json()["revision"], 2)
