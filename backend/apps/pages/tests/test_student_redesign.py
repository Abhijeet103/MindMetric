from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from backend.apps.assessments.models import Attempt, AttemptMode, AttemptSection, AttemptStatus
from backend.apps.pages.models import ApplicationDeadline, EmployerAssessment, LegalPage
from backend.apps.pages.student import build_study_plan


def make_user(email="student@example.com"):
    return get_user_model().objects.create_user(email=email, password="secret-pass-123")


class HomePageTests(TestCase):
    def test_home_leads_with_student_positioning_and_live_test_picker(self):
        response = self.client.get(reverse("pages:home"))
        self.assertContains(response, "From invite to interview.")
        self.assertContains(response, reverse("pages:assessment-practice", args=["ccat"]))
        self.assertContains(response, reverse("pages:company-lookup"))
        picker = response.context["home_tests"]
        self.assertEqual(picker[0]["key"], "ccat")
        self.assertTrue(all(item["url"] for item in picker))
        self.assertContains(response, f"All {len(picker)} tests")
        # The homepage drops the nav "Start free" button; other pages keep it.
        self.assertNotContains(response, 'class="nav-cta"')
        self.assertContains(self.client.get(reverse("pages:pricing")), 'class="nav-cta"')

    def test_sample_question_links_to_free_practice_with_real_limit(self):
        response = self.client.get(reverse("pages:home"))
        url = response.context["sample_practice_url"]
        count = response.context["sample_free_count"]
        self.assertContains(response, f'href="{url}"')
        if count:
            self.assertContains(response, f"Try {count} more like this")
        # The free practice page it points to must open without signing in.
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_pricing_section_uses_configured_plans(self):
        response = self.client.get(reverse("pages:home"))
        self.assertContains(response, 'id="pricing"')
        for plan in response.context["home_plans"]:
            self.assertContains(response, plan["price_display"])


class ResultsPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.attempt = Attempt.objects.create(
            user=self.user,
            assessment_type="prepgia",
            mode=AttemptMode.FULL_TEST,
            status=AttemptStatus.COMPLETED,
            completed_at=timezone.now(),
        )
        AttemptSection.objects.create(
            attempt=self.attempt, section_type="reasoning", order_index=0, time_limit_seconds=300,
            question_count=10, correct_answers_count=9, incorrect_answers_count=1,
        )
        AttemptSection.objects.create(
            attempt=self.attempt, section_type="perceptual_speed", order_index=1, time_limit_seconds=120,
            question_count=10, correct_answers_count=4, incorrect_answers_count=2,
        )
        self.url = reverse("pages:attempt-results", args=[self.attempt.id])

    def test_owner_sees_accuracy_and_weakest_section(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["accuracy"], 65)
        self.assertEqual(response.context["weakest"]["section_type"], "perceptual_speed")
        self.assertEqual(response.context["weakest"]["unanswered"], 4)
        self.assertContains(response, "Practice this next")
        self.assertContains(response, reverse("pages:assessment-section-detail", args=["prepgia", "perceptual_speed"]))
        self.assertContains(response, "See membership")

    def test_other_users_and_unfinished_attempts_are_hidden(self):
        self.client.force_login(make_user("other@example.com"))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.user)
        self.attempt.status = AttemptStatus.IN_PROGRESS
        self.attempt.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_requires_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)


class ApplicationDeadlineTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_add_list_and_remove_application(self):
        due = timezone.localdate() + timedelta(days=5)
        response = self.client.post(
            reverse("pages:application-add"),
            {"company": "  Example Bank ", "assessment_type": "ccat", "due_date": due.isoformat()},
        )
        self.assertEqual(response.status_code, 302)
        deadline = ApplicationDeadline.objects.get(user=self.user)
        self.assertEqual(deadline.company, "Example Bank")

        dashboard = self.client.get(reverse("pages:dashboard"))
        self.assertContains(dashboard, "Example Bank")
        self.assertEqual(dashboard.context["study_plan"]["action_url"], reverse("pages:assessment-practice", args=["ccat"]))

        self.client.post(reverse("pages:application-delete", args=[deadline.id]))
        self.assertFalse(ApplicationDeadline.objects.exists())

    def test_rejects_past_dates_and_unknown_tests(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self.client.post(reverse("pages:application-add"), {"company": "Late Co", "assessment_type": "", "due_date": yesterday.isoformat()})
        self.client.post(reverse("pages:application-add"), {"company": "Odd Co", "assessment_type": "not_a_test", "due_date": timezone.localdate().isoformat()})
        self.assertFalse(ApplicationDeadline.objects.exists())

    def test_cannot_delete_someone_elses_application(self):
        other = ApplicationDeadline.objects.create(user=make_user("other@example.com"), company="Theirs", due_date=timezone.localdate())
        response = self.client.post(reverse("pages:application-delete", args=[other.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ApplicationDeadline.objects.filter(id=other.id).exists())

    def test_study_plan_moves_from_drills_to_simulation_to_rest(self):
        titles = {"ccat": "CCAT"}
        today = timezone.localdate()

        def plan(days, test="ccat"):
            return build_study_plan(ApplicationDeadline(company="X", assessment_type=test, due_date=today + timedelta(days=days)), titles)

        self.assertIn("Drill", plan(6)["headline"])
        self.assertIn("simulation", plan(2)["headline"])
        self.assertEqual(plan(0)["headline"], "Assessment day")
        self.assertIn("Find out which test", plan(4, test="")["headline"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_NOTIFICATIONS_ENABLED=True)
class DeadlineReminderTests(TestCase):
    def test_sends_one_reminder_two_days_out(self):
        user = make_user()
        soon = ApplicationDeadline.objects.create(user=user, company="Soon Co", due_date=timezone.localdate() + timedelta(days=2))
        ApplicationDeadline.objects.create(user=user, company="Later Co", due_date=timezone.localdate() + timedelta(days=9))
        call_command("send_deadline_reminders", stdout=open("/dev/null", "w"))
        call_command("send_deadline_reminders", stdout=open("/dev/null", "w"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Soon Co", mail.outbox[0].subject)
        soon.refresh_from_db()
        self.assertIsNotNone(soon.reminder_sent_at)


class CompanyLookupTests(TestCase):
    def setUp(self):
        EmployerAssessment.objects.create(
            company="Published Corp", industry="Banking", assessment_types=["ccat"],
            source_url="https://example.com/careers", source_label="Careers FAQ",
            verified_on=timezone.localdate(), is_published=True,
        )
        EmployerAssessment.objects.create(
            company="Draft Corp", industry="Banking", assessment_types=["ccat"],
            source_url="https://example.com/draft", source_label="Unchecked",
            verified_on=timezone.localdate(), is_published=False,
        )

    def test_only_published_entries_with_sources_are_shown(self):
        response = self.client.get(reverse("pages:company-lookup"), {"q": "bank"})
        self.assertContains(response, "Published Corp")
        self.assertContains(response, "Careers FAQ")
        self.assertNotContains(response, "Draft Corp")

    def test_no_match_shows_honest_empty_state(self):
        response = self.client.get(reverse("pages:company-lookup"), {"q": "Nowhere Ltd"})
        self.assertContains(response, "Get your prep guide")
        self.assertNotContains(response, "No sourced entry for")


class LegalPageTests(TestCase):
    def test_unpublished_pages_404_and_footer_falls_back_to_email(self):
        LegalPage.objects.create(slug="privacy", title="Privacy policy", body="Draft", effective_date=timezone.localdate())
        self.assertEqual(self.client.get(reverse("pages:legal-page", args=["privacy"])).status_code, 404)
        self.assertContains(self.client.get(reverse("pages:pricing")), "mailto:support@mindmetric.store?subject=Privacy")

    def test_published_page_renders_headings_and_footer_link(self):
        LegalPage.objects.create(
            slug="terms", title="Terms of service", body="## Using MindMetric\n\nBe kind.",
            effective_date=timezone.localdate(), is_published=True,
        )
        response = self.client.get(reverse("pages:legal-page", args=["terms"]))
        self.assertContains(response, "<h2>Using MindMetric</h2>", html=True)
        self.assertContains(response, reverse("pages:legal-page", args=["terms"]))


class CrawlerFilesTests(TestCase):
    def test_robots_blocks_private_student_routes(self):
        content = self.client.get("/robots.txt").content.decode()
        for path in ["/results/", "/applications/", "/practice/adaptive/", "/billing/", "/login/"]:
            self.assertIn(f"Disallow: {path}", content)
        self.assertNotIn("Disallow: /companies/\n", content)

    def test_sitemap_lists_company_lookup_and_only_published_legal_pages(self):
        LegalPage.objects.create(slug="terms", title="Terms", body="x", effective_date=timezone.localdate(), is_published=True)
        LegalPage.objects.create(slug="privacy", title="Privacy", body="x", effective_date=timezone.localdate())
        content = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/companies/</loc>", content)
        self.assertIn("/legal/terms/</loc>", content)
        self.assertNotIn("/legal/privacy/", content)
        self.assertNotIn("/results/", content)
