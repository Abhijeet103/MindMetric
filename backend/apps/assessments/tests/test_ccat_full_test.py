from django.test import SimpleTestCase

from backend.apps.assessments.config import (
    ASSESSMENT_CCAT,
    ASSESSMENT_PREPGIA,
    get_assessment_config,
    get_full_test_question_count,
)
from backend.apps.assessments.models import SectionType


class CCATFullTestConfigTests(SimpleTestCase):
    def test_ccat_is_one_fifty_question_fifteen_minute_assessment(self):
        config = get_assessment_config(ASSESSMENT_CCAT)
        section_counts = [
            get_full_test_question_count(ASSESSMENT_CCAT, SectionType.CCAT_NUMERICAL),
            get_full_test_question_count(ASSESSMENT_CCAT, SectionType.CCAT_VERBAL),
            get_full_test_question_count(ASSESSMENT_CCAT, SectionType.CCAT_SPATIAL),
        ]

        self.assertEqual(config["full_test_mode"], "mixed")
        self.assertEqual(config["full_test_duration_minutes"], 15)
        self.assertEqual(config["full_test_practice_count"], 0)
        self.assertEqual(section_counts, [17, 17, 16])
        self.assertEqual(sum(section_counts), 50)

    def test_gia_keeps_its_existing_staged_question_count(self):
        config = get_assessment_config(ASSESSMENT_PREPGIA)

        self.assertEqual(config["full_test_mode"], "staged")
        self.assertEqual(
            get_full_test_question_count(ASSESSMENT_PREPGIA, SectionType.REASONING),
            300,
        )
