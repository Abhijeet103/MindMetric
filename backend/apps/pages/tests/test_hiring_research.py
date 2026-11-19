import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from backend.apps.pages import hiring_research as service
from backend.apps.pages.models import AudienceContact, EmployerAssessment, HiringResearch, TestSuggestion


def provider_report(prep_days=3):
    report = {
        "stages": [{"title": "Assessment", "detail": "An employer-described assessment.",
                    "evidence": "employer", "source_urls": ["https://example.com/careers"]}],
        "experiences": [{"title": "Engineering interview", "detail": "A candidate described a technical discussion.",
                         "reported_date": "2025", "source_urls": ["https://example.com/interview"]}],
        "gaps": ["Team-specific details are uncertain."],
        "plan": [{"day": day, "title": "Prepare", "tasks": ["Review your projects."],
                  "practice_keys": ["shl_verify"]} for day in range(1, prep_days + 1)],
        "practice": [{"key": "shl_verify", "reason": "Develop numerical reasoning."}],
        "assessments": [],
        "coverage_note": "Coding practice is not included in this platform catalogue.",
    }
    return {
        "id": "resp_test123", "status": "completed", "output": [
            {"type": "web_search_call", "action": {"sources": [
                {"url": "https://example.com/careers", "title": "Careers"},
                {"url": "https://example.com/interview", "title": "Candidate account"},
            ]}},
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(report), "annotations": []}]},
        ],
    }


def alter_report(response, update):
    data = json.loads(response["output"][1]["content"][0]["text"])
    update(data)
    response["output"][1]["content"][0]["text"] = json.dumps(data)
    return response


@override_settings(HIRING_RESEARCH_ENABLED=True, OPENAI_API_KEY="test-key",
                   HIRING_RESEARCH_MODEL="gpt-6-luna", HIRING_RESEARCH_USER_DAILY_LIMIT=5,
                   HIRING_RESEARCH_SITE_DAILY_LIMIT=100)
class HiringResearchTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(email="research@example.com", password="pass12345")
        self.client.force_login(self.user)
        self.start = reverse("pages:hiring-research-start")
        self.data = {"company": "JP Morgan", "role": "Software engineer", "location": "India", "prep_days": 3}
        page = self.client.get(reverse("pages:company-lookup"))
        self.tenant_id = getattr(getattr(page.wsgi_request, "tenant", None), "pk", None)

    def create_job(self, **kwargs):
        return HiringResearch.objects.create(cache_key="fixture", tenant_id=self.tenant_id, **self.data,
                                             expires_at=timezone.now() + timedelta(hours=24), **kwargs)

    @patch.object(service, "_api")
    def test_requires_login_feature_and_valid_input_before_provider(self, api):
        self.client.logout()
        self.assertEqual(self.client.post(self.start, self.data).status_code, 401)
        self.client.force_login(self.user)
        with override_settings(HIRING_RESEARCH_ENABLED=False):
            self.assertEqual(self.client.post(self.start, self.data).status_code, 503)
        for changes in ({"role": ""}, {"company": "x"}, {"prep_days": 30}, {"company": "x" * 121}):
            self.assertEqual(self.client.post(self.start, {**self.data, **changes}).status_code, 400)
        api.assert_not_called()

    def test_post_is_csrf_protected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.start, self.data).status_code, 403)

    @patch.object(service, "_api", return_value=provider_report(7))
    def test_single_query_builds_a_plan_without_separate_fields(self, api):
        query = "JPMorgan software engineer interviews in India"
        response = self.client.post(self.start, {"query": query})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        request = json.loads(api.call_args.kwargs["payload"]["input"])["request"]
        self.assertEqual(request, {"company": query, "role": "", "location": "", "prep_days": 7})
        self.assertIn("7-day preparation plan", response.json()["html"])

    @patch.object(service, "_api")
    def test_invalid_single_queries_do_not_start_research(self, api):
        for query in ("", "!", "---", "x" * 121):
            self.assertEqual(self.client.post(self.start, {"query": query}).status_code, 400)
        api.assert_not_called()

    @patch.object(service, "_api", return_value={"id": "resp_test123", "status": "queued"})
    def test_background_start_poll_and_cached_alias(self, api):
        started = self.client.post(self.start, self.data)
        self.assertEqual(started.status_code, 202)
        self.assertNotIn("resp_test123", started.content.decode())
        payload = api.call_args.kwargs["payload"]
        self.assertTrue(payload["background"])
        self.assertEqual(payload["model"], "gpt-6-luna")
        self.assertEqual(payload["max_tool_calls"], 5)
        self.assertNotIn(self.user.email, json.dumps(payload))
        api.return_value = provider_report()
        finished = self.client.get(started.json()["status_url"])
        self.assertEqual(finished.json()["status"], "completed")
        self.assertIn('href="https://example.com/careers"', finished.json()["html"])
        self.assertIn("Candidate reported", finished.json()["html"])
        self.assertIn(reverse("pages:assessment-practice", args=["shl_verify"]), finished.json()["html"])
        cached = self.client.post(self.start, {**self.data, "company": "J.P.Morgan"})
        self.assertEqual(cached.json()["id"], started.json()["id"])
        self.assertEqual(api.call_count, 2)

    @patch.object(service, "_api", return_value=provider_report())
    def test_complete_response_is_immediately_rendered_and_reloadable(self, api):
        result = self.client.post(self.start, self.data)
        self.assertEqual(result.json()["status"], "completed")
        page = self.client.get(reverse("pages:company-lookup"), {"report": result.json()["id"]})
        self.assertContains(page, "Your preparation brief")
        self.assertContains(page, "Coding practice is not included")
        self.assertEqual(api.call_count, 1)

    @patch.object(service, "_api", side_effect=service.ResearchError("Research is temporarily unavailable."))
    def test_provider_failure_is_saved_and_cooled_down(self, api):
        self.assertEqual(self.client.post(self.start, self.data).status_code, 503)
        result = self.client.post(self.start, self.data)
        self.assertEqual(result.json()["status"], "failed")
        self.assertEqual(api.call_count, 1)
        job = HiringResearch.objects.get()
        job.expires_at = timezone.now() - timedelta(seconds=1)
        job.save()
        api.side_effect = None
        api.return_value = provider_report()
        self.assertEqual(self.client.post(self.start, self.data).json()["status"], "completed")

    @override_settings(HIRING_RESEARCH_USER_DAILY_LIMIT=1)
    @patch.object(service, "_api", return_value=provider_report())
    def test_quota_blocks_new_runs_but_allows_cached_result(self, api):
        self.assertEqual(self.client.post(self.start, self.data).status_code, 200)
        self.assertEqual(self.client.post(self.start, {**self.data, "company": "Other company"}).status_code, 429)
        self.assertEqual(self.client.post(self.start, self.data).status_code, 200)
        self.assertEqual(api.call_count, 1)

    @override_settings(HIRING_RESEARCH_SITE_DAILY_LIMIT=0)
    @patch.object(service, "_api")
    def test_site_budget_can_pause_new_runs(self, api):
        self.assertEqual(self.client.post(self.start, self.data).status_code, 429)
        api.assert_not_called()

    @patch.object(service, "_api")
    def test_pending_poll_is_throttled_and_stale_job_fails(self, api):
        api.return_value = {"status": "in_progress"}
        job = self.create_job(response_id="resp_test123")
        url = reverse("pages:hiring-research-status", args=[job.pk])
        self.assertEqual(self.client.get(url).status_code, 202)
        self.assertEqual(self.client.get(url).status_code, 202)
        self.assertEqual(api.call_count, 1)
        job.expires_at -= timedelta(minutes=11)
        job.created_at -= timedelta(minutes=11)
        job.save()
        self.assertEqual(self.client.get(url).json()["status"], "failed")
        self.assertEqual(api.call_count, 1)

    @patch.object(service, "_api")
    def test_status_requires_login_and_tenant_match(self, api):
        job = self.create_job()
        url = reverse("pages:hiring-research-status", args=[job.pk])
        with patch("backend.apps.pages.student._research_tenant_id", return_value=999999):
            self.assertEqual(self.client.get(url).status_code, 404)
            page = self.client.get(reverse("pages:company-lookup"), {"report": job.pk})
            self.assertNotIn("research_job", page.context)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 401)
        api.assert_not_called()

    def test_untraceable_and_unsafe_evidence_is_removed(self):
        response = alter_report(provider_report(), lambda report: report["stages"][0].update(
            source_urls=["https://invented.example/process", "javascript:alert(1)"]))
        report = service.parse_report(response, 3)
        self.assertEqual(report["stages"], [])
        self.assertEqual(len(report["experiences"]), 1)
        self.assertTrue(any("omitted" in gap for gap in report["gaps"]))
        for url in ("javascript:alert(1)", "http://127.0.0.1/test", "http://user:pass@example.com", "http://foo.local/x"):
            self.assertFalse(service._public_url(url))

    def test_fabricated_tracks_invalid_days_and_missing_search_rejected(self):
        mutations = [
            lambda report: report["plan"][0].update(practice_keys=["coding_test"]),
            lambda report: report["plan"][0].update(day=2),
            lambda report: report.update(stages="not a list"),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(service.ResearchError):
                service.parse_report(alter_report(provider_report(), mutation), 3)
        response = provider_report()
        response["output"].pop(0)
        with self.assertRaises(service.ResearchError):
            service.parse_report(response, 3)

    @patch.object(service, "_api", return_value=provider_report())
    def test_role_punctuation_does_not_conflate_different_languages(self, api):
        first = self.client.post(self.start, {**self.data, "role": "C++ developer"})
        second = self.client.post(self.start, {**self.data, "role": "C# developer"})
        self.assertNotEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(api.call_count, 2)

    @patch.object(service, "_api")
    def test_cache_failure_prevents_paid_request(self, api):
        with patch.object(service.cache, "add", side_effect=OSError("Cache offline")):
            self.assertEqual(self.client.post(self.start, self.data).status_code, 503)
        api.assert_not_called()

    def test_malformed_provider_envelopes_fail_without_server_error(self):
        for response in ({}, {"output": None}, {"output": [None]},
                         {"output": [{"type": "message", "content": [{"type": "output_text", "text": None}]}]}):
            with self.subTest(response=response), self.assertRaises(service.ResearchError):
                service.parse_report(response, 3)

    def test_no_evidence_yields_general_plan_with_explicit_gap(self):
        response = provider_report()
        response["output"][0]["action"]["sources"] = []
        report = service.parse_report(response, 3)
        self.assertFalse(report["stages"])
        self.assertFalse(report["experiences"])
        self.assertTrue(any("general preparation" in gap for gap in report["gaps"]))

    def test_external_and_model_text_is_escaped(self):
        report = service.parse_report(provider_report(), 3)
        report["stages"][0]["title"] = '<script>alert("x")</script>'
        report["stages"][0]["sources"][0]["title"] = '<img src=x onerror=alert(1)>'
        job = self.create_job(status="completed", report=report, checked_at=timezone.now())
        response = self.client.get(reverse("pages:hiring-research-status", args=[job.pk]))
        html = response.json()["html"]
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<img src=x", html)

    def test_practice_links_respect_current_catalogue(self):
        report = service.parse_report(provider_report(), 3)
        job = self.create_job(status="completed", report=report)
        with patch("backend.apps.pages.student._track_titles", return_value={}):
            response = self.client.get(reverse("pages:hiring-research-status", args=[job.pk]))
        self.assertNotIn('/practice/shl_verify/', response.json()["html"])
        self.assertIn("No suitable practice tracks", response.json()["html"])
        self.assertTrue(HiringResearch.objects.get(pk=job.pk).report["practice"])

    @patch.object(service, "_api")
    def test_browsing_never_starts_paid_research_and_alias_search_works(self, api):
        EmployerAssessment.objects.create(company="J.P. Morgan", industry="Banking", assessment_types=["ccat"],
                                          source_url="https://example.com/careers", source_label="Careers",
                                          verified_on=timezone.localdate(), is_published=True)
        page = self.client.get(reverse("pages:company-lookup"), {"q": "JP morgan", "role": "Engineer"})
        self.assertContains(page, "J.P. Morgan")
        api.assert_not_called()
        self.assertEqual(self.client.get(reverse("pages:company-lookup"), {"report": "bad-uuid"}).status_code, 200)

    @patch("backend.apps.pages.hiring_research.urlopen")
    def test_rest_transport_does_not_expose_provider_errors(self, urlopen):
        from urllib.error import HTTPError
        urlopen.side_effect = HTTPError(service.API_URL, 401, "sensitive provider detail", {}, None)
        with self.assertRaisesMessage(service.ResearchError, "temporarily unavailable") as caught:
            service._api("POST", payload={"test": True})
        self.assertNotIn("sensitive", str(caught.exception))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, service.API_URL)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 20)

    @patch.object(service, "_api", return_value=provider_report(7))
    def test_company_role_only_defaults_to_seven_days(self, api):
        result = self.client.post(self.start, {"company": "JPMorgan", "role": "Engineer"})
        self.assertEqual(result.json()["status"], "completed")
        job = HiringResearch.objects.get()
        self.assertEqual(job.prep_days, 7)
        self.assertGreater(job.expires_at, timezone.now() + timedelta(days=6))

    @patch.object(service, "_api")
    def test_missing_tests_are_saved_once_and_existing_tests_have_links(self, api):
        assessments = [
            {"name": "HackerRank coding assessment", "reason": "Reported coding round.", "source_urls": ["https://example.com/interview"]},
            {"name": "SHL Verify", "reason": "Reported reasoning assessment.", "source_urls": ["https://example.com/careers"]},
        ]
        api.return_value = alter_report(provider_report(), lambda report: report.update(assessments=assessments))
        result = self.client.post(self.start, self.data)
        self.assertEqual(result.json()["status"], "completed")
        html = result.json()["html"]
        self.assertIn("Use this test", html)
        self.assertIn("Saved to our test suggestions", html)
        suggestion = TestSuggestion.objects.get()
        self.assertEqual(suggestion.requested_test, "HackerRank coding assessment")
        self.assertIn("https://example.com/interview", suggestion.message)
        self.assertFalse(suggestion.email)
        self.assertFalse(AudienceContact.objects.filter(email="").exists())
        cached = self.client.post(self.start, self.data)
        self.assertTrue(cached.json()["cached"])
        self.assertEqual(api.call_count, 1)
        self.client.post(self.start, {**self.data, "role": "Senior software engineer"})
        self.assertEqual(TestSuggestion.objects.count(), 1)

    @patch.object(service, "_api")
    def test_untraceable_assessments_are_not_added_as_suggestions(self, api):
        api.return_value = alter_report(provider_report(), lambda report: report.update(assessments=[{
            "name": "Invented test", "reason": "Unsupported claim", "source_urls": ["https://invented.example/test"],
        }]))
        self.client.post(self.start, self.data)
        self.assertFalse(TestSuggestion.objects.exists())

    @patch.object(service, "_api")
    def test_existing_manual_suggestion_is_reused_without_changing_review(self, api):
        suggestion = TestSuggestion.objects.create(tenant_id=self.tenant_id, requested_test="New Test", email="", status="planned")
        api.return_value = alter_report(provider_report(), lambda report: report.update(assessments=[{
            "name": "new test", "reason": "Reported assessment", "source_urls": ["https://example.com/careers"],
        }]))
        self.client.post(self.start, self.data)
        self.assertEqual(TestSuggestion.objects.count(), 1)
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, "planned")

    @patch.object(service, "_api")
    def test_new_catalogue_track_is_recognized_in_cached_guide_without_search(self, api):
        from backend.apps.assessments.models import AssessmentTrack
        api.return_value = alter_report(provider_report(), lambda report: report.update(assessments=[{
            "name": "New Reasoning Test", "reason": "Reported assessment", "source_urls": ["https://example.com/careers"],
        }]))
        self.client.post(self.start, self.data)
        AssessmentTrack.objects.create(assessment_type="new_reasoning", title="New Reasoning Test", tenant_id=self.tenant_id)
        cached = self.client.post(self.start, self.data)
        self.assertIn("Already in our catalogue", cached.json()["html"])
        self.assertNotIn("Saved to our test suggestions", cached.json()["html"])
        self.assertEqual(api.call_count, 1)
        self.assertEqual(TestSuggestion.objects.count(), 1)

    def test_page_has_two_fields_and_one_guide_button(self):
        page = self.client.get(reverse("pages:company-lookup"))
        self.assertContains(page, 'name="company"')
        self.assertContains(page, 'name="role"')
        self.assertContains(page, "Get your prep guide")
        self.assertNotContains(page, "AI search")

    def test_tracking_parameters_do_not_hide_official_evidence(self):
        raw = alter_report(provider_report(), lambda report: report.update(assessments=[{
            "name": "General Intelligence Assessment (GIA)", "reason": "Required assessment.",
            "source_urls": ["https://example.com/careers"],
        }]))
        raw["output"][0]["action"]["sources"][0]["url"] = "https://example.com/careers?utm_campaign%3Azalo=&utm_medium%3Azalo=&utm_source%3Azalo="
        report = service.parse_report(raw, 3)
        self.assertEqual(len(report["stages"]), 1)
        self.assertEqual(report["assessments"][0]["sources"][0]["url"], "https://example.com/careers")

    def test_source_matching_preserves_meaningful_query_parameters(self):
        raw = provider_report()
        raw["output"][0]["action"]["sources"][0]["url"] = "https://example.com/careers?role=engineer&utm_source=search"
        raw = alter_report(raw, lambda report: report["stages"][0].update(source_urls=["https://example.com/careers?role=recruiter"]))
        self.assertEqual(service.parse_report(raw, 3)["stages"], [])

    @patch.object(service, "_api")
    def test_sourced_gia_is_recommended_and_linked_when_model_omits_practice(self, api):
        api.return_value = alter_report(provider_report(), lambda report: report.update(
            practice=[], plan=[{"day": day, "title": "Prepare", "tasks": ["Review your projects."], "practice_keys": []} for day in range(1, 4)],
            assessments=[{"name": "General Intelligence Assessment (GIA)", "reason": "Employer requires GIA.", "source_urls": ["https://example.com/careers"]}],
        ))
        result = self.client.post(self.start, {**self.data, "company": "Canonical"})
        self.assertEqual(result.json()["status"], "completed")
        self.assertIn('/practice/prepgia/', result.json()["html"])
        report = HiringResearch.objects.get().report
        self.assertEqual(report["practice"][0]["key"], "prepgia")
        self.assertIn("prepgia", report["plan"][0]["practice_keys"])
        self.assertFalse(TestSuggestion.objects.exists())

    def test_known_assessment_name_variants_map_to_existing_tracks(self):
        catalogue = service.assessment_catalogue(self.tenant_id)
        for name, key in [
            ("General Intelligence Assessment (GIA)", "prepgia"),
            ("Thomas International General Intelligence Assessment (GIA)", "prepgia"),
            ("Thomas Aptitude (GIA)", "prepgia"),
            ("Criteria Cognitive Aptitude Test (CCAT)", "ccat"),
            ("Proctored CCAT", "ccat"),
        ]:
            with self.subTest(name=name):
                self.assertEqual(catalogue[service.normalize_search(name)]["key"], key)

    @patch.object(service, "_api")
    def test_pg_missing_assessments_are_saved_without_confusing_another_ppa(self, api):
        from backend.apps.assessments.models import AssessmentTrack

        TestSuggestion.objects.create(tenant_id=self.tenant_id, email="", requested_test="Personality Profile Analysis (PPA)")
        names = ["Peak Performance Assessment (PPA)", "P&G Interactive Assessment"]
        raw = alter_report(provider_report(), lambda report: report.update(assessments=[{
            "name": name, "reason": "Listed in the employer hiring process.",
            "source_urls": ["https://www.pgcareers.com/global/en/hiring-process"],
        } for name in names]))
        raw["output"][0]["action"]["sources"].append({
            "url": "https://www.pgcareers.com/global/en/hiring-process", "title": "P&G hiring process",
        })
        api.return_value = raw
        track_count = AssessmentTrack.objects.count()
        data = {**self.data, "company": "Procter & Gamble", "role": "Brand manager"}
        response = self.client.post(self.start, data)
        self.assertEqual(response.json()["status"], "completed")
        self.assertIn("Saved to our test suggestions for future development", response.json()["html"])
        for name in names:
            saved = TestSuggestion.objects.get(tenant_id=self.tenant_id, requested_test=name)
            self.assertEqual(saved.source_page, "hiring-research")
            self.assertEqual(saved.status, "new")
            self.assertIn("https://www.pgcareers.com/global/en/hiring-process", saved.message)
        self.assertEqual(TestSuggestion.objects.count(), 3)
        self.assertEqual(AssessmentTrack.objects.count(), track_count)
        repeated = self.client.post(self.start, data)
        self.assertTrue(repeated.json()["cached"])
        self.assertEqual(TestSuggestion.objects.count(), 3)
        api.assert_called_once()


@override_settings(HIRING_RESEARCH_ENABLED=True, OPENAI_API_KEY="test-key", HIRING_RESEARCH_MODEL="gpt-6-luna")
class HiringLocationAndNewTracksTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(email="location@example.com", password="pass12345")
        self.client.force_login(self.user)
        self.url = reverse("pages:hiring-research-start")
        self.data = {"company": "Deloitte", "role": "Graduate analyst", "prep_days": 3}

    @patch.object(service, "_api", return_value=provider_report())
    def test_location_is_sent_to_provider_and_separates_cached_guides(self, api):
        uk = self.client.post(self.url, {**self.data, "location": "United Kingdom"})
        india = self.client.post(self.url, {**self.data, "location": "India"})
        self.assertEqual(uk.status_code, 200)
        self.assertEqual(india.status_code, 200)
        self.assertNotEqual(uk.json()["id"], india.json()["id"])
        self.assertEqual(json.loads(api.call_args.kwargs["payload"]["input"])["request"]["location"], "India")
        self.assertIn("strict research scope", api.call_args.kwargs["payload"]["instructions"])
        again = self.client.post(self.url, {**self.data, "location": "United Kingdom"})
        self.assertEqual(again.json()["id"], uk.json()["id"])
        self.assertEqual(api.call_count, 2)
        page = self.client.get(reverse("pages:company-lookup"), {"report": india.json()["id"]})
        self.assertContains(page, 'value="India" selected')

    @patch.object(service, "_api")
    def test_location_dropdown_has_no_fixed_default_and_rejects_unknown_values(self, api):
        page = self.client.get(reverse("pages:company-lookup"))
        self.assertContains(page, 'id="lookup-location"')
        self.assertContains(page, 'value="" selected')
        self.assertEqual(self.client.post(self.url, {**self.data, "location": "invalid-country"}).status_code, 400)
        api.assert_not_called()

    @patch.object(service, "_api")
    def test_generic_new_formats_match_playable_practice_without_suggestions(self, api):
        response = provider_report()
        names = ["Situational judgement test", "Job simulation", "Verbal reasoning test"]
        response = alter_report(response, lambda report: report.update(assessments=[
            {"name": name, "reason": "Named in the source.", "source_urls": ["https://example.com/careers"]}
            for name in names
        ]))
        api.return_value = response
        result = self.client.post(self.url, {**self.data, "location": "United Kingdom"})
        self.assertEqual(result.status_code, 200)
        for key in ("situational_judgement", "work_simulation", "verbal_reasoning"):
            self.assertIn(reverse("pages:assessment-practice", args=[key]), result.json()["html"])
        self.assertFalse(TestSuggestion.objects.exists())


    @override_settings(BILLING_TRUST_PROXY_COUNTRY_HEADERS=True)
    def test_network_country_initializes_dropdown_but_explicit_choice_wins(self):
        page = self.client.get(reverse("pages:company-lookup"), HTTP_CF_IPCOUNTRY="IN")
        self.assertContains(page, 'value="India" selected')
        page = self.client.get(reverse("pages:company-lookup"), {"location": "United Kingdom"}, HTTP_CF_IPCOUNTRY="IN")
        self.assertContains(page, 'value="United Kingdom" selected')
        page = self.client.get(reverse("pages:company-lookup"), {"location": ""}, HTTP_CF_IPCOUNTRY="IN")
        self.assertContains(page, 'value="" selected')
        self.assertContains(page, 'data-auto-location="false"')

    @patch("backend.apps.billing.regions._lookup_ip_country", return_value="CA")
    def test_public_ip_detection_selects_country_and_caches_lookup(self, lookup):
        for _ in range(2):
            page = self.client.get(reverse("pages:company-lookup"), REMOTE_ADDR="8.8.8.8")
            self.assertContains(page, 'value="Canada" selected')
        lookup.assert_called_once_with("8.8.8.8")

    def test_legacy_billing_fallback_does_not_become_a_location(self):
        session = self.client.session
        session["billing_country_code"] = "US"
        session.save()
        page = self.client.get(reverse("pages:company-lookup"))
        self.assertContains(page, 'value="" selected')
        self.assertContains(page, 'data-auto-location="true"')

    def test_last_search_location_is_retained_without_detection(self):
        session = self.client.session
        session["hiring_location"] = "Germany"
        session.save()
        page = self.client.get(reverse("pages:company-lookup"))
        self.assertContains(page, 'value="Germany" selected')
        self.assertContains(page, 'data-auto-location="false"')
