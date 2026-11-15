from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import uuid

from backend.apps.assessments.models import WordMeaningItem
from prepgia.verbal_bank import VERBAL_BANK, unrelated_entries
from prepgia import gia_languages as gl
from prepgia.question_types import (
    BaseQuestionGenerator,
    GeneratedQuestion,
    _choose_batch_balanced_variant,
    _format_ccat_number,
    _build_ccat_number_options,
)
from prepgia.shl_generators import SHLDeductiveGenerator, SHLNumericalGenerator
from prepgia.consulting_generators import (
    ConsultingMathGenerator,
    ConsultingEvidenceGenerator,
    ConsultingShortCaseGenerator,
    CriticalThinkingGenerator,
    LinkedCaseGenerator,
)

SECTION_TYPES = [
    "reasoning",
    "perceptual_speed",
    "number_speed_accuracy",
    "word_meaning",
    "spatial_visualization",
    "ccat_numerical",
    "ccat_verbal",
    "ccat_spatial",
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

# (greater comparative, lesser comparative, greater adjective, lesser adjective).
# The lesser adjective is None where "not as ... as" would read unnaturally.
COMPARATIVE_TRAITS = [
    ("taller", "shorter", "tall", "short"),
    ("heavier", "lighter", "heavy", "light"),
    ("stronger", "weaker", "strong", "weak"),
    ("faster", "slower", "fast", "slow"),
    ("older", "younger", "old", "young"),
    ("happier", "sadder", "happy", "sad"),
    ("richer", "poorer", "rich", "poor"),
    ("louder", "quieter", "loud", "quiet"),
    ("brighter", "duller", "bright", "dull"),
    ("busier", "less busy", "busy", None),
    ("calmer", "less calm", "calm", None),
    ("braver", "less brave", "brave", None),
    ("kinder", "less kind", "kind", None),
    ("more careful", "less careful", "careful", None),
    ("more creative", "less creative", "creative", None),
    ("more curious", "less curious", "curious", None),
    ("more generous", "less generous", "generous", None),
    ("more organized", "less organized", "organized", None),
    ("more patient", "less patient", "patient", None),
    ("more confident", "less confident", "confident", None),
    ("more reliable", "less reliable", "reliable", None),
    ("more thoughtful", "less thoughtful", "thoughtful", None),
]
NAMES = [
    "Tom",
    "Robert",
    "Chloe",
    "Charles",
    "Maya",
    "Noah",
    "Ava",
    "Leo",
    "Emma",
    "Rachel",
    "Aria",
    "Ethan",
    "Ivy",
    "Lucas",
    "Mila",
    "Owen",
    "Sofia",
    "Liam",
    "Zara",
    "Nathan",
    "Ella",
    "Julian",
    "Grace",
    "Henry",
    "Nina",
    "Isaac",
    "Priya",
    "Rohan",
    "Anya",
    "Daniel",
    "Harper",
    "Victor",
    "Aiden",
    "Bella",
    "Caleb",
    "Daisy",
    "Elena",
    "Felix",
    "Gia",
    "Hudson",
    "Jasmine",
    "Kian",
    "Layla",
    "Mason",
    "Nora",
    "Oscar",
    "Pooja",
    "Quinn",
    "Reyansh",
    "Sara",
    "Tara",
    "Uma",
    "Vihaan",
    "Willow",
    "Xavier",
    "Yash",
    "Zane",
]
# Each template names who is "first" in the sentence and whether that person
# has more ("greater") or less ("lesser") of the trait.
REASONING_COMPARISON_TEMPLATES = [
    ("{first} is {greater} than {second}.", "greater"),
    ("{first} is {lesser} than {second}.", "lesser"),
    ("{first} is not as {greater_base} as {second}.", "lesser"),
    ("{first} is not as {lesser_base} as {second}.", "greater"),
]
REASONING_QUESTION_TEMPLATES = [
    "Who is {comparative}?",
    "Which of them is {comparative}?",
]
PERCEPTUAL_SPEED_LETTER_POOLS = {
    "easy": list("ABCDEFGHJKLMNPRSTUVWXYZ"),
    "medium": list("BCDEFGHJKMNPRSTUVWXYZ"),
    "hard": list("bdfghjkmnpqrtxyBDFGHJKMNPQRTXY"),
}
PERCEPTUAL_SPEED_INSTRUCTIONS = [
    "Count how many pairs show the same letter in different case.",
    "How many pairs contain the same letter, once uppercase and once lowercase?",
    "Count the pairs where both letters match apart from case.",
]
WORD_MEANING_INSTRUCTIONS = [
    "Choose the odd one out.",
    "Which word does not belong with the other two?",
    "Pick the word that does not fit the group.",
]
CCAT_SPATIAL_RULES = [
    {
        "question": "Which option continues the sequence where the shape rotates 90° clockwise each step?",
        "options": ["▲", "▶", "▼", "◀"],
        "answer": "◀",
        "instruction": "Track the direction change from one shape to the next.",
        "stimulus": [
            {"shape": "triangle", "rotation": 0},
            {"shape": "triangle", "rotation": 90},
            {"shape": "triangle", "rotation": 180},
            {"shape": "missing"},
        ],
        "option_visuals": [
            {"value": "▲", "shape": "triangle", "rotation": 0},
            {"value": "▶", "shape": "triangle", "rotation": 90},
            {"value": "▼", "shape": "triangle", "rotation": 180},
            {"value": "◀", "shape": "triangle", "rotation": 270},
        ],
    },
    {
        "question": "Which option is the mirrored version of the reference pattern?",
        "options": ["◧", "◨", "◩", "◪"],
        "answer": "◨",
        "instruction": "Compare the filled side of each figure to the reference rule.",
        "stimulus": [
            {"shape": "split_square", "fill": "left"},
            {"shape": "mirror_axis"},
            {"shape": "missing"},
        ],
        "option_visuals": [
            {"value": "◧", "shape": "split_square", "fill": "left"},
            {"value": "◨", "shape": "split_square", "fill": "right"},
            {"value": "◩", "shape": "split_square", "fill": "top"},
            {"value": "◪", "shape": "split_square", "fill": "bottom"},
        ],
    },
    {
        "question": "Which option completes the abstract pattern by adding one new side each step?",
        "options": ["△", "□", "⬟", "⬢"],
        "answer": "⬢",
        "instruction": "Count the edges and follow the growth pattern.",
        "stimulus": [
            {"shape": "polygon", "sides": 3},
            {"shape": "polygon", "sides": 4},
            {"shape": "polygon", "sides": 5},
            {"shape": "missing"},
        ],
        "option_visuals": [
            {"value": "△", "shape": "polygon", "sides": 3},
            {"value": "□", "shape": "polygon", "sides": 4},
            {"value": "⬟", "shape": "polygon", "sides": 5},
            {"value": "⬢", "shape": "polygon", "sides": 6},
        ],
    },
]


def _difficulty_templates(templates, difficulty: str, negation: str):
    if difficulty == "easy":
        return [(template, role) for template, role in templates if negation not in template]
    if difficulty == "hard":
        return [(template, role) for template, role in templates if negation in template]
    return list(templates)


class ReasoningGenerator(BaseQuestionGenerator):
    section_type = "reasoning"

    def generate(self, difficulty: str, seed: str, conn=None, language: str = "en") -> GeneratedQuestion:
        if language == "de":
            return self._generate_german(difficulty, seed)
        if language == "es":
            return self._generate_spanish(difficulty, seed)
        rng = self.rng(seed)
        names = rng.sample(NAMES, 2)
        greater_word, lesser_word, greater_base, lesser_base = rng.choice(COMPARATIVE_TRAITS)
        templates = [
            (template, role)
            for template, role in REASONING_COMPARISON_TEMPLATES
            if lesser_base is not None or "{lesser_base}" not in template
        ]
        if difficulty == "easy":
            templates = [
                (template, role) for template, role in templates if "not as" not in template
            ]
        elif difficulty == "hard":
            templates = [(template, role) for template, role in templates if "not as" in template]
        statement_template, first_role = rng.choice(templates)
        greater, lesser = rng.sample(names, 2)
        first, second = (greater, lesser) if first_role == "greater" else (lesser, greater)
        statement = statement_template.format(
            first=first,
            second=second,
            greater=greater_word,
            lesser=lesser_word,
            greater_base=greater_base,
            lesser_base=lesser_base,
        )

        ask_for_greater = rng.choice([True, False])
        answer = greater if ask_for_greater else lesser
        question = rng.choice(REASONING_QUESTION_TEMPLATES).format(
            comparative=greater_word if ask_for_greater else lesser_word,
        )

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "statements": [statement],
                "question": question,
                "explanation": f"{greater} is {greater_word} than {lesser}; therefore the answer is {answer}.",
            },
            "options": names,
            "metadata": {
                "difficulty": difficulty,
                "trait": greater_base,
                "comparison_template": statement_template,
            },
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})

    def _payload(self, statement, question, explanation, names, difficulty, trait, template, language):
        return {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {"statements": [statement], "question": question, "explanation": explanation},
            "options": names,
            "metadata": {"difficulty": difficulty, "trait": trait, "comparison_template": template, "language": language},
        }

    def _generate_german(self, difficulty: str, seed: str) -> GeneratedQuestion:
        rng = self.rng(seed)
        names = rng.sample(gl.DE_NAMES, 2)
        templates = _difficulty_templates(gl.DE_COMPARISON_TEMPLATES, difficulty, "nicht so")
        greater_word, lesser_word, greater_base, lesser_base = rng.choice(
            [trait for trait in gl.DE_TRAITS if trait[3] is not None or difficulty != "hard"]
        )
        templates = [(t, r) for t, r in templates if lesser_base is not None or "{lesser_base}" not in t]
        template, first_role = rng.choice(templates)
        greater, lesser = rng.sample(names, 2)
        first, second = (greater, lesser) if first_role == "greater" else (lesser, greater)
        statement = template.format(first=first, second=second, greater=greater_word, lesser=lesser_word,
                                    greater_base=greater_base, lesser_base=lesser_base)
        ask_for_greater = rng.choice([True, False])
        answer = greater if ask_for_greater else lesser
        question = rng.choice(gl.DE_QUESTION_TEMPLATES).format(comparative=greater_word if ask_for_greater else lesser_word)
        explanation = gl.DE_REASONING_EXPLANATION.format(greater=greater, greater_word=greater_word, lesser=lesser, answer=answer)
        payload = self._payload(statement, question, explanation, names, difficulty, greater_base, template, "de")
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})

    def _generate_spanish(self, difficulty: str, seed: str) -> GeneratedQuestion:
        rng = self.rng(seed)
        gender = rng.choice(["m", "f"])
        g = 0 if gender == "m" else 1
        names = rng.sample(gl.ES_NAMES[gender], 2)
        traits = [trait for trait in gl.ES_TRAITS if difficulty != "hard" or trait[2] is not None]
        greater_comp, lesser_comp, greater_base, lesser_base = rng.choice(traits)
        templates = _difficulty_templates(gl.ES_COMPARISON_TEMPLATES, difficulty, "no es tan")
        templates = [
            (t, r) for t, r in templates
            if (greater_base is not None or "{greater_base}" not in t) and (lesser_base is not None or "{lesser_base}" not in t)
        ]
        template, first_role = rng.choice(templates)
        greater, lesser = rng.sample(names, 2)
        first, second = (greater, lesser) if first_role == "greater" else (lesser, greater)
        statement = template.format(
            first=first, second=second, greater=greater_comp[g], lesser=lesser_comp[g],
            greater_base=greater_base[g] if greater_base else "", lesser_base=lesser_base[g] if lesser_base else "",
        )
        ask_for_greater = rng.choice([True, False])
        answer = greater if ask_for_greater else lesser
        question = rng.choice(gl.ES_QUESTION_TEMPLATES[gender]).format(
            comparative=greater_comp[g] if ask_for_greater else lesser_comp[g]
        )
        explanation = gl.ES_REASONING_EXPLANATION.format(greater=greater, greater_word=greater_comp[g], lesser=lesser, answer=answer)
        trait = greater_base[0] if greater_base else greater_comp[0]
        payload = self._payload(statement, question, explanation, names, difficulty, trait, template, "es")
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})


class PerceptualSpeedGenerator(BaseQuestionGenerator):
    section_type = "perceptual_speed"

    def generate(self, difficulty: str, seed: str, conn=None, language: str = "en") -> GeneratedQuestion:
        rng = self.rng(seed)
        length = 4
        letter_pool = PERCEPTUAL_SPEED_LETTER_POOLS.get(
            difficulty, PERCEPTUAL_SPEED_LETTER_POOLS["medium"]
        )
        pairs = []
        match_count = 0

        for _ in range(length):
            same = rng.random() < (0.55 if difficulty == "easy" else 0.45)
            left = rng.choice(letter_pool).upper()
            if same:
                right = left.lower()
                match_count += 1
            else:
                different = rng.choice(
                    [c.lower() for c in letter_pool if c.lower() != left.lower()]
                )
                right = different
            pairs.append({"left": left, "right": right})

        matching = ", ".join(str(i + 1) for i, pair in enumerate(pairs) if pair["left"].lower() == pair["right"].lower())
        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": rng.choice(gl.PERCEPTUAL_INSTRUCTIONS.get(language, PERCEPTUAL_SPEED_INSTRUCTIONS)),
                "pairs": pairs,
                "explanation": (
                    gl.perceptual_explanation(language, matching, match_count)
                    if language in gl.PERCEPTUAL_EXPLANATION
                    else f"The matching pairs are {matching or 'none'}. There are {match_count} matches."
                ),
            },
            "options": list(range(length + 1)),
            "metadata": {
                "difficulty": difficulty,
                "letter_pool_size": len(letter_pool),
            },
        }
        return GeneratedQuestion(
            self.section_type, difficulty, seed, payload, {"answer": match_count}
        )


class NumberSpeedAccuracyGenerator(BaseQuestionGenerator):
    section_type = "number_speed_accuracy"

    def generate(self, difficulty: str, seed: str, conn=None, language: str = "en") -> GeneratedQuestion:
        rng = self.rng(seed)
        upper = {"easy": 50, "medium": 100, "hard": 200}.get(difficulty, 100)

        while True:
            numbers = rng.sample(range(1, upper + 1), 3)
            ordered = sorted(numbers)
            low_gap = ordered[1] - ordered[0]
            high_gap = ordered[2] - ordered[1]
            if low_gap != high_gap:
                break

        if low_gap > high_gap:
            answer = ordered[0]
        else:
            answer = ordered[2]

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": gl.NUMBER_INSTRUCTION.get(language, "Which number is furthest from the middle value?"),
                "numbers": numbers,
                "explanation": (
                    gl.NUMBER_EXPLANATION[language].format(a=ordered[0], b=ordered[1], c=ordered[2], low=low_gap, high=high_gap, answer=answer)
                    if language in gl.NUMBER_EXPLANATION
                    else f"In order: {ordered[0]}, {ordered[1]}, {ordered[2]}. The gaps are {low_gap} and {high_gap}; {answer} is farther from {ordered[1]}."
                ),
            },
            "options": numbers,
            "metadata": {"difficulty": difficulty},
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})


class WordMeaningGenerator(BaseQuestionGenerator):
    section_type = "word_meaning"

    def generate(self, difficulty: str, seed: str, conn=None, language: str = "en") -> GeneratedQuestion:
        rng = self.rng(seed)
        queryset = WordMeaningItem.objects.filter(is_active=True, language=gl.normalize_language(language))
        candidates = list(queryset.filter(difficulty=difficulty).order_by("id"))
        if not candidates:
            raise ValueError(f"No word meaning items available for {difficulty}.")
        row = _choose_batch_balanced_variant(rng, seed, candidates)

        words = [row.pair_word_1, row.pair_word_2, row.odd_word]
        rng.shuffle(words)

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": rng.choice(gl.WORD_MEANING_INSTRUCTIONS.get(language, WORD_MEANING_INSTRUCTIONS)),
                "words": words,
                "explanation": row.explanation
                or f"{row.pair_word_1} and {row.pair_word_2} are related ({row.relationship_type.replace('_', ' ')}); {row.odd_word} does not share that relationship.",
            },
            "options": words,
            "metadata": {
                "difficulty": difficulty,
                "relationship_type": row.relationship_type,
                "source_item_id": row.pk,
                "bank_version": hashlib.sha256(
                    json.dumps(
                        [
                            (
                                item.pk,
                                item.pair_word_1,
                                item.pair_word_2,
                                item.odd_word,
                                item.explanation,
                            )
                            for item in candidates
                        ]
                    ).encode()
                ).hexdigest()[:16],
            },
        }
        return GeneratedQuestion(
            self.section_type, difficulty, seed, payload, {"answer": row.odd_word}
        )


class SpatialVisualizationGenerator(BaseQuestionGenerator):
    section_type = "spatial_visualization"
    # Every glyph must lack reflection symmetry; otherwise its mirror image is
    # just a rotation of itself and the "different" answer becomes ambiguous.
    LETTERS = ["F", "P", "R", "L", "b", "q"]
    ROTATIONS = [90, 180, 270]

    def generate(self, difficulty: str, seed: str, conn=None, language: str = "en") -> GeneratedQuestion:
        rng = self.rng(seed)
        letters = rng.sample(self.LETTERS, 2)
        pairs = []
        match_count = 0
        for letter in letters:
            is_same = rng.choice([True, False])
            if is_same:
                match_count += 1
            # As in the GIA, the second figure is always turned, so a match
            # has to be confirmed by mental rotation rather than by sight.
            pairs.append(
                {
                    "letter": letter,
                    "same": is_same,
                    "rotation": rng.choice(
                        {"easy": [90, 180], "medium": self.ROTATIONS, "hard": [90, 270]}.get(
                            difficulty, self.ROTATIONS
                        )
                    ),
                }
            )

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": gl.SPATIAL_INSTRUCTION.get(language, "How many pairs show the same image?"),
                "letter_pairs": pairs,
                "explanation": (
                    " ".join(gl.SPATIAL_PAIR_EXPLANATION[language][0 if pair["same"] else 1].format(n=i + 1) for i, pair in enumerate(pairs))
                    + gl.SPATIAL_TOTAL[language].format(count=match_count)
                    if language in gl.SPATIAL_INSTRUCTION
                    else " ".join(
                        f"Pair {i + 1} is {'a rotated match' if pair['same'] else 'a rotated mirror image'}."
                        for i, pair in enumerate(pairs)
                    )
                    + f" Total matching pairs: {match_count}."
                ),
            },
            "options": ["0", "1", "2"],
            "metadata": {"difficulty": difficulty},
        }
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            payload,
            {"answer": str(match_count)},
        )


class CCATNumericalGenerator(BaseQuestionGenerator):
    section_type = "ccat_numerical"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        level = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
        subtype = _choose_batch_balanced_variant(
            rng,
            seed,
            [
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
            ],
        )

        if subtype == "series":
            pattern = rng.choice(
                ["arithmetic"]
                if level == 1
                else ["growing_gap", "geometric"]
                if level == 2
                else ["growing_gap"]
            )
            start = rng.randint(2 * level, 12 * level)
            if pattern == "arithmetic":
                gap = rng.randint(2, 9)
                series = [start + gap * index for index in range(5)]
                answer = series[-1] + gap
                distractors = [answer - gap, answer + 1, answer + gap]
            elif pattern == "geometric":
                multiplier = rng.choice([2, 3])
                series = [start * (multiplier**index) for index in range(4)]
                answer = series[-1] * multiplier
                distractors = [series[-1] + multiplier, answer - multiplier, answer + multiplier]
            else:
                gap = rng.randint(level, 4 * level)
                growth = rng.randint(level, 3 * level)
                series = [start]
                for index in range(4):
                    series.append(series[-1] + gap + growth * index)
                answer = series[-1] + gap + growth * 4
                distractors = [answer - growth, answer + growth, series[-1] + gap]
            prompt = {
                "instruction": "What comes next in the number series?",
                "question": f"{', '.join(str(value) for value in series)}, ___",
            }
        elif subtype == "percentage":
            percent = rng.choice(
                {1: [10, 25, 50], 2: [15, 20, 35, 40], 3: [12.5, 17.5, 22.5, 37.5]}[level]
            )
            base = rng.randint(4, 20 * level) * 20
            answer = base * percent / 100
            distractors = [base - answer, base + answer, percent]
            prompt = {
                "instruction": "Calculate the percentage.",
                "question": f"What is {percent}% of {base}?",
            }
        elif subtype == "discount":
            base = rng.randint(4, 12 * level) * 10
            markup = rng.choice(
                [20, 25] if level == 1 else [15, 30, 35] if level == 2 else [12.5, 17.5, 27.5]
            )
            discount = rng.choice([10, 20, 25])
            marked = base * (1 + markup / 100)
            answer = round(marked * (1 - discount / 100), 2)
            distractors = [
                round(base * (1 - discount / 100), 2),
                round(base * (1 + (markup - discount) / 100), 2),
                round(marked, 2),
            ]
            prompt = {
                "instruction": "Calculate the final price.",
                "question": f"A product costing ${base} is marked up by {markup}% and then discounted by {discount}%. What is the final price?",
            }
        elif subtype == "ratio":
            left = rng.randint(level + 1, 5 * level)
            right = rng.randint(level + 1, 5 * level)
            multiplier = rng.randint(3, 12)
            total = (left + right) * multiplier
            answer = left * multiplier
            distractors = [right * multiplier, total - left, total // left]
            prompt = {
                "instruction": "Use the ratio to find the requested share.",
                "question": f"A total of {total} items is divided in the ratio {left}:{right}. How many items are in the first share?",
            }
        elif subtype == "work_rate":
            workers = rng.randint(2 + level, 5 * level)
            days = rng.randint(3 * level, 8 * level)
            target_workers = rng.choice([value for value in range(2, 8) if value != workers])
            answer = round((workers * days) / target_workers, 2)
            distractors = [days - 1, days + 1, round((target_workers * days) / workers, 2)]
            prompt = {
                "instruction": "Use work-rate reasoning.",
                "question": f"If {workers} equally productive workers finish a job in {days} days, how many days will {target_workers} workers need at the same constant individual rate? Round to two decimal places if needed.",
            }
        elif subtype == "average":
            average = rng.randint(8 * level, 30 * level)
            known = [average + rng.randint(-5, 5) for _ in range(3)]
            answer = average * 4 - sum(known)
            if answer <= 0:
                known = [average - 1, average, average + 1]
                answer = average
            distractors = [average, answer + 2, max(1, answer - 2)]
            prompt = {
                "instruction": "Find the missing value from the average.",
                "question": f"The average of {known[0]}, {known[1]}, {known[2]}, and one other number is {average}. What is the missing number?",
            }
        elif subtype == "equation":
            answer = rng.randint(3 * level, 20 * level)
            coefficient = rng.randint(2 * level, 8 * level)
            constant = rng.randint(level, 15 * level)
            result = coefficient * answer + constant
            distractors = [answer - 1, answer + 1, round(result / coefficient, 2)]
            prompt = {
                "instruction": "Solve for the unknown value.",
                "question": f"If {coefficient}x + {constant} = {result}, what is x?",
            }
        elif subtype == "distance":
            speed = rng.randint(3 * level, 10 * level) * 5
            hours = rng.choice(
                [2, 3, 4] if level == 1 else [1.5, 2.5, 3.5] if level == 2 else [1.25, 2.75, 3.25]
            )
            answer = speed * hours
            distractors = [speed + hours, speed * (hours - 1), speed * (hours + 1)]
            prompt = {
                "instruction": "Use the distance, speed, and time relationship.",
                "question": f"A vehicle travels at {speed} miles per hour for {hours} hours. How far does it travel?",
            }
        elif subtype == "fraction":
            denominator = rng.choice(
                [4, 5] if level == 1 else [8, 10, 12] if level == 2 else [16, 20, 24]
            )
            numerator = rng.randint(1, denominator - 1)
            total = denominator * rng.choice([6, 8, 10, 12])
            answer = total * numerator // denominator
            distractors = [total - answer, answer + denominator, max(1, answer - denominator)]
            prompt = {
                "instruction": "Find the requested fraction of the quantity.",
                "question": f"What is {numerator}/{denominator} of {total}?",
            }
        elif subtype == "profit_loss":
            cost = rng.randint(4 * level, 20 * level) * 10
            percent = rng.choice([10, 15, 20, 25, 30])
            is_profit = rng.choice([True, False])
            answer = round(cost * (1 + percent / 100 if is_profit else 1 - percent / 100), 2)
            distractors = [
                round(cost * (1 - percent / 100 if is_profit else 1 + percent / 100), 2),
                cost,
                round(cost * percent / 100, 2),
            ]
            prompt = {
                "instruction": "Calculate the selling price.",
                "question": f"An item costs ${cost} and is sold at a {percent}% {'profit' if is_profit else 'loss'}. What is its selling price?",
            }
        elif subtype == "conversion":
            unit, factor, target = rng.choice(
                [
                    ("kilometres", 1000, "metres"),
                    ("kilograms", 1000, "grams"),
                    ("hours", 60, "minutes"),
                    ("metres", 100, "centimetres"),
                ]
            )
            quantity = rng.randint(2, 15 * level) / (1 if level == 1 else 2 if level == 2 else 4)
            answer = quantity * factor
            distractors = [quantity + factor, quantity * (factor // 10), answer + factor]
            prompt = {
                "instruction": "Convert the measurement to the requested unit.",
                "question": f"How many {target} are in {quantity} {unit}?",
            }
        else:
            start = rng.randint(4, 20 * level) * 20
            increase = rng.choice(
                [10, 20, 25] if level == 1 else [15, 30, 35] if level == 2 else [12.5, 17.5, 22.5]
            )
            decrease = rng.choice([10, 20, 25])
            answer = round(start * (1 + increase / 100) * (1 - decrease / 100), 2)
            distractors = [
                round(start * (1 + (increase - decrease) / 100), 2),
                start,
                round(start * (1 - decrease / 100), 2),
            ]
            prompt = {
                "instruction": "Apply each percentage change in order.",
                "question": f"A value of {start} increases by {increase}% and then decreases by {decrease}%. What is the final value?",
            }

        explanations = {
            "series": lambda: f"The rule is {pattern.replace('_', ' ')}. "
            + (
                f"Add {gap} each time."
                if pattern == "arithmetic"
                else f"Multiply by {multiplier} each time."
                if pattern == "geometric"
                else f"The gaps grow by {growth}; the next gap is {gap + growth * 4}."
            )
            + f" The next value is {_format_ccat_number(answer)}.",
            "percentage": lambda: f"{base} × {percent}/100 = {_format_ccat_number(answer)}.",
            "discount": lambda: f"First mark up: {base} × (1 + {markup}/100) = {_format_ccat_number(marked)}. Then multiply by (1 − {discount}/100) to get {_format_ccat_number(answer)}.",
            "ratio": lambda: f"One part is {total}/({left} + {right}) = {multiplier}; the first share is {left} × {multiplier} = {answer}.",
            "work_rate": lambda: f"The job takes {workers} × {days} = {workers * days} worker-days. Divide by {target_workers} to get {_format_ccat_number(answer)} days (rounded if necessary).",
            "average": lambda: f"The total is 4 × {average} = {4 * average}. Subtract {sum(known)} to get {answer}.",
            "equation": lambda: f"Subtract {constant} from {result}, then divide by {coefficient}: x = {answer}.",
            "distance": lambda: f"Distance = speed × time = {speed} × {hours} = {_format_ccat_number(answer)} miles.",
            "fraction": lambda: f"Divide {total} by {denominator}, then multiply by {numerator}: {answer}.",
            "profit_loss": lambda: f"{'Add' if is_profit else 'Subtract'} {percent}% of ${cost}: the selling price is ${_format_ccat_number(answer)}.",
            "conversion": lambda: f"Each {unit} unit contains {factor} {target}; {quantity} × {factor} = {_format_ccat_number(answer)} {target}.",
            "compound_change": lambda: f"Apply the changes to successive bases: {start} × (1 + {increase}/100) × (1 − {decrease}/100) = {_format_ccat_number(answer)}.",
        }
        prompt["explanation"] = explanations[subtype]()
        option_strings, answer_string = _build_ccat_number_options(rng, answer, distractors)
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": prompt,
                "options": option_strings,
                "metadata": {"difficulty": difficulty, "subtype": subtype},
            },
            {"answer": answer_string},
        )


class CCATVerbalGenerator(BaseQuestionGenerator):
    section_type = "ccat_verbal"
    FAMILIES = [
        "analogy",
        "sentence_completion",
        "word_relationship",
        "synonym",
        "antonym",
        "inference",
        "definition",
        "deduction",
    ]

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        bank = VERBAL_BANK.get(difficulty, VERBAL_BANK["medium"])
        subtype = _choose_batch_balanced_variant(rng, seed, self.FAMILIES)
        # Family and item cycles have different lengths, preventing repeats of a
        # lexical concept within the same family before its bank is exhausted.
        prefix, _, position = seed.rpartition(":")
        item_seed = (
            f"{prefix}:{int(position) // len(self.FAMILIES)}" if position.isdigit() else seed
        )
        word, synonym, antonym, definition, sentence = _choose_batch_balanced_variant(
            rng, item_seed, bank
        )
        alternatives = unrelated_entries(bank, word)
        other_words = [
            entry[1] for entry in alternatives if entry[1] not in {word, synonym, antonym}
        ]
        wrong = [antonym, *rng.sample(other_words, 2)]
        explanation = f"{word.capitalize()} means {definition}; {synonym} is similar in meaning, while {antonym} expresses the opposite."
        if subtype == "synonym":
            question, answer, options = (
                f"Which word is closest in meaning to '{word}'?",
                synonym,
                [synonym, *wrong],
            )
        elif subtype == "antonym":
            question, answer, options = (
                f"Which word is opposite in meaning to '{word}'?",
                antonym,
                [antonym, synonym, *rng.sample(other_words, 2)],
            )
        elif subtype == "definition":
            answer = definition
            options = [answer, *rng.sample([entry[3] for entry in alternatives], 3)]
            question = f"What does '{word}' most nearly mean?"
        elif subtype == "sentence_completion":
            question, answer = sentence, word
            options = [word, *wrong]
        elif subtype == "word_relationship":
            is_opposite = rng.choice([True, False])
            question = (
                f"How are '{word}' and '{antonym if is_opposite else synonym}' related in meaning?"
            )
            answer = "Opposite" if is_opposite else "Similar"
            options = ["Similar", "Opposite", "Unrelated", "Identical spelling"]
        elif subtype == "analogy":
            reference = rng.choice(alternatives)
            is_opposite = rng.choice([True, False])
            question = f"{reference[0]} is to {reference[2] if is_opposite else reference[1]} as {word} is to ___?"
            answer = antonym if is_opposite else synonym
            options = [answer, word, reference[0], synonym if is_opposite else antonym]
            explanation = (
                "Both pairs are opposites. "
                if is_opposite
                else "Both pairs have similar meanings. "
            ) + explanation
        else:
            # Information-based reasoning replaces trivia and speculative causes.
            level = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
            subject = rng.choice(["archive", "dispatch", "quality", "support", "design", "finance"])
            code = rng.randint(10, 999)
            steps = [f"Every {subject} request receives code {code}."]
            steps += [
                f"Every request with code {code + i} also receives code {code + i + 1}."
                for i in range(level - 1)
            ]
            if subtype == "deduction":
                question = (
                    " ".join(steps)
                    + f" Request K is a {subject} request. Which statement must be true?"
                )
                answer = f"K receives code {code + level - 1}."
                options = [
                    answer,
                    f"K does not receive code {code}.",
                    "K has already been completed.",
                    f"Only {subject} requests receive code {code}.",
                ]
                explanation = f"K is a {subject} request, so follow the stated rules through to code {code + level - 1}. No completion rule or converse is given."
            else:
                question = (
                    " ".join(steps)
                    + f" Request K receives code {code + level - 1}. Must K be a {subject} request?"
                )
                answer = "Cannot be determined"
                options = ["Yes", "No; it cannot be", answer, "The rules contradict each other"]
                explanation = f"The rules say {subject} requests receive the codes, not that only those requests do. Other requests may receive the same code."
        rng.shuffle(options)
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": {
                    "instruction": "Choose the best answer using the information given.",
                    "question": question,
                    "explanation": explanation,
                },
                "options": options,
                "metadata": {
                    "difficulty": difficulty,
                    "subtype": subtype,
                    "source_item_id": f"{difficulty}:{subtype}:{word}",
                    "bank_version": "2026-11",
                },
            },
            {"answer": answer},
        )


class CCATSpatialGenerator(BaseQuestionGenerator):
    section_type = "ccat_spatial"

    ROTATABLE_SHAPES = [
        ("triangle", "Triangle"),
        ("arrow", "Arrow"),
        ("chevron", "Chevron"),
        ("l_shape", "L shape"),
        ("kite", "Kite"),
    ]
    SHAPE_CYCLES = [
        [
            ("triangle", "Triangle"),
            ("square", "Square"),
            ("circle", "Circle"),
            ("diamond", "Diamond"),
        ],
        [
            ("star", "Star"),
            ("pentagon", "Pentagon"),
            ("hexagon", "Hexagon"),
            ("octagon", "Octagon"),
        ],
        [("arrow", "Arrow"), ("chevron", "Chevron"), ("kite", "Kite"), ("trapezoid", "Trapezoid")],
        [("plus", "Plus"), ("l_shape", "L shape"), ("cross", "Cross"), ("circle", "Circle")],
    ]

    ROTATION_OPTIONS = [
        {"value": "Up", "shape": "triangle", "rotation": 0},
        {"value": "Right", "shape": "triangle", "rotation": 90},
        {"value": "Down", "shape": "triangle", "rotation": 180},
        {"value": "Left", "shape": "triangle", "rotation": 270},
    ]
    FILL_OPTIONS = [
        {"value": "Left half", "shape": "split_square", "fill": "left"},
        {"value": "Top half", "shape": "split_square", "fill": "top"},
        {"value": "Right half", "shape": "split_square", "fill": "right"},
        {"value": "Bottom half", "shape": "split_square", "fill": "bottom"},
    ]

    def _rotation_rule(self, rng: random.Random) -> dict:
        start = rng.choice([0, 90, 180, 270])
        step = rng.choice([90, -90])
        rotations = [(start + step * index) % 360 for index in range(4)]
        shape, label = rng.choice(self.ROTATABLE_SHAPES)
        options = [
            {"value": direction, "shape": shape, "rotation": rotation}
            for direction, rotation in [("Up", 0), ("Right", 90), ("Down", 180), ("Left", 270)]
        ]
        answer_visual = next(item for item in options if item["rotation"] == rotations[-1])
        return {
            "subtype": "rotation",
            "question": f"Which option continues the {('clockwise' if step > 0 else 'counter-clockwise')} rotation?",
            "instruction": "Track the direction change from one shape to the next.",
            "stimulus": [
                *[{"shape": shape, "rotation": value} for value in rotations[:3]],
                {"shape": "missing"},
            ],
            "option_visuals": options,
            "answer": answer_visual["value"],
        }

    def _fill_rotation_rule(self, rng: random.Random) -> dict:
        fills = ["left", "top", "right", "bottom"]
        start = rng.randrange(len(fills))
        step = rng.choice([1, -1])
        sequence = [fills[(start + step * index) % len(fills)] for index in range(4)]
        answer_visual = next(item for item in self.FILL_OPTIONS if item["fill"] == sequence[-1])
        return {
            "subtype": "fill_rotation",
            "question": "Which option continues the movement of the shaded half?",
            "instruction": "Follow the shaded area around the square.",
            "stimulus": [
                *[{"shape": "split_square", "fill": value} for value in sequence[:3]],
                {"shape": "missing"},
            ],
            "option_visuals": self.FILL_OPTIONS,
            "answer": answer_visual["value"],
        }

    def _mirror_rule(self, rng: random.Random) -> dict:
        axis = rng.choice(["vertical", "horizontal"])
        source = rng.choice(["left", "right"] if axis == "vertical" else ["top", "bottom"])
        mirrors = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
        answer_fill = mirrors[source]
        answer_visual = next(item for item in self.FILL_OPTIONS if item["fill"] == answer_fill)
        return {
            "subtype": "mirror",
            "question": "Which option is the mirror image of the reference figure?",
            "instruction": f"Reflect the shaded area across the {axis} mirror line.",
            "stimulus": [
                {"shape": "split_square", "fill": source},
                {"shape": "mirror_axis", "orientation": axis},
                {"shape": "missing"},
            ],
            "option_visuals": self.FILL_OPTIONS,
            "answer": answer_visual["value"],
        }

    def _polygon_rule(self, rng: random.Random) -> dict:
        start = rng.choice([3, 4, 5])
        step = rng.choice([1, 2])
        if start + step * 3 > 8:
            step = 1
        sequence = [start + step * index for index in range(4)]
        answer = sequence[-1]
        candidates = list(range(3, 9))
        distractors = rng.sample([value for value in candidates if value != answer], 3)
        option_visuals = [
            {"value": f"{value} sides", "shape": "polygon", "sides": value}
            for value in [answer, *distractors]
        ]
        rng.shuffle(option_visuals)
        return {
            "subtype": "polygon_growth",
            "question": f"Which option continues the pattern by adding {step} side{'' if step == 1 else 's'} each step?",
            "instruction": "Count the sides of each figure.",
            "stimulus": [
                *[{"shape": "polygon", "sides": value} for value in sequence[:3]],
                {"shape": "missing"},
            ],
            "option_visuals": option_visuals,
            "answer": f"{answer} sides",
        }

    def _shape_cycle_rule(self, rng: random.Random) -> dict:
        cycle = rng.choice(self.SHAPE_CYCLES)
        shapes = [shape for shape, _label in cycle]
        labels = dict(cycle)
        start = rng.randrange(len(shapes))
        sequence = [shapes[(start + index) % len(shapes)] for index in range(4)]
        option_visuals = [{"value": labels[shape], "shape": shape} for shape in shapes]
        return {
            "subtype": "shape_cycle",
            "question": "Which option continues the repeating shape sequence?",
            "instruction": "Identify the order in which the different shapes repeat.",
            "stimulus": [
                *[{"shape": shapes[(start + index) % 4]} for index in range(7)],
                {"shape": "missing"},
            ],
            "option_visuals": option_visuals,
            "answer": labels[sequence[-1]],
        }

    def _dot_movement_rule(self, rng: random.Random) -> dict:
        positions = ["top", "right", "bottom", "left"]
        start = rng.randrange(4)
        step = rng.choice([1, -1])
        sequence = [positions[(start + step * index) % 4] for index in range(4)]
        option_visuals = [
            {"value": position.title(), "shape": "circle_dot", "position": position}
            for position in positions
        ]
        return {
            "subtype": "dot_movement",
            "question": "Which option continues the movement of the dot around the circle?",
            "instruction": "Track the dot's direction around the outline.",
            "stimulus": [
                *[{"shape": "circle_dot", "position": position} for position in sequence[:3]],
                {"shape": "missing"},
            ],
            "option_visuals": option_visuals,
            "answer": sequence[-1].title(),
        }

    def _dot_count_rule(self, rng: random.Random) -> dict:
        start = rng.choice([1, 2, 3])
        step = rng.choice([1, 2])
        if start + step * 3 > 9:
            step = 1
        sequence = [start + step * index for index in range(4)]
        answer = sequence[-1]
        candidates = [value for value in range(1, 10) if value != answer]
        option_visuals = [
            {"value": f"{value} dots", "shape": "dot_grid", "count": value}
            for value in [answer, *rng.sample(candidates, 3)]
        ]
        rng.shuffle(option_visuals)
        return {
            "subtype": "dot_count",
            "question": f"Which option continues the pattern by adding {step} dot{'' if step == 1 else 's'} each step?",
            "instruction": "Count the dots in each figure.",
            "stimulus": [
                *[{"shape": "dot_grid", "count": value} for value in sequence[:3]],
                {"shape": "missing"},
            ],
            "option_visuals": option_visuals,
            "answer": f"{answer} dots",
        }

    def _quadrant_fill_rule(self, rng: random.Random) -> dict:
        fills = ["top_left", "top_right", "bottom_right", "bottom_left"]
        start = rng.randrange(4)
        sequence = [fills[(start + index) % 4] for index in range(4)]
        option_visuals = [
            {"value": fill.replace("_", " ").title(), "shape": "quadrant_square", "fill": fill}
            for fill in fills
        ]
        return {
            "subtype": "quadrant_fill",
            "question": "Which option continues the movement of the shaded quadrant?",
            "instruction": "Follow the shaded corner around the square.",
            "stimulus": [
                *[{"shape": "quadrant_square", "fill": fill} for fill in sequence[:3]],
                {"shape": "missing"},
            ],
            "option_visuals": option_visuals,
            "answer": sequence[-1].replace("_", " ").title(),
        }

    def _size_growth_rule(self, rng: random.Random) -> dict:
        step = rng.choice([0.1, 0.15])
        start = rng.choice([0.3, 0.35, 0.4])
        direction = rng.choice([1, -1])
        sizes = [round(start + step * i, 2) for i in range(4)]
        if direction < 0:
            sizes.reverse()
        candidates = sorted(
            {round(size, 2) for size in [start, start + step, start + 2 * step, start + 3 * step]}
        )
        option_visuals = [
            {"value": f"Size {i}", "shape": "diamond", "scale": size}
            for i, size in enumerate(candidates)
        ]
        return {
            "subtype": "size_growth",
            "question": "Which figure completes the sequence?",
            "instruction": "Study the figures and choose the missing one.",
            "stimulus": [
                *[{"shape": "diamond", "scale": size} for size in sizes[:3]],
                {"shape": "missing"},
            ],
            "option_visuals": option_visuals,
            "answer": f"Size {candidates.index(sizes[-1])}",
        }

    def _bar_growth_rule(self, rng: random.Random) -> dict:
        orientation = rng.choice(["vertical", "horizontal"])
        step = rng.choice([1, 2])
        start = rng.randint(1, 3)
        sequence = [start + step * i for i in range(4)]
        if rng.choice([True, False]):
            sequence.reverse()
        answer = sequence[-1]
        candidates = [answer, *rng.sample([n for n in range(1, 10) if n != answer], 3)]
        option_visuals = [
            {"value": f"{count} bars", "shape": "bars", "count": count, "orientation": orientation}
            for count in candidates
        ]
        rng.shuffle(option_visuals)
        return {
            "subtype": "bar_growth",
            "question": "Which figure completes the sequence?",
            "instruction": "Study the figures and choose the missing one.",
            "stimulus": [
                *[
                    {"shape": "bars", "count": count, "orientation": orientation}
                    for count in sequence[:3]
                ],
                {"shape": "missing"},
            ],
            "option_visuals": option_visuals,
            "answer": f"{answer} bars",
        }

    def _matrix_completion_rule(self, rng: random.Random) -> dict:
        """Generate a multi-feature 3×3 matrix like standard CCAT abstract items."""
        shapes = rng.choice(
            [
                [("triangle", "Triangles"), ("circle", "Circles"), ("square", "Squares")],
                [("star", "Stars"), ("diamond", "Diamonds"), ("hexagon", "Hexagons")],
            ]
        )
        shapes = rng.sample(shapes, len(shapes))
        counts = rng.sample([1, 2, 3, 4], 3)
        positions_by_count = {
            1: ["center"],
            2: ["top_right", "bottom_left"],
            3: ["top_left", "center", "bottom_right"],
            4: ["top_left", "top_right", "bottom_left", "bottom_right"],
        }

        def cell(shape: str, count: int, filled_offset: int = 0) -> dict:
            positions = positions_by_count[count]
            return {
                "shape": "symbol_box",
                "marks": [
                    {
                        "shape": shape,
                        "position": position,
                        # Filled symbols move diagonally through the matrix;
                        # count and symbol type must both be considered.
                        "filled": index in {filled_offset % count, (filled_offset + 2) % count}
                        if count > 2
                        else index == filled_offset % count,
                    }
                    for index, position in enumerate(positions)
                ],
            }

        matrix = []
        for row, (shape, _label) in enumerate(shapes):
            for column, count in enumerate(counts):
                matrix.append(cell(shape, count, row + column))
        answer_spec = matrix.pop(4)
        matrix.insert(4, {"shape": "missing"})
        answer = f"choice-{rng.getrandbits(64):016x}"
        # Some fill offsets render identically for small counts, so keep only
        # distractors that differ visually from the answer and from each other.
        candidate_specs = [
            cell(shapes[1][0], counts[0], 1),
            cell(shapes[0][0], counts[1], 1),
            cell(shapes[1][0], counts[1], 0),
            cell(shapes[1][0], counts[1], 1),
            cell(shapes[2][0], counts[1], 2),
            cell(shapes[1][0], counts[2], 2),
        ]
        seen = {json.dumps(answer_spec, sort_keys=True)}
        wrong_specs = []
        for spec in candidate_specs:
            key = json.dumps(spec, sort_keys=True)
            if key not in seen:
                seen.add(key)
                wrong_specs.append(spec)
        wrong_specs = wrong_specs[:3]
        option_visuals = [{"value": answer, **answer_spec}] + [
            {"value": f"choice-{rng.getrandbits(64):016x}", **spec}
            for index, spec in enumerate(wrong_specs, start=2)
        ]
        rng.shuffle(option_visuals)
        return {
            "subtype": "matrix_completion",
            "question": "Which option replaces the missing box to complete the pattern?",
            "instruction": "Use both directions of the matrix: each row fixes the symbol type, while each column changes the number and placement of filled symbols.",
            "stimulus": matrix,
            "stimulus_layout": "matrix",
            "option_visuals": option_visuals,
            "answer": answer,
        }

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        families = [
            self._rotation_rule,
            self._fill_rotation_rule,
            self._mirror_rule,
            self._polygon_rule,
            self._shape_cycle_rule,
            self._dot_movement_rule,
            self._dot_count_rule,
            self._quadrant_fill_rule,
            self._size_growth_rule,
            self._bar_growth_rule,
            self._matrix_completion_rule,
        ]
        if difficulty == "easy":
            families = [family for family in families if family != self._matrix_completion_rule]
        elif difficulty == "hard":
            families = [
                self._matrix_completion_rule,
                self._polygon_rule,
                self._dot_count_rule,
                self._fill_rotation_rule,
            ]
        rule_factory = _choose_batch_balanced_variant(rng, seed, families)
        rule = copy.deepcopy(rule_factory(rng))
        # Difficulty also changes the rule within a family where appropriate.
        if difficulty == "hard" and rule["subtype"] in {"polygon_growth", "dot_count"}:
            rule = self._matrix_completion_rule(rng)
        # Option IDs describe their displayed position, never their correctness.
        rng.shuffle(rule["option_visuals"])
        answer_visual = next(
            visual for visual in rule["option_visuals"] if visual["value"] == rule["answer"]
        )
        for index, visual in enumerate(rule["option_visuals"]):
            visual["value"] = chr(65 + index)
        rule["answer"] = answer_visual["value"]
        rule["question"] = (
            "Which figure completes the pattern?"
            if rule["subtype"] != "mirror"
            else "Which figure is the reflection across the shown mirror line?"
        )
        rule["instruction"] = "Study all the figures before choosing your answer."
        explanations = {
            "rotation": "The same figure turns one quarter-turn at every step; continue the direction of rotation.",
            "fill_rotation": "Only the shaded half changes, moving one side around the square at each step.",
            "mirror": "A reflection swaps left and right (or top and bottom) across the displayed mirror line.",
            "polygon_growth": "The number of sides increases by the same amount at every step.",
            "shape_cycle": "The shapes repeat in a fixed order; continue that order rather than choosing a similar-looking shape.",
            "dot_movement": "The dot advances around the circle by the same direction and distance each time.",
            "dot_count": "Count the dots: the total changes by a constant amount in every step.",
            "quadrant_fill": "The shaded quadrant moves around the square one corner at a time.",
            "size_growth": "The shape changes size by a constant increment; continue the increase or decrease.",
            "bar_growth": "The number of parallel bars changes by a constant amount; continue the increase or decrease.",
            "matrix_completion": "Read both directions: each row keeps one symbol type, while each column fixes the symbol count and filled-symbol arrangement.",
        }
        options = [visual["value"] for visual in rule["option_visuals"]]
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": {
                    "instruction": rule["instruction"],
                    "question": rule["question"],
                    "stimulus": rule["stimulus"],
                    "stimulus_layout": rule.get("stimulus_layout", "sequence"),
                    "explanation": explanations[rule["subtype"]],
                },
                "options": options,
                "option_visuals": rule["option_visuals"],
                "metadata": {"difficulty": difficulty, "subtype": rule["subtype"]},
            },
            {"answer": rule["answer"]},
        )


def _make_polygon_points(rng: random.Random, vertex_count: int) -> list[list[float]]:
    points = []
    for index in range(vertex_count):
        angle = (2 * math.pi * index) / vertex_count
        radius = rng.uniform(25, 45)
        x = round(math.cos(angle) * radius, 2)
        y = round(math.sin(angle) * radius * rng.uniform(0.7, 1.2), 2)
        points.append([x, y])
    return points


class SHLInductiveGenerator(CCATSpatialGenerator):
    section_type = "shl_inductive"

    def generate(self, difficulty, seed, conn=None):
        rng = self.rng(seed)
        if _choose_batch_balanced_variant(rng, seed, ["existing", "compound"]) == "existing":
            return super().generate(difficulty, seed, conn)
        level = {"easy": 1, "medium": 2, "hard": 3}[difficulty]
        positions = ["top_left", "top_right", "bottom_right", "bottom_left"]
        start, direction = rng.randrange(4), rng.choice([-1, 1])
        shape = rng.choice(["triangle", "diamond", "circle"])

        def cell(step, reverse=False, hold_fill=False, wrong_shape=False):
            marks = []
            for index in range(level):
                position = (start + index + (-direction if reverse else direction) * step) % 4
                marks.append(
                    {
                        "shape": "square" if wrong_shape else shape,
                        "position": positions[position],
                        "filled": (index + (0 if hold_fill else step)) % 2 == 0,
                    }
                )
            return {"shape": "symbol_box", "marks": marks}

        target = cell(4)
        candidates = [target, cell(4, hold_fill=True), cell(3), cell(4, wrong_shape=True), cell(2)]
        # Step 4's fill equals step 0: use the opposite fill as the diagnostic
        # distractor, rather than an identical 'held' fill.
        candidates[1] = copy.deepcopy(target)
        for mark in candidates[1]["marks"]:
            mark["filled"] = not mark["filled"]
        distinct = []
        for spec in candidates:
            if spec not in distinct:
                distinct.append(spec)
        options = [{"value": "", **spec} for spec in distinct[:4]]
        rng.shuffle(options)
        answer = None
        for index, spec in enumerate(options):
            spec["value"] = chr(65 + index)
            if {k: v for k, v in spec.items() if k != "value"} == target:
                answer = spec["value"]
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": {
                    "instruction": "Study every figure and select the missing one.",
                    "question": "Which figure completes the sequence?",
                    "stimulus": [*[cell(i) for i in range(4)], {"shape": "missing"}],
                    "stimulus_layout": "sequence",
                    "explanation": f"All {level} symbols move one corner {'clockwise' if direction == 1 else 'anticlockwise'} per step, and each symbol alternates between filled and outline. Continue both changes; a correct position with the wrong fill is insufficient.",
                },
                "options": [spec["value"] for spec in options],
                "option_visuals": options,
                "metadata": {
                    "difficulty": difficulty,
                    "subtype": "compound_movement",
                    "generator_version": 2,
                    "start": start,
                    "direction": direction,
                    "symbol_count": level,
                },
            },
            {"answer": answer},
        )


GENERATOR_MAP = {
    "reasoning": ReasoningGenerator(),
    "perceptual_speed": PerceptualSpeedGenerator(),
    "number_speed_accuracy": NumberSpeedAccuracyGenerator(),
    "word_meaning": WordMeaningGenerator(),
    "spatial_visualization": SpatialVisualizationGenerator(),
    "ccat_numerical": CCATNumericalGenerator(),
    "ccat_verbal": CCATVerbalGenerator(),
    "ccat_spatial": CCATSpatialGenerator(),
    "shl_numerical": SHLNumericalGenerator(),
    "shl_deductive": SHLDeductiveGenerator(),
    "shl_inductive": SHLInductiveGenerator(),
}

GENERATOR_MAP.update(
    {
        "consulting_math": ConsultingMathGenerator(),
        "consulting_evidence": ConsultingEvidenceGenerator(),
        "consulting_case": ConsultingShortCaseGenerator(),
        "linked_case": LinkedCaseGenerator(),
        **{
            key: CriticalThinkingGenerator(key)
            for key in [
                "wg_inference",
                "wg_assumptions",
                "wg_deduction",
                "wg_interpretation",
                "wg_arguments",
            ]
        },
    }
)


# Sections that can be generated in German and Spanish (Thomas GIA).
LOCALIZED_SECTION_TYPES = frozenset(
    {"reasoning", "perceptual_speed", "number_speed_accuracy", "word_meaning", "spatial_visualization"}
)


def generate_question(
    section_type: str,
    difficulty: str,
    seed: str,
    conn=None,
    language: str = "en",
) -> GeneratedQuestion:
    try:
        generator = GENERATOR_MAP[section_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported section type: {section_type}") from exc
    language = gl.normalize_language(language)
    if language != "en" and section_type in LOCALIZED_SECTION_TYPES:
        return generator.generate(difficulty=difficulty, seed=seed, conn=conn, language=language)
    return generator.generate(difficulty=difficulty, seed=seed, conn=conn)
