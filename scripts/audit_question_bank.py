"""Repeatable structural sample audit; not an editorial or psychometric rating.

Run from the repository root, e.g.:
DJANGO_SETTINGS_MODULE=backend.config.test_settings python scripts/audit_question_bank.py --output /tmp/question-audit.json
"""

import argparse
from collections import Counter
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.test_settings")
import django

django.setup()
from prepgia.generators import GENERATOR_MAP  # noqa: E402 - Django must be initialised first
from prepgia.question_types import semantic_question_signature  # noqa: E402
from backend.apps.assessments.services import _serialize_generated_question_for_player  # noqa: E402

SECTIONS = [
    "shl_numerical",
    "shl_deductive",
    "shl_inductive",
    "consulting_math",
    "consulting_evidence",
    "consulting_case",
    "wg_inference",
    "wg_assumptions",
    "wg_deduction",
    "wg_interpretation",
    "wg_arguments",
    "linked_case",
]


def audit(samples):
    result = {
        "samples_per_difficulty": samples,
        "difficulty_levels": ["easy", "medium", "hard"],
        "sections": {},
        "limitations": [
            "Family labels describe implemented templates, not independently reviewed items.",
            "Exact task signatures detect repeats but numeric/context changes can overstate semantic variety.",
            "This checks structure, reproducibility and leakage, not predictive validity or publisher equivalence.",
        ],
    }
    for section in SECTIONS:
        families, answers, signatures, failures = Counter(), Counter(), set(), Counter()
        tier_signatures = {}
        examples = []
        visual_fixtures = []
        for difficulty in result["difficulty_levels"]:
            tier_signatures[difficulty] = []
            for index in range(samples):
                seed = f"competitor-audit:{index}"
                q = GENERATOR_MAP[section].generate(difficulty, seed)
                payload, prompt = q.payload, q.payload["prompt"]
                family = payload.get("metadata", {}).get("subtype", "unknown")
                # Case steps are not separate scenarios.
                family = (
                    family.split("_step_")[0]
                    if "_step_" in family
                    else "automation"
                    if family.startswith("case_step_")
                    else family
                )
                families[family] += 1
                answers[str(q.correct_answer["answer"])] += 1
                signature = semantic_question_signature(payload)
                signatures.add(signature)
                tier_signatures[difficulty].append(signature)
                options = payload["options"]
                failures["missing_key"] += q.correct_answer["answer"] not in options
                failures["duplicate_options"] += len(
                    {str(o).strip().casefold() for o in options}
                ) != len(options)
                failures["missing_explanation"] += not bool(prompt.get("explanation"))
                serialized = _serialize_generated_question_for_player(asdict(q), False)
                failures["answer_leak"] += any(
                    key in serialized for key in ("correct_answer", "explanation", "metadata")
                ) or bool(serialized.get("seed"))
                repeat = GENERATOR_MAP[section].generate(difficulty, seed)
                failures["not_reproducible"] += (
                    signature != semantic_question_signature(repeat.payload)
                    or q.correct_answer != repeat.correct_answer
                    or options != repeat.payload["options"]
                )
                if family == "compound_movement" and index < 24:
                    visual_fixtures.append(payload["option_visuals"])
                if index < 2 and difficulty == "hard":
                    examples.append(
                        {
                            "prompt": prompt,
                            "options": options,
                            "answer": q.correct_answer["answer"],
                            "family": family,
                        }
                    )
        result["sections"][section] = {
            "sample_count": samples * 3,
            "families": dict(sorted(families.items())),
            "unique_exact_tasks": len(signatures),
            "same_seed_easy_hard_changed": sum(
                a != b for a, b in zip(tier_signatures["easy"], tier_signatures["hard"])
            ),
            "checks_failed": dict(failures),
            "answer_distribution": dict(answers) if section.startswith("wg_") else None,
            "hard_examples": examples,
            "visual_fixtures": visual_fixtures,
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=180)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    report = audit(args.samples)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"Audited {len(SECTIONS) * args.samples * 3} questions across {len(SECTIONS)} modules: {args.output}"
    )
    for section, row in report["sections"].items():
        print(
            f"{section}: {len(row['families'])} families, {sum(row['checks_failed'].values())} structural failures"
        )
    sys.exit(bool(any(sum(row["checks_failed"].values()) for row in report["sections"].values())))
