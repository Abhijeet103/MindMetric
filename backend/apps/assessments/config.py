from __future__ import annotations

from backend.apps.assessments.models import SectionType
from prepgia.critical_scenarios import INSTRUCTIONS as CRITICAL_INSTRUCTIONS

ASSESSMENT_PREPGIA = "prepgia"
ASSESSMENT_CCAT = "ccat"
ASSESSMENT_WATSON_GLASER = "watson_glaser"
ASSESSMENT_SHL_VERIFY = "shl_verify"

ASSESSMENT_CONFIG = {
    ASSESSMENT_PREPGIA: {
        "slug": ASSESSMENT_PREPGIA,
        "title": "Thomas GIA",
        "eyebrow": "Thomas GIA practice platform",
        "description": "Thomas International GIA cognitive ability practice with timed tests and section-wise drills.",
        "full_test_title": "Full test",
        "full_test_description": "All five sections in one flow, designed to feel very close to the real GIA.",
        "full_test_meta_tail": "",
        "full_test_intro_copy": "Each section is shown one by one. First you get instructions, then eight practice questions with instant feedback, then the timed test for that section.",
        "full_test_practice_count": 8,
        "full_test_mode": "staged",
        "full_test_duration_minutes": 45,
        "module_label": "Modules",
        "modules": [
            {
                "key": SectionType.REASONING,
                "title": "Reasoning",
                "description": "Comparative and transitive logic questions under timed conditions.",
                "instruction": "Read the context statements first. Once you understand the relationship, reveal the question and choose the correct person or thing.",
                "time_limit_seconds": 300,
                "help": {
                    "task": "Remember a comparison, then answer a question about the relationship without seeing the original statement.",
                    "steps": [
                        "Identify the people or things being compared.",
                        "Restate the comparison in simpler words.",
                        "Keep the direction of the relationship clear when the question appears.",
                    ],
                    "watch_out": "Reversed or negative wording such as less careful instead of more careful.",
                    "tip": "Mentally place the stronger or greater item first before revealing the question.",
                },
            },
            {
                "key": SectionType.PERCEPTUAL_SPEED,
                "title": "Perceptual Speed",
                "description": "Fast letter-pair matching built to simulate GIA-style pressure.",
                "instruction": "Look at the letter pairs carefully. Count the matching pairs quickly before selecting the correct number.",
                "time_limit_seconds": 120,
                "help": {
                    "task": "Compare the letter pairs and count how many are exact matches.",
                    "steps": [
                        "Scan the pairs from left to right.",
                        "Compare both characters in each pair.",
                        "Keep a running count and answer once the row is complete.",
                    ],
                    "watch_out": "Do not count a pair when only one of its characters matches.",
                    "tip": "Use a steady scan rhythm instead of repeatedly checking earlier pairs.",
                },
            },
            {
                "key": SectionType.NUMBER_SPEED_ACCURACY,
                "title": "Number Speed & Accuracy",
                "description": "Find the number furthest from the median with speed and accuracy.",
                "instruction": "Review the three numbers, identify the middle value mentally, and choose the number furthest from it.",
                "time_limit_seconds": 120,
                "help": {
                    "task": "Find the middle value, then choose the number furthest away from it.",
                    "steps": [
                        "Order the three values from smallest to largest.",
                        "Identify the middle value.",
                        "Compare the distance from the middle to both outer values.",
                    ],
                    "watch_out": "The correct answer is not always the largest number.",
                    "tip": "Ignore the middle value after identifying it and compare only the two gaps.",
                },
            },
            {
                "key": SectionType.WORD_MEANING,
                "title": "Word Meaning",
                "description": "Odd-one-out vocabulary sets backed by a curated word bank.",
                "instruction": "Read the words shown in the context, spot the odd one out, and then choose it from the answer options.",
                "time_limit_seconds": 180,
                "help": {
                    "task": "Identify the word that does not belong with the others.",
                    "steps": [
                        "Look for a meaning or category shared by most words.",
                        "Test each word against that shared relationship.",
                        "Choose the word that falls outside the group.",
                    ],
                    "watch_out": "Do not choose a word only because it is less familiar.",
                    "tip": "Describe the shared group in one short phrase before selecting the odd word.",
                },
            },
            {
                "key": SectionType.SPATIAL_VISUALIZATION,
                "title": "Spatial Visualization",
                "description": "Decide whether abstract shapes are rotated matches or mirrored variants.",
                "instruction": "Study the shapes first, then decide whether they are the same when rotated or if one is mirrored.",
                "time_limit_seconds": 120,
                "help": {
                    "task": "Decide whether two shapes are the same after rotation or whether one has been mirrored.",
                    "steps": [
                        "Choose one distinctive corner, mark, or feature.",
                        "Mentally rotate the first shape to align that feature.",
                        "Check whether the remaining features keep the same arrangement.",
                    ],
                    "watch_out": "A mirrored shape cannot be matched by rotation alone.",
                    "tip": "Track an asymmetric feature rather than comparing the whole outline at once.",
                },
            },
        ],
    },
    ASSESSMENT_CCAT: {
        "slug": ASSESSMENT_CCAT,
        "title": "CCAT",
        "eyebrow": "CCAT aptitude practice platform",
        "description": "Criteria Cognitive Aptitude Test (CCAT) practice for numerical, verbal, logic, and spatial reasoning.",
        "full_test_title": "Full test",
        "full_test_description": "A realistic 50-question mixed aptitude test with one 15-minute time limit.",
        "full_test_meta_tail": "50 mixed questions",
        "full_test_intro_copy": "Answer 50 mixed numerical, verbal, logic, and spatial questions in 15 minutes. Questions appear in one continuous flow, just like the CCAT format.",
        "full_test_practice_count": 0,
        "full_test_mode": "mixed",
        "full_test_duration_minutes": 15,
        "full_test_question_counts": {
            SectionType.CCAT_NUMERICAL: 17,
            SectionType.CCAT_VERBAL: 17,
            SectionType.CCAT_SPATIAL: 16,
        },
        "module_label": "Modules",
        "modules": [
            {
                "key": SectionType.CCAT_NUMERICAL,
                "question_count": 30,
                "title": "Math & Numerical Reasoning",
                "description": "Fast quantitative reasoning with number series, ratios, percentages, and work-rate logic.",
                "instruction": "Read the question, work mentally where possible, and choose the best quantitative answer quickly.",
                "time_limit_seconds": 180,
                "help": {
                    "task": "Solve short numerical problems involving patterns, ratios, percentages, and practical arithmetic.",
                    "steps": [
                        "Identify the type of calculation the question requires.",
                        "Estimate the likely answer range.",
                        "Calculate only what is needed and eliminate unsuitable options.",
                    ],
                    "watch_out": "Avoid spending time on exact calculation when estimation separates the options.",
                    "tip": "Check units and direction before calculating.",
                },
            },
            {
                "key": SectionType.CCAT_VERBAL,
                "question_count": 30,
                "title": "Verbal Reasoning",
                "description": "Analogies, vocabulary, contextual language and conclusions from stated facts.",
                "instruction": "Read the prompt carefully, compare the options, and choose the strongest language-based answer.",
                "time_limit_seconds": 180,
                "help": {
                    "task": "Solve analogies, vocabulary, sentence logic, and word-group questions.",
                    "steps": [
                        "Identify the relationship or language rule being tested.",
                        "Predict the kind of answer you expect.",
                        "Compare that prediction with the available options.",
                    ],
                    "watch_out": "A plausible option may still fail to match the exact relationship.",
                    "tip": "State an analogy relationship as a short sentence before checking the answers.",
                },
            },
            {
                "key": SectionType.CCAT_SPATIAL,
                "question_count": 24,
                "title": "Spatial and Abstract Reasoning",
                "description": "Pattern recognition, transformations, and non-verbal logic questions.",
                "instruction": "Look for the transformation rule or pattern first, then choose the option that completes it best.",
                "time_limit_seconds": 180,
                "help": {
                    "task": "Identify a visual rule and choose the option that correctly continues or completes it.",
                    "steps": [
                        "Track changes in position, rotation, count, fill, and shape separately.",
                        "Form the simplest rule that explains the sequence.",
                        "Confirm that rule across every available step.",
                    ],
                    "watch_out": "Do not accept a rule that explains only the final two images.",
                    "tip": "Test one visual property at a time before combining multiple changes.",
                },
            },
        ],
    },
    ASSESSMENT_SHL_VERIFY: {
        "slug": ASSESSMENT_SHL_VERIFY,
        "title": "SHL-style Reasoning",
        "eyebrow": "Independent numerical, deductive and inductive practice",
        "description": "Original SHL-style reasoning questions with worked explanations. Independent practice, not an official or adaptive SHL assessment.",
        "full_test_title": "Mixed reasoning practice test",
        "full_test_description": "A fixed 24-question, 36-minute practice form covering three reasoning skills. This is not an adaptive SHL replica.",
        "full_test_meta_tail": "24 original questions · Fixed practice form",
        "full_test_intro_copy": "Answer 24 original numerical, deductive and inductive questions in 36 minutes. A calculator is allowed for numerical practice. This independent fixed form does not reproduce an official adaptive assessment.",
        "full_test_practice_count": 0,
        "full_test_mode": "mixed",
        "full_test_duration_minutes": 36,
        "full_test_question_counts": {
            SectionType.SHL_NUMERICAL: 8,
            SectionType.SHL_DEDUCTIVE: 8,
            SectionType.SHL_INDUCTIVE: 8,
        },
        "module_label": "Modules",
        "modules": [
            {
                "key": SectionType.SHL_NUMERICAL,
                "question_count": 12,
                "title": "Numerical Reasoning",
                "description": "Interpret business tables, percentage changes, weighted averages and contribution figures.",
                "instruction": "Use the table to answer the question. A calculator is allowed. Round to two decimal places where needed.",
                "time_limit_seconds": 720,
                "help": {
                    "task": "Make decisions from numerical data.",
                    "steps": [
                        "Check units and headings.",
                        "Identify the correct base or comparison.",
                        "Calculate only what the question asks.",
                    ],
                    "watch_out": "Revenue, contribution and units are different measures.",
                    "tip": "Write down the formula before entering values.",
                },
            },
            {
                "key": SectionType.SHL_DEDUCTIVE,
                "question_count": 12,
                "title": "Deductive Reasoning",
                "description": "Apply conditions, arrange appointments and draw conclusions from stated rules.",
                "instruction": "Use only the stated rules. Distinguish conclusions that must follow from those that are merely possible.",
                "time_limit_seconds": 720,
                "help": {
                    "task": "Find conclusions required by the given information.",
                    "steps": [
                        "Translate each rule.",
                        "Combine the constraints.",
                        "Check that the answer is necessary.",
                    ],
                    "watch_out": "If A implies B, B need not imply A.",
                    "tip": "Sketch an ordering chain for scheduling questions.",
                },
            },
            {
                "key": SectionType.SHL_INDUCTIVE,
                "question_count": 12,
                "title": "Inductive Reasoning",
                "description": "Discover visual rules in sequences, reflections and matrices.",
                "instruction": "Look for a rule consistent with all the figures and choose the missing figure.",
                "time_limit_seconds": 720,
                "help": {
                    "task": "Infer a visual rule from examples.",
                    "steps": [
                        "Track count, position, size and rotation.",
                        "Test the rule across the examples.",
                        "Eliminate figures that break it.",
                    ],
                    "watch_out": "A rule must explain all the figures.",
                    "tip": "Check one property at a time.",
                },
            },
        ],
    },
}


def _practice_track(key, title, description, modules, minutes):
    return {
        "slug": key, "title": title, "eyebrow": "Independent reasoning practice",
        "description": description, "full_test_title": "Full practice test",
        "full_test_description": description, "full_test_meta_tail": "Original questions",
        "full_test_intro_copy": "Use the information in each question and its exhibits. A calculator is allowed for business mathematics. This is independent practice material.",
        "full_test_practice_count": 0, "full_test_mode": "mixed", "full_test_duration_minutes": minutes,
        "full_test_question_counts": {module["key"]: 8 for module in modules},
        "module_label": "Modules", "modules": modules,
    }


def _module(key, title, description, case_group_size=1):
    return {"key": key, "title": title, "description": description, "instruction": "Use the passage, rules and exhibits to choose the best answer.", "time_limit_seconds": 600, "question_count": 12, "case_group_size": case_group_size,
            "help": {"task": description, "steps": ["Read the decision rule.", "Identify the relevant evidence.", "Check the conclusion against every constraint."], "watch_out": "Use only justified assumptions.", "tip": "Separate facts, assumptions and conclusions."}}


ASSESSMENT_CONFIG["consulting"] = _practice_track("consulting", "Consulting Problem Solving", "Charts, business mathematics, evidence evaluation and original short business cases.", [
    _module(SectionType.CONSULTING_MATH, "Charts & Business Mathematics", "Interpret exhibits, market sizing, pricing, margins, capacity and opportunity costs."),
    _module(SectionType.CONSULTING_EVIDENCE, "Evidence Evaluation", "Evaluate sampling, causal claims and evidence needed for business decisions."),
    _module(SectionType.CONSULTING_CASE, "Short Business Cases", "Solve four linked questions using a shared business case.", 4),
], 30)
ASSESSMENT_CONFIG[ASSESSMENT_WATSON_GLASER] = _practice_track(ASSESSMENT_WATSON_GLASER, "Watson–Glaser-style Critical Thinking", "Original passage-based inference, assumptions, deduction, interpretation and argument evaluation.", [
    _module(SectionType.WG_INFERENCE, "Inference", "Distinguish certainty, probability and missing information."),
    _module(SectionType.WG_ASSUMPTIONS, "Recognising Assumptions", "Identify assumptions necessary to a recommendation."),
    _module(SectionType.WG_DEDUCTION, "Deduction", "Decide whether conclusions logically follow from the stated rules."),
    _module(SectionType.WG_INTERPRETATION, "Interpretation", "Judge conclusions supported by the given evidence."),
    _module(SectionType.WG_ARGUMENTS, "Evaluating Arguments", "Judge the relevance and importance of arguments to the stated decision."),
], 30)
ASSESSMENT_CONFIG["consulting_cases"] = _practice_track("consulting_cases", "Consulting Case Practice", "Independent BCG/Bain-style case skills with shared exhibits and linked questions; original cases, not official replicas.", [
    _module(SectionType.LINKED_CASE, "Linked Case Sessions", "Evaluate automation, market entry and capacity decisions using shared exhibits, incremental economics and evidence.", 4),
], 30)
ASSESSMENT_CONFIG["consulting_cases"]["full_test_question_counts"][SectionType.LINKED_CASE] = 12

# Keep the learning guidance aligned with each section's actual decision rule.

_CRITICAL_TRAPS = {
    "inference": "Distinguish a population estimate from a fact about every individual; preference is not willingness to pay.",
    "assumptions": "A useful benefit need not be an assumption. Negate the proposed assumption and test the stated reason.",
    "deduction": "Necessary is not sufficient. All A are B does not imply all B are A or that any A exist.",
    "interpretation": "Changing group weights can reverse an overall rate. An observed improvement does not identify its cause.",
    "arguments": "An argument against a proposal may be strong. Check its relevance to the exact objective and constraints.",
}
for _critical_module in ASSESSMENT_CONFIG[ASSESSMENT_WATSON_GLASER]["modules"]:
    _skill = _critical_module["key"].removeprefix("wg_")
    _critical_module["instruction"] = CRITICAL_INSTRUCTIONS[_skill]
    _critical_module["help"].update(
        task=CRITICAL_INSTRUCTIONS[_skill], watch_out=_CRITICAL_TRAPS[_skill],
        tip="Use the explanation to identify the reasoning error, not just the correct option.",
    )


PRACTICE_TRACK_LIBRARY = {
    ASSESSMENT_PREPGIA: {
        "key": ASSESSMENT_PREPGIA,
        "title": "Thomas GIA",
        "description": "Thomas International GIA cognitive ability practice with timed tests and section-wise drills.",
        "module_count": len(ASSESSMENT_CONFIG[ASSESSMENT_PREPGIA]["modules"]),
        "trust_line": "Used by 30,000+ employers across the UK and Europe",
        "available_languages": ["English", "German (coming soon)"],
        "route_enabled": True,
        "default_visibility_state": "accessible",
    },
    ASSESSMENT_CCAT: {
        "key": ASSESSMENT_CCAT,
        "title": "CCAT",
        "description": "Criteria Cognitive Aptitude Test (CCAT) practice for numerical, verbal, logic, and spatial reasoning.",
        "module_count": len(ASSESSMENT_CONFIG[ASSESSMENT_CCAT]["modules"]),
        "trust_line": "Taken 10M+ times at 4,500+ US employers",
        "available_languages": ["English"],
        "route_enabled": True,
        "default_visibility_state": "accessible",
    },
    ASSESSMENT_WATSON_GLASER: {
        "key": ASSESSMENT_WATSON_GLASER,
        "title": "Watson-Glaser",
        "description": "Watson-Glaser Critical Thinking Appraisal (WGCTA) practice for inference, assumptions, deductions, and arguments.",
        "module_count": 4,
        "trust_line": "In testing with a small group right now",
        "available_languages": ["English"],
        "route_enabled": False,
        "default_visibility_state": "upcoming",
    },
    ASSESSMENT_SHL_VERIFY: {
        "key": ASSESSMENT_SHL_VERIFY,
        "title": "SHL-style Reasoning",
        "description": "Independent numerical, deductive and inductive reasoning practice with worked explanations.",
        "module_count": 3,
        "trust_line": "Original practice questions · Independent of SHL",
        "available_languages": ["English"],
        "route_enabled": True,
        "default_visibility_state": "accessible",
    },
}


for _key in ("consulting", "watson_glaser", "consulting_cases"):
    _config = ASSESSMENT_CONFIG[_key]
    PRACTICE_TRACK_LIBRARY[_key] = {"key": _key, "title": _config["title"], "description": _config["description"], "module_count": len(_config["modules"]), "trust_line": "Original questions · Independent practice", "available_languages": ["English"], "route_enabled": True, "default_visibility_state": "accessible"}


def get_assessment_config(assessment_type: str) -> dict:
    try:
        return ASSESSMENT_CONFIG[assessment_type]
    except KeyError as exc:
        raise KeyError(f"Unsupported assessment type: {assessment_type}") from exc


def get_assessment_module_keys(assessment_type: str) -> list[str]:
    return [module["key"] for module in get_assessment_config(assessment_type)["modules"]]


def get_module_meta(section_type: str) -> dict:
    for assessment_type, config in ASSESSMENT_CONFIG.items():
        for module in config["modules"]:
            if module["key"] == section_type:
                enriched = dict(module)
                enriched["assessment_type"] = assessment_type
                return enriched
    raise KeyError(f"Unsupported section type: {section_type}")


def get_module_assessment_type(section_type: str) -> str:
    return get_module_meta(section_type)["assessment_type"]


def get_time_limit_seconds(section_type: str) -> int:
    return int(get_module_meta(section_type)["time_limit_seconds"])


def get_full_test_question_count(assessment_type: str, section_type: str) -> int:
    config = get_assessment_config(assessment_type)
    configured_counts = config.get("full_test_question_counts", {})
    return int(configured_counts.get(section_type, get_time_limit_seconds(section_type)))


def get_assessment_cards() -> list[dict]:
    cards = []
    for key, config in PRACTICE_TRACK_LIBRARY.items():
        cards.append(
            {
                "key": key,
                **config,
            }
        )
    return cards


def get_section_question_count(section_type: str) -> int:
    return int(
        get_module_meta(section_type).get("question_count", get_time_limit_seconds(section_type))
    )
