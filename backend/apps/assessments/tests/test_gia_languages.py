from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from backend.apps.assessments import services
from backend.apps.assessments.i18n import TRANSLATIONS, localize
from backend.apps.assessments.models import WordMeaningItem
from backend.apps.assessments.tests.test_shl_and_quality_release import MemoryRedis
from backend.apps.tenants.models import Tenant, TenantType
from backend.apps.tenants.utils import reset_current_tenant_slug, set_current_tenant_slug
from prepgia import gia_languages as gl
from prepgia.generators import LOCALIZED_SECTION_TYPES, generate_question

GIA_SECTIONS = sorted(LOCALIZED_SECTION_TYPES)


class GiaGeneratorLanguageTests(TestCase):
    def test_every_section_generates_in_german_and_spanish(self):
        for language in ("de", "es"):
            for section in GIA_SECTIONS:
                for difficulty in ("easy", "medium", "hard"):
                    with self.subTest(language=language, section=section, difficulty=difficulty):
                        question = generate_question(section, difficulty, f"seed:{language}:{section}:{difficulty}", language=language)
                        prompt = question.payload["prompt"]
                        text = " ".join(
                            str(value) for value in prompt.values() if isinstance(value, str)
                        ) + " ".join(str(word) for word in prompt.get("statements", []) + prompt.get("words", []))
                        self.assertNotIn("{", text)
                        self.assertIn(str(question.correct_answer["answer"]), [str(o) for o in question.payload["options"]])

    def test_english_output_is_unchanged_by_default(self):
        for section in GIA_SECTIONS:
            self.assertEqual(
                generate_question(section, "medium", "same-seed").payload["prompt"]["explanation"],
                generate_question(section, "medium", "same-seed", language="en").payload["prompt"]["explanation"],
            )

    def test_german_reasoning_answer_follows_the_statement(self):
        for i in range(200):
            question = generate_question("reasoning", ["easy", "medium", "hard"][i % 3], f"de-{i}", language="de")
            statement = question.payload["prompt"]["statements"][0]
            self.assertTrue(statement.endswith("."))
            self.assertTrue(" ist " in statement and (" als " in statement or " wie " in statement))
            # The worked explanation names the answer that the key stores.
            self.assertTrue(question.payload["prompt"]["explanation"].endswith(f"{question.correct_answer['answer']}."))

    def test_spanish_reasoning_uses_one_gender_per_question(self):
        for i in range(200):
            question = generate_question("reasoning", ["easy", "medium", "hard"][i % 3], f"es-{i}", language="es")
            names = question.payload["options"]
            in_male = all(name in gl.ES_NAMES["m"] for name in names)
            in_female = all(name in gl.ES_NAMES["f"] for name in names)
            self.assertTrue(in_male or in_female, names)
            question_text = question.payload["prompt"]["question"]
            self.assertTrue(question_text.startswith("¿") and question_text.endswith("?"))
            if in_female and "Cuál" in question_text:
                self.assertIn("de las dos", question_text)

    def test_word_meaning_uses_the_language_bank(self):
        for language in ("de", "es"):
            self.assertGreater(WordMeaningItem.objects.filter(language=language, is_active=True).count(), 300)
            question = generate_question("word_meaning", "medium", f"wm-{language}", language=language)
            item = WordMeaningItem.objects.get(pk=question.payload["metadata"]["source_item_id"])
            self.assertEqual(item.language, language)
        english = generate_question("word_meaning", "medium", "wm-en")
        self.assertEqual(WordMeaningItem.objects.get(pk=english.payload["metadata"]["source_item_id"]).language, "en")


class GiaTranslationTableTests(TestCase):
    def test_both_languages_cover_the_same_strings(self):
        self.assertEqual(set(TRANSLATIONS["de"]), set(TRANSLATIONS["es"]))

    def test_placeholders_survive_translation(self):
        import re

        for language, table in TRANSLATIONS.items():
            for english, translated in table.items():
                with self.subTest(language=language, english=english):
                    self.assertEqual(sorted(re.findall(r"\{(\w+)\}", english)), sorted(re.findall(r"\{(\w+)\}", translated)))

    def test_gia_config_is_fully_translated(self):
        from backend.apps.assessments.config import ASSESSMENT_CONFIG

        config = ASSESSMENT_CONFIG["prepgia"]
        for module in config["modules"]:
            for language in ("de", "es"):
                localized = localize(module, language)
                for key in ("title", "description", "instruction"):
                    self.assertNotEqual(localized[key], module[key], (language, module["key"], key))
                for step in localized["help"]["steps"]:
                    self.assertNotIn(step, module["help"]["steps"], (language, module["key"]))


class GiaLanguagePageTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Language platform", slug="language-platform", primary_domain="lang.example.com",
            tenant_type=TenantType.PLATFORM, allowed_assessments=["prepgia", "ccat"],
        )
        self.user = get_user_model().objects.create_user(email="lang@example.com", password="test-pass", tenant=self.tenant)
        self.token = set_current_tenant_slug(self.tenant.slug)
        self.addCleanup(reset_current_tenant_slug, self.token)
        self.redis = MemoryRedis()
        redis_patch = patch("backend.apps.assessments.services._get_redis_client", return_value=self.redis)
        redis_patch.start()
        self.addCleanup(redis_patch.stop)

    def test_practice_page_switches_language_and_remembers_it(self):
        url = reverse("pages:assessment-practice", args=["prepgia"])
        german = self.client.get(url, {"lang": "de"})
        self.assertContains(german, "Gesamttest starten")
        self.assertContains(german, "Wortbedeutung")
        self.assertContains(german, '<html lang="de">', html=False)
        # The choice is remembered for the next GIA page.
        section = self.client.get(reverse("pages:assessment-section-detail", args=["prepgia", "reasoning"]))
        self.assertContains(section, "Übung starten")
        self.assertContains(section, 'id="player-i18n"', html=False)
        self.assertIn(" ist ", section.context["section"]["practice_previews"][0]["context_lines"][0])

    def test_english_and_other_tests_are_unaffected(self):
        english = self.client.get(reverse("pages:assessment-practice", args=["prepgia"]))
        self.assertContains(english, "Start full test")
        self.assertNotContains(english, 'id="player-i18n"', html=False)
        self.client.get(reverse("pages:assessment-practice", args=["prepgia"]), {"lang": "es"})
        ccat = self.client.get(reverse("pages:assessment-practice", args=["ccat"]))
        self.assertContains(ccat, "Start full test")
        self.assertNotContains(ccat, "language-switch", html=False)

    def test_section_test_attempts_are_kept_per_language(self):
        spanish = services.get_or_create_section_attempt(self.user, "number_speed_accuracy", assessment_type="prepgia", language="es")
        self.assertEqual(services.attempt_language(spanish), "es")
        previews = services.get_section_test_previews(spanish)
        self.assertEqual(previews[0]["summary"], gl.NUMBER_INSTRUCTION["es"])
        # Resuming in Spanish returns the same attempt; English starts its own.
        self.assertEqual(
            services.get_or_create_section_attempt(self.user, "number_speed_accuracy", assessment_type="prepgia", language="es").id,
            spanish.id,
        )

    def test_full_test_page_and_attempt_follow_the_language(self):
        self.client.force_login(self.user)
        url = reverse("pages:assessment-full-test", args=["prepgia"])
        response = self.client.get(url, {"lang": "es"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pantalla completa y empezar la prueba completa")
        self.assertContains(response, 'id="player-i18n"', html=False)
        attempt_id = response.context["full_test_attempt_id"]
        if attempt_id:
            from backend.apps.assessments.models import Attempt

            self.assertEqual(services.attempt_language(Attempt.objects.get(pk=attempt_id)), "es")

    def test_practice_page_full_test_summary_is_translated(self):
        response = self.client.get(reverse("pages:assessment-practice", args=["prepgia"]), {"lang": "de"})
        self.assertContains(response, "Alle Abschnitte direkt hintereinander")
        self.assertContains(response, " Fragen")
        self.assertNotContains(response, "Every section, back to back")
