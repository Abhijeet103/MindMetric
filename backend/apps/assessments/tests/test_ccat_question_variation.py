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
            },
        )
        self.assertGreater(len({question_signature(question) for question in questions}), 175)

    def test_verbal_questions_cover_all_problem_families(self):
        questions = self.generate_sample(CCATVerbalGenerator())

        self.assert_valid_options(questions)
        self.assertEqual(
            {question.payload["metadata"]["subtype"] for question in questions},
            {"analogy", "sentence_completion", "odd_one_out", "synonym", "antonym", "category"},
        )
        self.assertGreater(len({question_signature(question) for question in questions}), 45)

    def test_spatial_questions_cover_parameterized_visual_rules(self):
        questions = self.generate_sample(CCATSpatialGenerator())

        self.assert_valid_options(questions)
        self.assertEqual(
            {question.payload["metadata"]["subtype"] for question in questions},
            {"rotation", "fill_rotation", "mirror", "polygon_growth"},
        )
        self.assertGreater(len({question_signature(question) for question in questions}), 20)

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
