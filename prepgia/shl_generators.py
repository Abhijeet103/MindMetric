"""Original SHL-style skill drills, independent of publisher item banks.

These fixed practice forms are not adaptive SHL Verify replicas. Numerical data,
logic constraints and answer derivations are generated together for validation.
"""

from __future__ import annotations

import math
import uuid

from prepgia.question_types import (
    BaseQuestionGenerator,
    GeneratedQuestion,
    _build_ccat_number_options,
    _choose_batch_balanced_variant,
    _format_ccat_number,
)


class SHLNumericalGenerator(BaseQuestionGenerator):
    section_type = "shl_numerical"
    FAMILIES = [
        "growth",
        "share",
        "profit",
        "weighted_average",
        "ratio",
        "difference",
        "revenue_growth",
        "contribution_margin",
        "target_profit",
    ]

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        level = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
        subtype = _choose_batch_balanced_variant(rng, seed, self.FAMILIES)
        departments = rng.sample(
            ["North", "South", "East", "West", "Central", "Coastal"], level + 1
        )
        rows = []
        for name in departments:
            previous = rng.randint(5, 20 * level) * 20
            change = rng.choice([-20, -10, 10, 20, 25, 50])
            current = previous * (100 + change) // 100
            price = rng.randint(3, 12) * 5
            cost = price - rng.randint(1, 4) * 2
            rows.append([name, previous, current, price, cost])
        name, previous, current, price, cost = rows[0]
        if subtype == "growth":
            question = f"What is the percentage change in units sold by {name} from last year to this year? Enter a negative percentage for a decrease."
            answer = (current - previous) / previous * 100
            wrong = [(current - previous) / current * 100, abs(answer), 100 + answer]
            explanation = f"Percentage change uses last year's base: ({current} − {previous}) / {previous} × 100 = {_format_ccat_number(answer)}%."
        elif subtype == "share":
            total = sum(row[2] for row in rows)
            answer = current / total * 100
            question = f"What percentage of this year's total units sold came from {name}?"
            wrong = [
                previous / total * 100,
                current / sum(row[1] for row in rows) * 100,
                100 - answer,
            ]
            explanation = f"Total current units = {total}. {name}'s share = {current}/{total} × 100 = {_format_ccat_number(answer)}%."
        elif subtype == "profit":
            answer = sum(row[2] * (row[3] - row[4]) for row in rows)
            question = "What is the total contribution this year across all regions (sales revenue minus variable costs, before fixed costs)?"
            wrong = [
                sum(row[2] * row[3] for row in rows),
                sum(row[2] * row[4] for row in rows),
                current * (price - cost),
            ]
            explanation = (
                "Sum units × (price − variable cost) for each region: "
                + " + ".join(f"{row[2]} × ({row[3]} − {row[4]})" for row in rows)
                + f" = £{answer}."
            )
        elif subtype == "weighted_average":
            total = sum(row[2] for row in rows)
            revenue = sum(row[2] * row[3] for row in rows)
            answer = revenue / total
            question = "What is the average selling price per unit this year across all regions, weighted by units sold?"
            wrong = [
                sum(row[3] for row in rows) / len(rows),
                revenue / sum(row[1] for row in rows),
                answer + 5,
            ]
            explanation = f"Divide total revenue £{revenue} by total units {total}: £{_format_ccat_number(answer)} per unit. A simple average of regional prices ignores volumes."
        elif subtype == "ratio":
            other = rows[1]
            answer = current / other[2]
            question = f"How many times {other[0]}'s current units did {name} sell this year?"
            wrong = [other[2] / current, previous / other[1], answer + 1]
            explanation = f"Divide {name}'s {current} units by {other[0]}'s {other[2]} units: {_format_ccat_number(answer)} times."
        elif subtype == "revenue_growth":
            previous_revenue = sum(r[1] * r[3] for r in rows)
            current_revenue = sum(r[2] * r[3] for r in rows)
            answer = (current_revenue / previous_revenue - 1) * 100
            question = "What is the percentage change in total revenue across all regions? Use the unchanged regional prices and a negative percentage for a decline."
            wrong = [
                100 * (sum(r[2] for r in rows) / sum(r[1] for r in rows) - 1),
                100 * (current_revenue - previous_revenue) / current_revenue,
                current_revenue / previous_revenue * 100,
            ]
            explanation = f"Previous revenue = £{previous_revenue:,}; current revenue = £{current_revenue:,}. Change = ({current_revenue}/{previous_revenue} − 1) × 100 = {answer:.2f}%. Different prices mean unit growth is not necessarily revenue growth."
        elif subtype == "contribution_margin":
            revenue = sum(r[2] * r[3] for r in rows)
            contribution = sum(r[2] * (r[3] - r[4]) for r in rows)
            answer = 100 * contribution / revenue
            question = "What is this year's total contribution margin, as a percentage of total sales revenue?"
            wrong = [
                100 * contribution / (revenue - contribution),
                sum(100 * (r[3] - r[4]) / r[3] for r in rows) / len(rows),
                contribution / sum(r[2] for r in rows),
            ]
            explanation = f"Contribution = £{contribution:,}; revenue = £{revenue:,}. Divide contribution by revenue, not by costs: {contribution}/{revenue} × 100 = {answer:.2f}%."
        elif subtype == "target_profit":
            target = rng.randint(10, 30) * 1000 * level
            fixed = rng.randint(2, 8) * 1000
            answer = math.ceil((target + fixed) / (price - cost))
            question = f"If {name} operates alone at its listed price and variable cost, how many whole units must it sell to earn at least £{target:,} annual operating profit after £{fixed:,} fixed costs? There is no capacity or demand limit."
            wrong = [
                target / (price - cost),
                (target + fixed) / price,
                (target - fixed) / (price - cost),
            ]
            explanation = f"Required contribution = target profit + fixed costs = £{target + fixed:,}. Divide by unit contribution £{price - cost}, then round up: {answer:,} units."
        else:
            other = rows[1]
            answer = (current * price) - (other[2] * other[3])
            question = f"What is {name}'s sales revenue minus {other[0]}'s sales revenue this year? Use a negative amount if {name}'s revenue is lower."
            wrong = [abs(answer), current - other[2], (previous * price) - (other[1] * other[3])]
            explanation = f"{current} × £{price} − {other[2]} × £{other[3]} = £{_format_ccat_number(answer)}. Compare revenues, not units."
        options, correct = _build_ccat_number_options(rng, answer, wrong)
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": {
                    "instruction": "Use the table. Round your answer to two decimal places where necessary. A calculator is allowed for this practice module.",
                    "question": question,
                    "explanation": explanation,
                    "data_table": {
                        "caption": "Regional sales; prices and costs are per unit and unchanged between years",
                        "columns": [
                            "Region",
                            "Last year: units",
                            "This year: units",
                            "Price (£)",
                            "Variable cost (£)",
                        ],
                        "rows": rows,
                    },
                },
                "options": options,
                "metadata": {"difficulty": difficulty, "subtype": subtype, "generator_version": 2},
            },
            {"answer": correct},
        )


class SHLDeductiveGenerator(BaseQuestionGenerator):
    section_type = "shl_deductive"
    FAMILIES = ["ordering", "conditional", "syllogism", "scheduling", "feasible_schedule"]

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        level = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
        subtype = _choose_batch_balanced_variant(rng, seed, self.FAMILIES)
        names = rng.sample(
            ["Asha", "Ben", "Cora", "Dev", "Ella", "Finn", "Gita", "Hugo"], level + 2
        )
        metadata = {"difficulty": difficulty, "subtype": subtype, "generator_version": 2}
        if subtype in {"ordering", "scheduling"}:
            order = rng.sample(names, len(names))
            constraints = list(zip(order, order[1:]))
            rng.shuffle(constraints)
            rank = rng.randrange(len(names))
            if subtype == "ordering":
                statements = [f"{first} finishes before {second}." for first, second in constraints]
                question = (
                    " ".join(statements)
                    + f" There are no ties. Who finishes in position {rank + 1}?"
                )
            else:
                statements = [
                    f"{first}'s appointment is earlier than {second}'s."
                    for first, second in constraints
                ]
                question = (
                    " ".join(statements)
                    + f" Each person has one different slot, with no other appointments. Who occupies slot {rank + 1}, counting from earliest?"
                )
            answer = order[rank]
            options = list(names)
            explanation = (
                "The only order consistent with all the constraints is "
                + " → ".join(order)
                + f". Position {rank + 1} is {answer}."
            )
            metadata.update({"constraints": constraints, "rank": rank, "people": names})
        elif subtype == "feasible_schedule":
            import itertools

            order = rng.sample(names, len(names))
            constraints = [(order[0], order[1])]
            if level > 1:
                constraints.append((order[1], order[-1]))
            not_adjacent = (order[0], order[-1]) if level == 3 else None

            def valid(candidate):
                return all(candidate.index(a) < candidate.index(b) for a, b in constraints) and (
                    not not_adjacent
                    or abs(candidate.index(not_adjacent[0]) - candidate.index(not_adjacent[1])) != 1
                )

            permutations = list(itertools.permutations(names))
            legal = [candidate for candidate in permutations if valid(candidate)]
            illegal = [candidate for candidate in permutations if not valid(candidate)]
            selected = rng.choice(legal)
            answer = " → ".join(selected)
            options = [answer, *[" → ".join(candidate) for candidate in rng.sample(illegal, 3)]]
            statements = [f"{a} is earlier than {b}." for a, b in constraints]
            if not_adjacent:
                statements.append(
                    f"{not_adjacent[0]} and {not_adjacent[1]} cannot occupy adjacent slots."
                )
            question = (
                " ".join(statements)
                + " Each person occupies one distinct slot, with no empty slots. Which proposed schedule satisfies every rule, from earliest to latest?"
            )
            explanation = f"{answer} obeys every precedence and adjacency constraint. Other schedules may also be possible, but each other offered option violates at least one stated rule."
            metadata.update(people=names, constraints=constraints, not_adjacent=not_adjacent)
        elif subtype == "conditional":
            codes = rng.sample(range(100, 999), level + 2)
            statements = [
                f"If a file has label {a}, it must also have label {b}."
                for a, b in zip(codes, codes[1:])
            ]
            forward = rng.choice([True, False])
            if forward:
                question = (
                    " ".join(statements)
                    + f" File K has label {codes[0]}. Must it have label {codes[-1]}?"
                )
                answer = "Yes"
                explanation = (
                    "Follow the implications in the stated direction: "
                    + " → ".join(map(str, codes))
                    + "."
                )
            else:
                question = (
                    " ".join(statements)
                    + f" File K has label {codes[-1]}. Must it have label {codes[0]}?"
                )
                answer = "Cannot be determined"
                explanation = "An implication cannot be reversed: the final label can occur without the first. The rules give no converse."
            options = ["Yes", "No; it cannot have that label", "Cannot be determined"]
        else:
            categories = rng.sample(
                ["auditors", "planners", "analysts", "reviewers", "coordinators", "advisers"],
                level + 2,
            )
            statements = [f"All {a} are {b}." for a, b in zip(categories, categories[1:])]
            negative = rng.choice([True, False])
            if negative:
                statements.append(f"No {categories[-1]} are contractors.")
                conclusion = f"No {categories[0]} are contractors."
                answer = "Follows"
                explanation = "The first group is contained in every subsequent group; the final group excludes contractors, so the first group excludes them too."
            else:
                conclusion = f"All {categories[-1]} are {categories[0]}."
                answer = "Does not follow"
                explanation = "Group inclusion works in one direction. Members of the final group need not belong to the first group."
            question = (
                " ".join(statements)
                + f" Conclusion: {conclusion} Does it logically follow using only these statements?"
            )
            options = ["Follows", "Does not follow"]
        rng.shuffle(options)
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": {
                    "instruction": "Use only the stated rules. Do not assume their converses.",
                    "question": question,
                    "explanation": explanation,
                },
                "options": options,
                "metadata": metadata,
            },
            {"answer": answer},
        )
