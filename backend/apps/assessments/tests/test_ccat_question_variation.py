import json

from django.test import SimpleTestCase

from prepgia.generators import (
    CCATNumericalGenerator,
    CCATSpatialGenerator,
    CCATVerbalGenerator,
)


def question_signature(question):
    payload = dict(question.payload)
    payload.pop("question_id", None)
    return json.dumps(
        {"payload": payload, "correct_answer": question.correct_answer},
        sort_keys=True,
    )


class CCATQuestionVariationTests(SimpleTestCase):
    sample_size = 300

    def generate_sample(self, generator):
        return [
            generator.generate("medium", f"ccat-variation:{index}")
            for index in range(self.sample_size)
        ]

    def assert_valid_options(self, questions):
        for question in questions:
            with self.subTest(seed=question.seed):
                options = question.payload["options"]
                self.assertEqual(len(options), 4)
                self.assertEqual(len(set(options)), 4)
                self.assertIn(question.correct_answer["answer"], options)

    def test_numerical_questions_cover_all_problem_families(self):
        questions = self.generate_sample(CCATNumericalGenerator())

        self.assert_valid_options(questions)
        self.assertEqual(
            {question.payload["metadata"]["subtype"] for question in questions},
            {
                "series",
                "percentage",
                "discount",
                "ratio",
                "work_rate",
                "average",
                "equation",
                "distance",
                "fraction",
                "profit_loss",
                "conversion",
                "compound_change",
            },
        )
        self.assertGreater(len({question_signature(question) for question in questions}), 210)

    def test_verbal_questions_cover_all_problem_families(self):
        questions = self.generate_sample(CCATVerbalGenerator())

        self.assert_valid_options(questions)
        self.assertEqual(
            {question.payload["metadata"]["subtype"] for question in questions},
            {"analogy", "sentence_completion", "odd_one_out", "synonym", "antonym", "category", "definition", "cause_effect"},
        )
        self.assertGreater(len({question_signature(question) for question in questions}), 75)

    def test_spatial_questions_cover_parameterized_visual_rules(self):
        questions = self.generate_sample(CCATSpatialGenerator())

        self.assert_valid_options(questions)
        self.assertEqual(
            {question.payload["metadata"]["subtype"] for question in questions},
            {"rotation", "fill_rotation", "mirror", "polygon_growth", "shape_cycle", "dot_movement", "dot_count", "quadrant_fill", "size_growth", "bar_growth", "matrix_completion"},
        )
        self.assertGreater(len({question_signature(question) for question in questions}), 55)
        shapes = {
            visual["shape"]
            for question in questions
            for visual in [
                *question.payload["prompt"].get("stimulus", []),
                *question.payload.get("option_visuals", []),
            ]
            if visual["shape"] not in {"missing", "mirror_axis"}
        }
        self.assertGreaterEqual(len(shapes), 20)

    def test_practice_sized_batches_cycle_families_before_repeating(self):
        cases = (
            (CCATNumericalGenerator(), 12),
            (CCATVerbalGenerator(), 8),
            (CCATSpatialGenerator(), 11),
        )

        for generator, family_count in cases:
            with self.subTest(section=generator.section_type):
                questions = [
                    generator.generate(
                        "easy",
                        f"section:{generator.section_type}:practice:easy:session:{index}",
                    )
                    for index in range(family_count)
                ]
                subtypes = [
                    question.payload["metadata"]["subtype"] for question in questions
                ]
                self.assertEqual(family_count, len(set(subtypes)))

    def test_seeded_content_is_reproducible(self):
        for generator in (
            CCATNumericalGenerator(),
            CCATVerbalGenerator(),
            CCATSpatialGenerator(),
        ):
            with self.subTest(generator=generator.__class__.__name__):
                first = generator.generate("medium", "repeatable-seed")
                second = generator.generate("medium", "repeatable-seed")
                self.assertEqual(question_signature(first), question_signature(second))
