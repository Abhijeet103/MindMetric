from __future__ import annotations

import json
import math
import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.apps.assessments.models import WordMeaningItem


SECTION_TYPES = [
    "reasoning",
    "perceptual_speed",
    "number_speed_accuracy",
    "word_meaning",
    "spatial_visualization",
    "ccat_numerical",
    "ccat_verbal",
    "ccat_spatial",
]

TRAITS = [
    "fast",
    "happy",
    "strong",
    "smart",
    "tall",
    "rich",
    "calm",
    "brave",
    "careful",
    "creative",
    "curious",
    "focused",
    "friendly",
    "generous",
    "kind",
    "organized",
    "patient",
    "quick",
    "sharp",
    "steady",
    "alert",
    "ambitious",
    "balanced",
    "cheerful",
    "confident",
    "dependable",
    "diligent",
    "efficient",
    "gentle",
    "honest",
    "inventive",
    "logical",
    "observant",
    "polite",
    "reliable",
    "thoughtful",
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
REASONING_COMPARISON_TEMPLATES = [
    "{left} is more {trait} than {right}.",
    "{left} is less {trait} than {right}.",
    "Compared with {right}, {left} is more {trait}.",
    "Compared with {right}, {left} is less {trait}.",
    "{right} is less {trait} than {left}.",
    "{right} is more {trait} than {left}.",
]
REASONING_QUESTION_TEMPLATES = {
    "most": [
        "Who is the most {trait}?",
        "Which person is more {trait}?",
        "Who appears to be the most {trait}?",
    ],
    "least": [
        "Who is the least {trait}?",
        "Which person is less {trait}?",
        "Who appears to be the least {trait}?",
    ],
}
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
CCAT_SENTENCE_COMPLETIONS = [
    ("Despite the _____ weather, the outdoor event proceeded as planned.", ["favorable", "inclement", "predictable", "mild"], "inclement"),
    ("The manager praised her _____ approach to solving the deadline issue.", ["careless", "methodical", "random", "casual"], "methodical"),
    ("His answer was too _____ to support such a definite conclusion.", ["precise", "vague", "decisive", "detailed"], "vague"),
    ("The instructions were so _____ that every participant completed the task correctly.", ["ambiguous", "clear", "lengthy", "optional"], "clear"),
    ("Because the evidence was _____, the committee postponed its decision.", ["conclusive", "insufficient", "relevant", "abundant"], "insufficient"),
    ("Her explanation was _____, covering the issue in only two sentences.", ["concise", "confusing", "indirect", "repetitive"], "concise"),
    ("The two reports were _____; both reached the same conclusion.", ["contradictory", "consistent", "unrelated", "incomplete"], "consistent"),
    ("The new process should _____ the time required to review each application.", ["reduce", "repeat", "conceal", "divide"], "reduce"),
    ("Although the proposal was ambitious, the schedule remained _____.", ["feasible", "careless", "ordinary", "unrelated"], "feasible"),
    ("The witness gave an _____ account that did not favour either side.", ["impartial", "emotional", "invented", "hostile"], "impartial"),
]
CCAT_ANALOGIES = [
    ("Doctor", "Patient", "Teacher", ["Classroom", "Student", "Lesson", "School"], "Student"),
    ("Chef", "Kitchen", "Pilot", ["Runway", "Cockpit", "Ticket", "Airport"], "Cockpit"),
    ("Painter", "Brush", "Writer", ["Notebook", "Pen", "Library", "Idea"], "Pen"),
    ("Bird", "Nest", "Bee", ["Hive", "Honey", "Flower", "Wing"], "Hive"),
    ("Glove", "Hand", "Shoe", ["Sock", "Foot", "Lace", "Walk"], "Foot"),
    ("Thermometer", "Temperature", "Clock", ["Distance", "Weight", "Time", "Speed"], "Time"),
    ("Chapter", "Book", "Scene", ["Actor", "Play", "Stage", "Script"], "Play"),
    ("Sapling", "Tree", "Calf", ["Herd", "Grass", "Cow", "Farm"], "Cow"),
    ("Generous", "Selfish", "Cautious", ["Careful", "Reckless", "Patient", "Quiet"], "Reckless"),
    ("Whisper", "Speak", "Stroll", ["Run", "Walk", "Rest", "Stand"], "Walk"),
]
CCAT_ODD_ONE_OUT = [
    (["Sprint", "Jog", "Walk", "Whisper"], "Whisper"),
    (["Maple", "Oak", "Pine", "Copper"], "Copper"),
    (["Tablet", "Capsule", "Syrup", "Lantern"], "Lantern"),
    (["Violin", "Cello", "Guitar", "Trumpet"], "Trumpet"),
    (["Copper", "Iron", "Silver", "Granite"], "Granite"),
    (["Mercury", "Venus", "Mars", "Moon"], "Moon"),
    (["Triangle", "Square", "Pentagon", "Sphere"], "Sphere"),
    (["Novel", "Poem", "Essay", "Canvas"], "Canvas"),
    (["Minute", "Hour", "Second", "Metre"], "Metre"),
    (["January", "March", "July", "Monday"], "Monday"),
]
CCAT_SYNONYMS = [
    ("abundant", "plentiful", ["scarce", "narrow", "fragile"]),
    ("brief", "concise", ["ancient", "distant", "complex"]),
    ("diligent", "industrious", ["careless", "uncertain", "silent"]),
    ("obscure", "unclear", ["famous", "simple", "visible"]),
    ("reluctant", "unwilling", ["eager", "certain", "cheerful"]),
    ("verify", "confirm", ["ignore", "divide", "predict"]),
]
CCAT_ANTONYMS = [
    ("expand", "contract", ["extend", "explain", "include"]),
    ("frequent", "rare", ["regular", "common", "repeated"]),
    ("rigid", "flexible", ["solid", "strict", "fixed"]),
    ("transparent", "opaque", ["clear", "visible", "open"]),
    ("optimistic", "pessimistic", ["hopeful", "positive", "cheerful"]),
    ("permit", "forbid", ["allow", "request", "accept"]),
]
CCAT_CATEGORY_MATCHES = [
    ("Which option is a unit of electrical current?", "Ampere", ["Litre", "Metre", "Kelvin"]),
    ("Which option is a mammal?", "Dolphin", ["Trout", "Lizard", "Falcon"]),
    ("Which option is a programming language?", "Python", ["Falcon", "Mercury", "Sonnet"]),
    ("Which option is a form of precipitation?", "Sleet", ["Mist", "Dew", "Steam"]),
    ("Which option is a prime number?", "29", ["21", "27", "33"]),
    ("Which option is a renewable energy source?", "Wind", ["Coal", "Diesel", "Natural gas"]),
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


@dataclass
class GeneratedQuestion:
    section_type: str
    difficulty: str
    seed: str
    payload: dict
    correct_answer: dict

    def payload_json(self) -> str:
        return json.dumps(self.payload, sort_keys=True)

    def correct_answer_json(self) -> str:
        return json.dumps(self.correct_answer, sort_keys=True)


class BaseQuestionGenerator(ABC):
    section_type: str

    @abstractmethod
    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        raise NotImplementedError

    def rng(self, seed: str) -> random.Random:
        return random.Random(seed)


class ReasoningGenerator(BaseQuestionGenerator):
    section_type = "reasoning"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        entity_count = 2
        names = rng.sample(NAMES, entity_count)
        trait = rng.choice(TRAITS)
        stronger, weaker = rng.sample(names, 2)
        ask_for = rng.choice(["most", "least"])
        answer = stronger if ask_for == "most" else weaker
        statement_template = rng.choice(REASONING_COMPARISON_TEMPLATES)
        if "less" in statement_template:
            if statement_template.startswith("{left}") or "Compared with {right}, {left}" in statement_template:
                left, right = weaker, stronger
            else:
                left, right = stronger, weaker
        else:
            if statement_template.startswith("{left}") or "Compared with {right}, {left}" in statement_template:
                left, right = stronger, weaker
            else:
                left, right = weaker, stronger
        statements = [statement_template.format(left=left, right=right, trait=trait)]
        question = rng.choice(REASONING_QUESTION_TEMPLATES[ask_for]).format(trait=trait)

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "statements": statements,
                "question": question,
            },
            "options": names,
            "metadata": {
                "difficulty": difficulty,
                "trait": trait,
                "comparison_template": statement_template,
            },
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})


class PerceptualSpeedGenerator(BaseQuestionGenerator):
    section_type = "perceptual_speed"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        length = 4 if difficulty == "easy" else 6
        letter_pool = PERCEPTUAL_SPEED_LETTER_POOLS.get(difficulty, PERCEPTUAL_SPEED_LETTER_POOLS["medium"])
        pairs = []
        match_count = 0

        for _ in range(length):
            same = rng.random() < (0.55 if difficulty == "easy" else 0.45)
            left = rng.choice(letter_pool).upper()
            if same:
                right = left.lower()
                match_count += 1
            else:
                different = rng.choice([c.lower() for c in letter_pool if c.lower() != left.lower()])
                right = different
            pairs.append({"left": left, "right": right})

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": rng.choice(PERCEPTUAL_SPEED_INSTRUCTIONS),
                "pairs": pairs,
            },
            "options": list(range(length + 1)),
            "metadata": {
                "difficulty": difficulty,
                "letter_pool_size": len(letter_pool),
            },
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": match_count})


class NumberSpeedAccuracyGenerator(BaseQuestionGenerator):
    section_type = "number_speed_accuracy"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        upper = 50 if difficulty == "easy" else 200

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
                "instruction": "Which number is furthest from the middle value?",
                "numbers": numbers,
            },
            "options": numbers,
            "metadata": {"difficulty": difficulty},
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})


class WordMeaningGenerator(BaseQuestionGenerator):
    section_type = "word_meaning"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        queryset = WordMeaningItem.objects.filter(is_active=True)
        row = queryset.filter(difficulty=difficulty).order_by("?").first() or queryset.order_by("?").first()
        if row is None:
            raise ValueError("No word meaning items available.")

        words = [row.pair_word_1, row.pair_word_2, row.odd_word]
        rng.shuffle(words)

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": rng.choice(WORD_MEANING_INSTRUCTIONS),
                "words": words,
            },
            "options": words,
            "metadata": {
                "difficulty": difficulty,
                "relationship_type": row.relationship_type,
            },
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": row.odd_word})


class SpatialVisualizationGenerator(BaseQuestionGenerator):
    section_type = "spatial_visualization"
    LETTERS = ["b", "d", "f", "g", "j", "k", "n", "p", "q", "r", "y"]

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        letters = rng.sample(self.LETTERS, 2)
        pairs = []
        match_count = 0
        for letter in letters:
            is_same = rng.choice([True, False])
            if is_same:
                match_count += 1
            pairs.append({"letter": letter, "same": is_same})

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": "How many pairs show the same image?",
                "letter_pairs": pairs,
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


def _format_ccat_number(value: int | float) -> str:
    if isinstance(value, float):
        value = round(value, 2)
        if value.is_integer():
            return str(int(value))
    return str(value)


def _build_ccat_number_options(
    rng: random.Random,
    answer: int | float,
    distractors: list[int | float],
) -> tuple[list[str], str]:
    values = [answer]
    for value in distractors:
        normalized = round(value, 2) if isinstance(value, float) else value
        if normalized >= 0 and normalized not in values:
            values.append(normalized)

    offset = 1
    while len(values) < 4:
        candidate = round(answer + offset, 2)
        if candidate not in values:
            values.append(candidate)
        offset += 1

    options = [_format_ccat_number(value) for value in values[:4]]
    rng.shuffle(options)
    return options, _format_ccat_number(answer)


class CCATNumericalGenerator(BaseQuestionGenerator):
    section_type = "ccat_numerical"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        subtype = rng.choice(
            [
                "series",
                "percentage",
                "discount",
                "ratio",
                "work_rate",
                "average",
                "equation",
                "distance",
            ]
        )

        if subtype == "series":
            pattern = rng.choice(["arithmetic", "growing_gap", "geometric"])
            start = rng.randint(2, 12)
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
                gap = rng.randint(1, 4)
                growth = rng.randint(1, 3)
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
            percent = rng.choice([10, 20, 25, 30, 40, 50])
            base = rng.choice([40, 60, 80, 100, 120, 160, 200])
            answer = base * percent / 100
            distractors = [base - answer, base + answer, percent]
            prompt = {
                "instruction": "Calculate the percentage.",
                "question": f"What is {percent}% of {base}?",
            }
        elif subtype == "discount":
            base = rng.choice([40, 50, 60, 75, 80])
            markup = rng.choice([20, 25, 40])
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
            left = rng.randint(2, 7)
            right = rng.randint(2, 7)
            multiplier = rng.randint(3, 12)
            total = (left + right) * multiplier
            answer = left * multiplier
            distractors = [right * multiplier, total - left, total // left]
            prompt = {
                "instruction": "Use the ratio to find the requested share.",
                "question": f"A total of {total} items is divided in the ratio {left}:{right}. How many items are in the first share?",
            }
        elif subtype == "work_rate":
            workers = rng.randint(3, 6)
            days = rng.randint(4, 8)
            target_workers = rng.choice([value for value in range(2, 8) if value != workers])
            answer = round((workers * days) / target_workers, 2)
            distractors = [days - 1, days + 1, round((target_workers * days) / workers, 2)]
            prompt = {
                "instruction": "Use work-rate reasoning.",
                "question": f"If {workers} workers can finish a job in {days} days, how many days will {target_workers} workers need?",
            }
        elif subtype == "average":
            average = rng.randint(8, 30)
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
            answer = rng.randint(3, 20)
            coefficient = rng.randint(2, 8)
            constant = rng.randint(1, 15)
            result = coefficient * answer + constant
            distractors = [answer - 1, answer + 1, round(result / coefficient, 2)]
            prompt = {
                "instruction": "Solve for the unknown value.",
                "question": f"If {coefficient}x + {constant} = {result}, what is x?",
            }
        else:
            speed = rng.choice([30, 40, 45, 50, 60, 70])
            hours = rng.choice([2, 3, 4, 5])
            answer = speed * hours
            distractors = [speed + hours, speed * (hours - 1), speed * (hours + 1)]
            prompt = {
                "instruction": "Use the distance, speed, and time relationship.",
                "question": f"A vehicle travels at {speed} miles per hour for {hours} hours. How far does it travel?",
            }

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

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        subtype = rng.choice(
            ["analogy", "sentence_completion", "odd_one_out", "synonym", "antonym", "category"]
        )

        if subtype == "analogy":
            left, right, target, options, answer = rng.choice(CCAT_ANALOGIES)
            prompt = {
                "instruction": "Choose the option that completes the analogy.",
                "question": f"{left} is to {right} as {target} is to ___?",
            }
        elif subtype == "sentence_completion":
            question, options, answer = rng.choice(CCAT_SENTENCE_COMPLETIONS)
            prompt = {
                "instruction": "Choose the word that best completes the sentence.",
                "question": question,
            }
        elif subtype == "odd_one_out":
            options, answer = rng.choice(CCAT_ODD_ONE_OUT)
            prompt = {
                "instruction": "Choose the word that does not belong.",
                "question": "Which word does not belong with the others?",
            }
        elif subtype == "synonym":
            word, answer, distractors = rng.choice(CCAT_SYNONYMS)
            options = [answer, *distractors]
            prompt = {
                "instruction": "Choose the word with the closest meaning.",
                "question": f"Which word is most similar in meaning to '{word}'?",
            }
        elif subtype == "antonym":
            word, answer, distractors = rng.choice(CCAT_ANTONYMS)
            options = [answer, *distractors]
            prompt = {
                "instruction": "Choose the word with the opposite meaning.",
                "question": f"Which word is most opposite in meaning to '{word}'?",
            }
        else:
            question, answer, distractors = rng.choice(CCAT_CATEGORY_MATCHES)
            options = [answer, *distractors]
            prompt = {
                "instruction": "Choose the option that matches the category.",
                "question": question,
            }

        options = list(options)
        rng.shuffle(options)

        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": prompt,
                "options": options,
                "metadata": {"difficulty": difficulty, "subtype": subtype},
            },
            {"answer": answer},
        )


class CCATSpatialGenerator(BaseQuestionGenerator):
    section_type = "ccat_spatial"

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
        answer_visual = next(item for item in self.ROTATION_OPTIONS if item["rotation"] == rotations[-1])
        return {
            "subtype": "rotation",
            "question": f"Which option continues the {('clockwise' if step > 0 else 'counter-clockwise')} rotation?",
            "instruction": "Track the direction change from one shape to the next.",
            "stimulus": [
                *[{"shape": "triangle", "rotation": value} for value in rotations[:3]],
                {"shape": "missing"},
            ],
            "option_visuals": self.ROTATION_OPTIONS,
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

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        rule = rng.choice(
            [
                self._rotation_rule,
                self._fill_rotation_rule,
                self._mirror_rule,
                self._polygon_rule,
            ]
        )(rng)
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


GENERATOR_MAP = {
    "reasoning": ReasoningGenerator(),
    "perceptual_speed": PerceptualSpeedGenerator(),
    "number_speed_accuracy": NumberSpeedAccuracyGenerator(),
    "word_meaning": WordMeaningGenerator(),
    "spatial_visualization": SpatialVisualizationGenerator(),
    "ccat_numerical": CCATNumericalGenerator(),
    "ccat_verbal": CCATVerbalGenerator(),
    "ccat_spatial": CCATSpatialGenerator(),
}


def generate_question(
    section_type: str,
    difficulty: str,
    seed: str,
    conn=None,
) -> GeneratedQuestion:
    try:
        generator = GENERATOR_MAP[section_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported section type: {section_type}") from exc
    return generator.generate(difficulty=difficulty, seed=seed, conn=conn)
