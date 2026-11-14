import itertools
import math
from collections import defaultdict
from dataclasses import asdict

from django.test import SimpleTestCase
from backend.apps.assessments.services import (
    _serialize_generated_question_for_player,
    _build_question_batch,
)
from prepgia.generators import GENERATOR_MAP
from prepgia.business_scenarios import MATH_FAMILIES
from prepgia.critical_scenarios import FAMILIES, INFERENCE_OPTIONS


class EnhancedBusinessContentTests(SimpleTestCase):
    def test_business_answers_independently_derive_from_exhibits(self):
        covered = set()
        for difficulty in ("easy", "medium", "hard"):
            for i in range(160):
                q = GENERATOR_MAP["consulting_math"].generate(difficulty, f"business:{i}")
                family = q.payload["metadata"]["subtype"]
                covered.add(family)
                rows = q.payload["prompt"]["data_table"]["rows"]
                values = [r[1] for r in rows]
                if family == "market_funnel":
                    pop, eligible, adoption, frequency, price = values
                    expected = pop * eligible * adoption * frequency * price / 10000
                elif family == "break_even":
                    price, cost, fee, fixed = values
                    expected = math.ceil(fixed / (price - cost - fee))
                elif family == "price_volume":
                    units, price, cost, rise, fall = values
                    original_revenue = units * price
                    new_revenue = units * (1 - fall / 100) * price * (1 + rise / 100)
                    expected = (
                        (new_revenue / original_revenue - 1) * 100
                        if difficulty == "easy"
                        else new_revenue - units * (1 - fall / 100) * cost - units * (price - cost)
                    )
                elif family == "capacity_yield":
                    days, hours, rate, yield_pct, demand = values
                    expected = min(math.floor(days * hours * rate * yield_pct / 100), demand)
                elif family == "weighted_margin":
                    revenue = sum(r[1] * r[2] for r in rows)
                    expected = 100 * (revenue - sum(r[1] * r[3] for r in rows)) / revenue
                elif family == "currency":
                    euros, eur_per_gbp, duty, freight = values
                    expected = euros / eur_per_gbp + (euros / eur_per_gbp) * duty / 100 + freight
                elif family == "compound_growth":
                    revenue, first, second = values
                    expected = revenue + revenue * first / 100
                    expected += expected * second / 100
                else:
                    expected = rows[1][1] / rows[1][2] - rows[0][1] / rows[0][2]
                self.assertAlmostEqual(
                    float(q.correct_answer["answer"]), round(expected, 2), places=2
                )
        self.assertEqual(covered, set(MATH_FAMILIES))

    def test_case_arithmetic_and_shared_exhibits_for_all_scenarios(self):
        covered = set()
        for section in ("linked_case", "consulting_case"):
            for difficulty in ("easy", "medium", "hard"):
                for case in range(45):
                    questions = [
                        GENERATOR_MAP[section].generate(difficulty, f"case-audit-{case}:{step}")
                        for step in range(4)
                    ]
                    family = questions[0].payload["metadata"]["subtype"].split("_step_")[0]
                    covered.add(family)
                    prompts = [q.payload["prompt"] for q in questions]
                    for key in ("data_table", "chart"):
                        self.assertTrue(all(p[key] == prompts[0][key] for p in prompts))
                    self.assertEqual(
                        [p["case_study"]["question_index"] for p in prompts], [1, 2, 3, 4]
                    )
                    rows = prompts[0]["data_table"]["rows"]
                    if family == "automation":
                        volume, price, variable, fixed = [r[1] for r in rows]
                        new_variable, new_fixed = rows[2][2], rows[3][2]
                        expected = [
                            volume * price - volume * variable - fixed,
                            volume * price - volume * new_variable - new_fixed,
                            math.ceil((new_fixed - fixed) / (variable - new_variable)),
                        ]
                    elif family == "market_entry":
                        (
                            population,
                            eligible,
                            capture,
                            frequency,
                            price,
                            variable,
                            fixed,
                            switch,
                            lost,
                        ) = [r[1] for r in rows]
                        buyers = population * eligible / 100 * capture / 100
                        net_unit = frequency * (price - variable) - switch / 100 * lost
                        expected = [buyers, buyers * net_unit - fixed, math.ceil(fixed / net_unit)]
                        self.assertIn("paid pilot", questions[3].correct_answer["answer"])
                    else:
                        days, hours, a, b, extra, yield_pct, demand, price, variable, fee = [
                            r[1] for r in rows
                        ]
                        old = math.floor(days * hours * min(a, b) * yield_pct / 100)
                        new = math.floor(days * hours * min(a, b + extra) * yield_pct / 100)
                        added_sales = min(demand, new) - min(demand, old)
                        change = added_sales * (price - variable) - fee
                        expected = [old, added_sales, change]
                        self.assertTrue(
                            questions[3]
                            .correct_answer["answer"]
                            .startswith("Upgrade:" if change > 0 else "Keep")
                        )
                    for q, value in zip(questions, expected):
                        self.assertAlmostEqual(float(q.correct_answer["answer"]), value, places=2)
        self.assertEqual(covered, {"automation", "market_entry", "capacity"})

    def test_normal_and_mixed_forms_keep_all_case_exhibits_consistent(self):
        for section in ("linked_case", "consulting_case"):
            rows = _build_question_batch(321, section, "audit", 24, "mixed")
            for start in range(0, 24, 4):
                group = rows[start : start + 4]
                self.assertEqual(
                    len({q["payload"]["prompt"]["case_study"]["id"] for q in group}), 1
                )
                self.assertEqual(len({q["difficulty"] for q in group}), 1)
                self.assertTrue(
                    all(
                        q["payload"]["prompt"]["data_table"]
                        == group[0]["payload"]["prompt"]["data_table"]
                        for q in group
                    )
                )


class EnhancedReasoningTests(SimpleTestCase):
    def test_feasible_schedules_have_exactly_one_valid_offered_option(self):
        count = 0
        for difficulty in ("easy", "medium", "hard"):
            for i in range(120):
                q = GENERATOR_MAP["shl_deductive"].generate(difficulty, f"schedule:{i}")
                meta = q.payload["metadata"]
                if meta["subtype"] != "feasible_schedule":
                    continue
                count += 1

                def legal(order):
                    return all(
                        order.index(a) < order.index(b) for a, b in meta["constraints"]
                    ) and (
                        not meta["not_adjacent"]
                        or abs(
                            order.index(meta["not_adjacent"][0])
                            - order.index(meta["not_adjacent"][1])
                        )
                        > 1
                    )

                valid_options = [
                    option for option in q.payload["options"] if legal(option.split(" → "))
                ]
                self.assertEqual(valid_options, [q.correct_answer["answer"]])
                # Incomplete information really allows multiple possible worlds.
                self.assertGreater(
                    sum(legal(order) for order in itertools.permutations(meta["people"])), 1
                )
        self.assertGreater(count, 60)

    def test_compound_visual_answer_satisfies_movement_and_fill(self):
        count = 0
        positions = ["top_left", "top_right", "bottom_right", "bottom_left"]
        for difficulty in ("easy", "medium", "hard"):
            for i in range(100):
                q = GENERATOR_MAP["shl_inductive"].generate(difficulty, f"compound:{i}")
                meta = q.payload["metadata"]
                if meta["subtype"] != "compound_movement":
                    continue
                count += 1
                previous = q.payload["prompt"]["stimulus"][-2]["marks"]
                expected = [
                    {
                        **m,
                        "position": positions[
                            (positions.index(m["position"]) + meta["direction"]) % 4
                        ],
                        "filled": not m["filled"],
                    }
                    for m in previous
                ]
                visuals = q.payload["option_visuals"]
                correct = next(o for o in visuals if o["value"] == q.correct_answer["answer"])
                self.assertEqual(correct["marks"], expected)
                self.assertEqual(len(visuals), 4)
                self.assertEqual(
                    len(
                        {
                            str(
                                sorted((m["shape"], m["position"], m["filled"]) for m in o["marks"])
                            )
                            for o in visuals
                        }
                    ),
                    4,
                )
        self.assertEqual(count, 150)

    def test_critical_family_coverage_balanced_answers_and_interpretation_math(self):
        for skill, families in FAMILIES.items():
            covered, outcomes = set(), defaultdict(int)
            for difficulty in ("easy", "medium", "hard"):
                for i in range(180):
                    q = GENERATOR_MAP[f"wg_{skill}"].generate(difficulty, f"reasoning:{i}")
                    family = q.payload["metadata"]["subtype"]
                    covered.add(family)
                    answer = q.correct_answer["answer"]
                    outcomes[answer] += 1
                    if skill == "interpretation" and family == "weighted_rates":
                        rows = q.payload["prompt"]["data_table"]["rows"]
                        self.assertTrue(all(r[4] / r[3] > r[2] / r[1] for r in rows))
                        self.assertLess(
                            sum(r[4] for r in rows) / sum(r[3] for r in rows),
                            sum(r[2] for r in rows) / sum(r[1] for r in rows),
                        )
                    serialized = _serialize_generated_question_for_player(asdict(q), False)
                    self.assertNotIn("correct_answer", serialized)
                    self.assertNotIn("explanation", serialized)
                    self.assertNotIn("metadata", serialized)
            self.assertEqual(covered, set(families))
            self.assertEqual(
                set(outcomes),
                set(INFERENCE_OPTIONS)
                if skill == "inference"
                else {"Assumption made", "Assumption not made"}
                if skill == "assumptions"
                else {"Strong", "Weak"}
                if skill == "arguments"
                else {"Follows", "Does not follow"},
            )
            self.assertGreater(min(outcomes.values()), 50)

    def test_strong_arguments_include_support_and_opposition(self):
        stances = set()
        for i in range(180):
            q = GENERATOR_MAP["wg_arguments"].generate("hard", f"stance:{i}")
            if q.correct_answer["answer"] == "Strong":
                stances.add(
                    q.payload["prompt"]["question"].split("Argument: ")[1].split(".")[0][:3]
                )
        self.assertEqual(stances, {"Yes", "No"})
