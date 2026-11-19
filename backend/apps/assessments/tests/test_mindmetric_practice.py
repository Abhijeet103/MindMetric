from dataclasses import asdict
from django.test import TestCase
from django.urls import reverse
from backend.apps.assessments.config import ASSESSMENT_CONFIG
from backend.apps.assessments.services import _build_question_batch, _serialize_generated_question_for_player
from backend.apps.tenants.models import Tenant
from prepgia.generators import generate_question
from prepgia.question_types import semantic_question_signature


SECTIONS = ["sjt_workplace", "work_simulation", "verbal_passages", "aptitude_arithmetic", "aptitude_verbal", "aptitude_visual"]
TRACKS = ["situational_judgement", "work_simulation", "verbal_reasoning", "aptitude"]


class MindMetricPracticeTests(TestCase):
    def test_original_questions_render_and_hide_answers_in_timed_mode(self):
        for section in SECTIONS:
            for level in ("easy", "medium", "hard"):
                for index in range(40):
                    with self.subTest(section=section, level=level, index=index):
                        item = generate_question(section, level, f"quality:{section}:{level}:{index}")
                        self.assertIn(item.correct_answer["answer"], item.payload["options"])
                        self.assertEqual(len(item.payload["options"]), len(set(item.payload["options"])))
                        self.assertTrue(item.payload["prompt"]["explanation"])
                        preview = _serialize_generated_question_for_player(asdict(item), True)
                        self.assertTrue(preview["question_text"])
                        timed = _serialize_generated_question_for_player(asdict(item), False)
                        self.assertNotIn("correct_answer", timed)
                        self.assertNotIn("explanation", timed)

    def test_each_level_can_supply_a_paid_practice_batch(self):
        for section in SECTIONS:
            for level in ("easy", "medium", "hard"):
                with self.subTest(section=section, level=level):
                    batch = _build_question_batch("mindmetric-qa", section, "practice", 100, level)
                    self.assertEqual(len(batch), 100)
                    self.assertEqual(len({semantic_question_signature(q["payload"]) for q in batch}), 100)

    def test_simulation_shared_exhibit_and_independent_cost_answer(self):
        batch = _build_question_batch("linked-qa", "work_simulation", "test", 12, "hard")
        for start in range(0, 12, 4):
            group = batch[start:start+4]
            cases = [q["payload"]["prompt"]["case_study"] for q in group]
            self.assertEqual(len({c["id"] for c in cases}), 1)
            self.assertEqual([c["question_index"] for c in cases], [1, 2, 3, 4])
            rows = dict(group[0]["payload"]["prompt"]["data_table"]["rows"])
            shortage = int(rows["Units needed for today's dispatch"]) - int(rows["Physical units in stock"]) + int(rows["Units reserved for another confirmed order"])
            unit = int(rows["Supplier estimate per unit"][1:])
            self.assertEqual(float(group[1]["correct_answer"]["answer"]), shortage)
            self.assertEqual(float(group[2]["correct_answer"]["answer"]), ((shortage + 4)//5)*5*unit)

    def test_new_tracks_and_level_routes_are_playable(self):
        tenant = Tenant.objects.get(tenant_type="platform")
        tenant.allowed_assessments = list(ASSESSMENT_CONFIG)
        tenant.save(update_fields=["allowed_assessments"])
        for track in TRACKS:
            response = self.client.get(reverse("pages:assessment-practice", args=[track]))
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(b"CGL", response.content)
            for module in ASSESSMENT_CONFIG[track]["modules"]:
                url = reverse("pages:assessment-section-detail", args=[track, module["key"]])
                for level in ("easy", "medium", "hard", "invalid"):
                    page = self.client.get(url, {"level": level})
                    self.assertEqual(page.status_code, 200)
                    self.assertContains(page, "Foundation")
                    self.assertEqual(page.context["practice_level"], "easy" if level == "invalid" else level)

    def test_sjt_difficulty_introduces_authority_and_audit_constraints(self):
        easy = generate_question("sjt_workplace", "easy", "same:1")
        hard = generate_question("sjt_workplace", "hard", "same:1")
        self.assertNotIn("senior colleague", easy.payload["prompt"]["instruction"])
        self.assertIn("senior colleague", hard.payload["prompt"]["instruction"])
        self.assertIn("Record the decision", hard.correct_answer["answer"])
