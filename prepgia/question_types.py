from __future__ import annotations

import json
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass


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


def _choose_batch_balanced_variant(rng: random.Random, seed: str, variants: list):
    """Cycle through a shuffled family order for indexed question batches."""
    batch_seed, separator, position = seed.rpartition(":")
    if not separator or not position.isdigit():
        return rng.choice(variants)

    ordered_variants = list(variants)
    random.Random(batch_seed).shuffle(ordered_variants)
    return ordered_variants[int(position) % len(ordered_variants)]


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
    answer = round(answer, 2)
    values = [answer]
    for value in distractors:
        normalized = round(value, 2) if isinstance(value, float) else value
        if normalized not in values:
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


def semantic_question_signature(payload: dict) -> str:
    """Fingerprint the task, ignoring labels, hints and answer-option permutations."""
    prompt = {
        key: value
        for key, value in payload["prompt"].items()
        if key not in {"explanation", "instruction"}
    }
    for key in ("words", "numbers"):
        if key in prompt:
            prompt[key] = sorted(prompt[key])
    return json.dumps(prompt, sort_keys=True)
