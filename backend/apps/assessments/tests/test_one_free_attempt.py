from django.test import TestCase

from backend.apps.assessments.config import ASSESSMENT_CONFIG
from backend.apps.assessments.policies import resolve_test_configuration


class OneFreeAttemptTests(TestCase):
    def test_every_exam_allows_one_free_full_test_and_one_per_section(self):
        for assessment_type, config in ASSESSMENT_CONFIG.items():
            self.assertEqual(resolve_test_configuration(None, assessment_type)["free_full_test_attempts"], 1, assessment_type)
            for module in config["modules"]:
                policy = resolve_test_configuration(None, assessment_type, module["key"])
                self.assertEqual(policy["free_module_test_attempts"], 1, (assessment_type, module["key"]))
