import itertools
from dataclasses import asdict
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from backend.apps.assessments import services
from backend.apps.assessments.config import get_assessment_config
from backend.apps.assessments.models import AttemptMode, FreeTierModuleLimit, WordMeaningItem
from backend.apps.tenants.models import Tenant, TenantType
from backend.apps.tenants.utils import set_current_tenant_slug, reset_current_tenant_slug
from prepgia.generators import GENERATOR_MAP, WordMeaningGenerator
from prepgia.question_types import semantic_question_signature


class GeneratedQualityTests(SimpleTestCase):
    def test_perceptual_format_is_four_pairs_at_every_difficulty(self):
        for difficulty in ("easy", "medium", "hard"):
            for i in range(60):
                q = GENERATOR_MAP["perceptual_speed"].generate(difficulty, f"format:{i}")
                self.assertEqual(len(q.payload["prompt"]["pairs"]), 4)
                self.assertEqual(q.payload["options"], [0, 1, 2, 3, 4])
                expected = sum(
                    p["left"].lower() == p["right"].lower() for p in q.payload["prompt"]["pairs"]
                )
                self.assertEqual(q.correct_answer["answer"], expected)

    def test_difficulty_changes_generated_content(self):
        for section, generator in GENERATOR_MAP.items():
            if section == "word_meaning":
                continue
            different = sum(
                semantic_question_signature(generator.generate("easy", f"tier:{i}").payload)
                != semantic_question_signature(generator.generate("hard", f"tier:{i}").payload)
                for i in range(100)
            )
            with self.subTest(section=section):
                self.assertGreater(different, 40)

    def test_serialized_test_questions_hide_answers_seeds_and_explanations(self):
        for section, generator in GENERATOR_MAP.items():
            if section == "word_meaning":
                continue
            for difficulty in ("easy", "medium", "hard"):
                for i in range(40):
                    q = generator.generate(difficulty, f"visibility:{i}")
                    payload = services._serialize_generated_question_for_player(asdict(q), False)
                    self.assertNotIn("correct_answer", payload)
                    self.assertNotIn("explanation", payload)
                    self.assertEqual(payload["seed"], "")
                    self.assertNotIn("metadata", payload)
                    practice = services._serialize_generated_question_for_player(asdict(q), True)
                    self.assertTrue(practice["explanation"])
                    self.assertIn(practice["correct_answer"], practice["options"])
                    self.assertEqual(len(payload["options"]), len(set(payload["options"])))
                    if section.startswith("shl_"):
                        self.assertEqual(payload["reveal_mode"], "question_only")

    def test_spatial_is_reproducible_after_interleaved_calls(self):
        generator = GENERATOR_MAP["ccat_spatial"]
        for i in range(100):
            q = generator.generate("medium", f"stable:{i}")
            for j in range(5):
                generator.generate("hard", f"other:{j}")
            repeated = generator.generate("medium", f"stable:{i}")
            self.assertEqual(
                semantic_question_signature(q.payload),
                semantic_question_signature(repeated.payload),
            )
            self.assertEqual(q.correct_answer, repeated.correct_answer)
            self.assertEqual(q.payload["options"], ["A", "B", "C", "D"])

    def test_spatial_test_prompts_do_not_disclose_pattern_rules(self):
        for i in range(150):
            q = GENERATOR_MAP["ccat_spatial"].generate("medium", f"hints:{i}")
            prompt = q.payload["prompt"]
            self.assertNotRegex(
                prompt["question"] + prompt["instruction"],
                r"adding|clockwise|each row|each column|increasing|grows",
            )
            if q.payload["metadata"]["subtype"] == "shape_cycle":
                self.assertEqual(len(prompt["stimulus"]), 8)
                self.assertEqual(prompt["stimulus"][0], prompt["stimulus"][4])

    def test_shl_numerical_answers_derive_from_the_displayed_table(self):
        generator = GENERATOR_MAP["shl_numerical"]
        covered = set()
        for difficulty in ("easy", "medium", "hard"):
            for i in range(120):
                q = generator.generate(difficulty, f"numeric:{i}")
                rows = q.payload["prompt"]["data_table"]["rows"]
                _, prior, current, price, _ = rows[0]
                subtype = q.payload["metadata"]["subtype"]
                covered.add(subtype)
                if subtype == "growth":
                    expected = 100 * (current / prior - 1)
                elif subtype == "share":
                    expected = 100 * current / sum(row[2] for row in rows)
                elif subtype == "profit":
                    expected = sum(row[2] * row[3] for row in rows) - sum(
                        row[2] * row[4] for row in rows
                    )
                elif subtype == "weighted_average":
                    expected = sum(row[2] * row[3] for row in rows) / sum(row[2] for row in rows)
                elif subtype == "ratio":
                    expected = current / rows[1][2]
                else:
                    expected = current * price - rows[1][2] * rows[1][3]
                self.assertAlmostEqual(
                    float(q.correct_answer["answer"]), round(expected, 2), places=2
                )
        self.assertEqual(covered, set(generator.FAMILIES))

    def test_shl_ordering_has_one_solution_by_exhaustive_search(self):
        for i in range(120):
            q = GENERATOR_MAP["shl_deductive"].generate("hard", f"logic:{i}")
            meta = q.payload["metadata"]
            if meta["subtype"] not in {"ordering", "scheduling"}:
                continue
            solutions = [
                order
                for order in itertools.permutations(meta["people"])
                if all(order.index(a) < order.index(b) for a, b in meta["constraints"])
            ]
            self.assertEqual(len(solutions), 1)
            self.assertEqual(q.correct_answer["answer"], solutions[0][meta["rank"]])

    def test_full_test_batches_are_distinct_and_mix_difficulties(self):
        for assessment in ("ccat", "shl_verify"):
            config = get_assessment_config(assessment)
            for module in config["modules"]:
                questions = services._build_question_batch(
                    42,
                    module["key"],
                    "test",
                    config["full_test_question_counts"][module["key"]],
                    "mixed",
                )
                self.assertEqual(
                    len(questions),
                    len({semantic_question_signature(q["payload"]) for q in questions}),
                )
                self.assertEqual({q["difficulty"] for q in questions}, {"easy", "medium", "hard"})


class MemoryRedis:
    def __init__(self):
        self.data = {}

    def setex(self, key, ttl, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

    def exists(self, key):
        return key in self.data

    def expire(self, key, ttl):
        return key in self.data

    def delete(self, key):
        return self.data.pop(key, None) is not None


class SHLPracticeIntegrationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Quality platform",
            slug="quality-platform",
            primary_domain="quality.example.com",
            tenant_type=TenantType.PLATFORM,
            allowed_assessments=["prepgia", "ccat", "shl_verify"],
        )
        self.user = get_user_model().objects.create_user(
            email="quality@example.com", password="test-pass", tenant=self.tenant
        )
        self.token = set_current_tenant_slug(self.tenant.slug)
        self.addCleanup(reset_current_tenant_slug, self.token)
        self.redis = MemoryRedis()
        redis_patch = patch(
            "backend.apps.assessments.services._get_redis_client", return_value=self.redis
        )
        redis_patch.start()
        self.addCleanup(redis_patch.stop)

    def test_word_bank_is_seeded_reproducible_and_has_worked_explanations(self):
        generator = WordMeaningGenerator()
        for difficulty in ("easy", "medium", "hard"):
            self.assertGreaterEqual(
                WordMeaningItem.objects.filter(
                    difficulty=difficulty, is_active=True, explanation__gt=""
                ).count(),
                180,
            )
            first = generator.generate(difficulty, "repeat-word:0")
            repeated = generator.generate(difficulty, "repeat-word:0")
            self.assertEqual(first.correct_answer, repeated.correct_answer)
            self.assertEqual(first.payload["prompt"], repeated.payload["prompt"])
            self.assertEqual(
                first.payload["metadata"]["source_item_id"],
                repeated.payload["metadata"]["source_item_id"],
            )
            self.assertTrue(first.payload["prompt"]["explanation"])
        questions = services._build_question_batch(123, "word_meaning", "test", 180, "medium")
        self.assertEqual(len({semantic_question_signature(q["payload"]) for q in questions}), 180)

    def test_shl_practice_pages_and_catalogue(self):
        response = self.client.get("/practice/shl_verify/", HTTP_HOST=self.tenant.primary_domain)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SHL-style Reasoning")
        for module in get_assessment_config("shl_verify")["modules"]:
            response = self.client.get(
                reverse("pages:assessment-section-detail", args=["shl_verify", module["key"]]),
                HTTP_HOST=self.tenant.primary_domain,
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, module["title"])
        response = self.client.get("/api/tests/sections/", HTTP_HOST=self.tenant.primary_domain)
        self.assertEqual(
            len([m for m in response.json()["sections"] if m["assessment_type"] == "shl_verify"]), 3
        )

    def test_shl_full_test_payload_scoring_and_progress(self):
        attempt = services.get_or_create_full_test_attempt(self.user, "shl_verify")
        self.assertEqual(attempt.sections.count(), 3)
        submitted = []
        for index, section in enumerate(attempt.sections.order_by("order_index")):
            payload = services.get_full_test_section_payload(attempt, index)
            self.assertEqual(len(payload["test_questions"]), 8)
            self.assertFalse(payload["practice_questions"])
            self.assertNotIn("correct_answer", payload["test_questions"][0])
            session = services._load_full_test_session(attempt.id)
            questions = session["sections"][index]["test_questions"]
            submitted.append(
                {
                    "section_id": section.id,
                    "answers": [
                        {"question_index": n, "selected_option": str(q["correct_answer"]["answer"])}
                        for n, q in enumerate(questions)
                    ],
                }
            )
        result = services.submit_full_test_attempt(attempt, submitted)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, "completed")
        self.assertTrue(result)
        for section in attempt.sections.all():
            self.assertEqual(section.correct_answers_count, 8)
            self.assertEqual(section.incorrect_answers_count, 0)

    def test_section_tests_use_configured_question_count_and_free_limit(self):
        FreeTierModuleLimit.objects.create(
            tenant=self.tenant,
            assessment_type="shl_verify",
            section_type="shl_numerical",
            test_attempt_limit=1,
        )
        attempt = services.get_or_create_section_attempt(self.user, "shl_numerical")
        self.assertEqual(attempt.sections.get().question_count, 12)
        previews = services.get_section_test_previews(attempt)
        self.assertEqual(len(previews), 12)
        self.assertTrue(previews[0]["data_table"])
        self.assertFalse(
            services.can_start_attempt(
                self.user,
                AttemptMode.SECTION,
                assessment_type="shl_verify",
                section_type="shl_numerical",
            ).allowed
        )

    def test_mismatched_assessment_cannot_start_a_module(self):
        decision = services.can_start_attempt(
            self.user, AttemptMode.SECTION, assessment_type="ccat", section_type="shl_numerical"
        )
        self.assertFalse(decision.allowed)

    def test_release_migration_preserves_institution_allocation_and_custom_words(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        from backend.apps.assessments.models import AssessmentTrack

        institution = Tenant.objects.create(
            name="Private allocation",
            slug="private-allocation",
            subdomain_prefix="private-allocation",
            tenant_type=TenantType.INSTITUTION,
            allowed_assessments=["ccat"],
        )
        custom = WordMeaningItem.objects.create(
            pair_word_1="joyful",
            pair_word_2="cheerful",
            odd_word="cautious",
            difficulty="medium",
            explanation="An administrator's original item.",
        )
        self.tenant.allowed_assessments = ["prepgia", "ccat"]
        self.tenant.save(update_fields=["allowed_assessments"])
        migration = import_module(
            "backend.apps.assessments.migrations.0016_reviewed_word_meanings_and_shl_release"
        )
        migration.release_content(apps, SimpleNamespace(connection=connection))
        self.tenant.refresh_from_db()
        institution.refresh_from_db()
        custom.refresh_from_db()
        self.assertIn("shl_verify", self.tenant.allowed_assessments)
        self.assertNotIn("shl_verify", institution.allowed_assessments)
        self.assertTrue(custom.is_active)
        track = AssessmentTrack.objects.get(tenant=self.tenant, assessment_type="shl_verify")
        self.assertEqual(track.visibility_state, "accessible")
        self.assertEqual(track.module_count, 3)

    def test_unallocated_institution_cannot_open_shl(self):
        institution = Tenant.objects.create(
            name="Restricted",
            slug="restricted-quality",
            subdomain_prefix="restricted-quality",
            tenant_type=TenantType.INSTITUTION,
            allowed_assessments=["ccat"],
        )
        response = self.client.get("/practice/shl_verify/", HTTP_HOST=institution.primary_domain)
        self.assertEqual(response.status_code, 404)
