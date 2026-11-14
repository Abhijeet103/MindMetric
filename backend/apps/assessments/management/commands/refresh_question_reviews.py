"""Create review snapshots without claiming that generated items are approved."""

from dataclasses import asdict
from django.core.management.base import BaseCommand
from prepgia.generators import GENERATOR_MAP
from backend.apps.assessments.models import EditorialReview
from backend.apps.assessments.quality import family_key

SECTIONS = [
    "shl_numerical",
    "shl_deductive",
    "shl_inductive",
    "consulting_math",
    "consulting_evidence",
    "consulting_case",
    "linked_case",
    "wg_inference",
    "wg_assumptions",
    "wg_deduction",
    "wg_interpretation",
    "wg_arguments",
]


class Command(BaseCommand):
    help = "Refresh editorial snapshots of new question families; changed content returns to needs-review. Does not approve content."

    def handle(self, *args, **options):
        created = changed = 0
        for section in SECTIONS:
            examples = {}
            for difficulty in ("easy", "medium", "hard"):
                found = set()
                for index in range(120):
                    q = asdict(
                        GENERATOR_MAP[section].generate(difficulty, f"editorial-snapshot:{index}")
                    )
                    family = family_key(q)
                    marker = (
                        (family, index % 4)
                        if section in {"consulting_case", "linked_case"}
                        else family
                    )
                    if marker in found:
                        continue
                    found.add(marker)
                    q["payload"].pop("question_id", None)
                    examples.setdefault(family, []).append(q)
            for family, rows in examples.items():
                key = f"template:{section}:{family}"
                content = {
                    "kind": "template",
                    "key": key,
                    "title": f"{section}: {family}",
                    "examples": rows,
                    "review_requirements": [
                        "Independently solve every key and challenge alternatives.",
                        "Review each distractor, wording, units and assumptions.",
                        "These are representative generated variants, not proof that every possible item is reviewed.",
                    ],
                }
                row, was_created = EditorialReview.objects.get_or_create(
                    content_key=key, defaults={"title": content["title"], "content": content}
                )
                created += was_created
                if not was_created and row.content != content:
                    row.content = content
                    if row.status != "withdrawn":
                        row.status = "needs_review"
                    row.reviewer = None
                    row.reviewed_at = None
                    row.save(update_fields=["content", "status", "reviewer", "reviewed_at"])
                    changed += 1
        self.stdout.write(
            f"Created {created} family review records; refreshed {changed}. No content was automatically approved."
        )
