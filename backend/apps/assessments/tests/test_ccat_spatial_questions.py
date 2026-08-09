from dataclasses import asdict

from django.test import SimpleTestCase

from backend.apps.assessments.services import _serialize_generated_question_for_player
from prepgia.generators import CCAT_SPATIAL_RULES, CCATSpatialGenerator


class CCATSpatialQuestionTests(SimpleTestCase):
    def test_every_rule_contains_a_solvable_visual_pattern(self):
        for rule in CCAT_SPATIAL_RULES:
            with self.subTest(question=rule["question"]):
                self.assertGreaterEqual(len(rule["stimulus"]), 3)
                self.assertEqual(len(rule["options"]), len(rule["option_visuals"]))
                self.assertEqual(
                    rule["options"],
                    [visual["value"] for visual in rule["option_visuals"]],
                )
                self.assertIn(rule["answer"], rule["options"])

    def test_generated_question_keeps_visual_data_in_player_payload(self):
        generated = CCATSpatialGenerator().generate("easy", "spatial-renderer-regression")

        preview = _serialize_generated_question_for_player(asdict(generated), include_correct_answer=True)

        self.assertEqual(preview["context_kind"], "ccat_spatial")
        self.assertTrue(preview["spatial_stimulus"])
        self.assertTrue(preview["option_visuals"])
        self.assertEqual(preview["reveal_mode"], "question_only")
        self.assertIn(preview["correct_answer"], preview["options"])
