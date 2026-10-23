import json
import re

from django.test import SimpleTestCase

from prepgia.generators import (
    CCATSpatialGenerator,
    ReasoningGenerator,
    SpatialVisualizationGenerator,
)

SAMPLE_SIZE = 500


def _visual_key(option_visual: dict) -> str:
    return json.dumps({key: value for key, value in option_visual.items() if key != "value"}, sort_keys=True)


class CCATMatrixQuestionTests(SimpleTestCase):
    def test_matrix_options_are_visually_distinct(self):
        generator = CCATSpatialGenerator()
        for index in range(SAMPLE_SIZE):
            rule = generator._matrix_completion_rule(generator.rng(f"matrix-quality:{index}"))
            keys = [_visual_key(option) for option in rule["option_visuals"]]
            with self.subTest(seed=index):
                self.assertEqual(len(keys), 4)
                self.assertEqual(len(set(keys)), 4, "a distractor renders identically to another option")
                self.assertIn(rule["answer"], [option["value"] for option in rule["option_visuals"]])


class GIAReasoningQuestionTests(SimpleTestCase):
    UNGRAMMATICAL = re.compile(
        r"\bmore (fast|tall|strong|smart|rich|calm|kind|quick|sharp|brave|happy|busy)\b"
        r"|\bmost \w+\?"
    )

    def generate(self, index: int):
        return ReasoningGenerator().generate("medium", f"reasoning-quality:{index}")

    def test_statements_and_questions_use_correct_comparatives(self):
        for index in range(SAMPLE_SIZE):
            payload = self.generate(index).payload
            text = " ".join([*payload["prompt"]["statements"], payload["prompt"]["question"]])
            with self.subTest(text=text):
                self.assertIsNone(self.UNGRAMMATICAL.search(text))

    def test_answer_follows_from_the_statement(self):
        for index in range(SAMPLE_SIZE):
            generated = self.generate(index)
            statement = generated.payload["prompt"]["statements"][0]
            question = generated.payload["prompt"]["question"]
            first, second = generated.payload["options"]
            if not statement.startswith(first):
                first, second = second, first

            # Resolve who has more of the trait from the statement's wording.
            match = re.match(rf"{first} is (not as )?(.+?) (than|as) {second}\.", statement)
            self.assertIsNotNone(match, statement)
            negated, phrase = bool(match.group(1)), match.group(2)
            first_is_lesser = phrase.startswith("less ") or phrase in {
                "shorter", "lighter", "weaker", "slower", "younger", "sadder", "poorer", "quieter", "duller",
                "short", "light", "weak", "slow", "young", "sad", "poor", "quiet", "dull",
            }
            if negated:
                first_is_lesser = not first_is_lesser
            greater, lesser = (second, first) if first_is_lesser else (first, second)

            asked = question.removeprefix("Who is ").removeprefix("Which of them is ").rstrip("?")
            asks_for_lesser = asked.startswith("less ") or asked in {
                "shorter", "lighter", "weaker", "slower", "younger", "sadder", "poorer", "quieter", "duller",
            }
            with self.subTest(statement=statement, question=question):
                self.assertEqual(generated.correct_answer["answer"], lesser if asks_for_lesser else greater)

    def test_uses_not_as_wording(self):
        statements = [self.generate(index).payload["prompt"]["statements"][0] for index in range(SAMPLE_SIZE)]
        self.assertTrue(any(" is not as " in statement for statement in statements))


class GIASpatialVisualizationQuestionTests(SimpleTestCase):
    def test_second_figure_is_always_rotated(self):
        for index in range(SAMPLE_SIZE):
            pairs = SpatialVisualizationGenerator().generate("medium", f"spatial-quality:{index}").payload["prompt"]["letter_pairs"]
            for pair in pairs:
                with self.subTest(pair=pair):
                    self.assertIn(pair["rotation"], {90, 180, 270})

    def test_letters_have_no_reflection_symmetry(self):
        # A glyph that is mirror-symmetric looks unchanged when "mirrored",
        # which would make a different pair indistinguishable from a match.
        symmetric = set("AHIMOTUVWXYilmnouvwxz")
        self.assertFalse(symmetric & set(SpatialVisualizationGenerator.LETTERS))

    def test_answer_counts_matching_pairs(self):
        for index in range(SAMPLE_SIZE):
            generated = SpatialVisualizationGenerator().generate("medium", f"spatial-count:{index}")
            pairs = generated.payload["prompt"]["letter_pairs"]
            self.assertEqual(generated.correct_answer["answer"], str(sum(pair["same"] for pair in pairs)))
