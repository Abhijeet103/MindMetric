"""Independent interactive skill workshops; no official test scoring or replicas."""

import math
import random
from prepgia.passage_bank import PASSAGES
from prepgia.critical_scenarios import INSTRUCTIONS

WORKSHOPS = {
    "shl_verify": [
        ("schedule", "Calendar and scheduling"),
        ("chart_builder", "Build a data chart"),
        ("node_path", "Connect a sequence"),
    ],
    "consulting": [
        ("chart_insight", "Line and stacked-chart analysis"),
        ("market_estimate", "Market sizing and assumptions"),
        ("case", "Progressive case and recommendation"),
    ],
    "watson_glaser": [("passage", "Linked passage session")],
    "consulting_cases": [
        ("case", "Progressive case and recommendation"),
        ("market_estimate", "Market sizing and assumptions"),
        ("chart_insight", "Line and stacked-chart analysis"),
    ],
}
SECTIONS = {
    "schedule": "shl_deductive",
    "chart_builder": "shl_numerical",
    "node_path": "shl_inductive",
    "chart_insight": "consulting_math",
    "market_estimate": "consulting_math",
    "case": "linked_case",
    "passage": "wg_inference",
}


def make_workshop(kind, seed, passage=None):
    rng = random.Random(seed)
    stages = []
    if kind == "schedule":
        names = rng.sample(["Asha", "Ben", "Cora", "Dev", "Ella", "Finn"], 4)
        order = rng.sample(names, 4)
        stages = [
            {
                "kind": "schedule",
                "question": "Assign one person to each appointment slot so every rule holds. More than one valid schedule may exist.",
                "labels": ["09:00", "10:00", "11:00", "12:00"],
                "options": names,
                "rules": {
                    "before": [[order[0], order[1]], [order[1], order[3]]],
                    "not_adjacent": [order[0], order[3]],
                },
                "constraints": [
                    f"{order[0]} must be earlier than {order[1]}.",
                    f"{order[1]} must be earlier than {order[3]}.",
                    f"{order[0]} and {order[3]} cannot have adjacent appointments.",
                ],
                "explanation": "A valid schedule uses each person once, respects both earlier-than rules, and separates the non-adjacent pair. Any schedule meeting every rule is accepted.",
            }
        ]
        title = "Calendar constraints"
    elif kind == "chart_builder":
        total = rng.randint(20, 60) * 10
        a, b = rng.choice([20, 30, 40]), rng.choice([10, 20, 30])
        shares = [a, b, 100 - a - b]
        values = [total * share / 100 for share in shares]
        stages = [
            {
                "kind": "chart_builder",
                "question": f"A team processed {total} requests: {a}% online, {b}% by telephone and the remainder in person. Set each bar to the number of requests, not the percentage.",
                "labels": ["Online", "Telephone", "In person"],
                "answer": values,
                "explanation": f"Multiply each share by the total {total}: {values}. The values must sum to {total}. The remaining share is {shares[2]}%.",
            }
        ]
        title = "Construct the chart"
    elif kind == "node_path":
        start = rng.randrange(0, 10)
        increment = rng.choice([2, 3, 4])
        letter = rng.randint(0, 12)
        sequence = [
            value
            for i in range(4)
            for value in [chr(65 + letter + i), str(start + increment * (i + 1))]
        ]
        remaining = sequence[4:]
        decoys = [chr(65 + letter + 5), str(start + increment * 6)]
        nodes = remaining + decoys
        rng.shuffle(nodes)
        stages = [
            {
                "kind": "node_path",
                "question": f"Continue this alternating sequence: {' → '.join(sequence[:4])}. Select the next four nodes in order. Two offered nodes are distractors.",
                "options": nodes,
                "length": 4,
                "answer": remaining,
                "explanation": f"Letters advance one place and the interleaved numbers rise by {increment}. Next: {' → '.join(remaining)}. Both subsequences must be preserved.",
            }
        ]
        title = "Connect the sequence"
    elif kind == "chart_insight":
        base = rng.randint(30, 80) * 100
        growth = rng.choice([10, 20, 30])
        current = base * (1 + growth / 100)
        first, second = rng.randint(10, 30) * 100, rng.randint(40, 70) * 100
        series = [
            {"name": "Existing clients", "values": [first, first * 1.2]},
            {"name": "New clients", "values": [second, second * 0.8]},
        ]
        stages = [
            {
                "kind": "numeric",
                "question": "What is the percentage revenue change from January to March? Use a negative value for a decline.",
                "chart": {
                    "type": "line",
                    "title": "Monthly revenue (£)",
                    "labels": ["January", "February", "March"],
                    "values": [base, base * 0.9, current],
                },
                "answer": growth,
                "tolerance": 0.01,
                "explanation": f"Use the endpoints, not the February trough: ({current:g} − {base}) / {base} × 100 = {growth}%.",
            },
            {
                "kind": "numeric",
                "question": "In the second period, what percentage of total orders came from new clients? Round to two decimals.",
                "chart": {
                    "type": "stacked",
                    "title": "Orders by client segment",
                    "labels": ["Period 1", "Period 2"],
                    "series": series,
                },
                "answer": round(second * 0.8 / (first * 1.2 + second * 0.8) * 100, 2),
                "tolerance": 0.01,
                "explanation": f"New-client orders = {second * 0.8:g}; total = {first * 1.2 + second * 0.8:g}. Divide the segment by that period's total, rather than by the first-period total.",
            },
            {
                "kind": "choice",
                "question": "These charts record outcomes without a control group. Which conclusion is justified?",
                "options": [
                    "Revenue rose between the first and last months, but the charts alone do not identify its cause.",
                    "The charts prove marketing caused the revenue rise.",
                    "The March result guarantees the next month's revenue.",
                    "Every client bought more because total revenue rose.",
                ],
                "answer": "Revenue rose between the first and last months, but the charts alone do not identify its cause.",
                "explanation": "The endpoint comparison is observable. Cause, future outcomes and every individual's behaviour need additional evidence.",
            },
        ]
        title = "Chart-only evidence analysis"
    elif kind == "market_estimate":
        population = rng.randint(10, 30) * 10000
        stages = [
            {
                "kind": "estimate",
                "question": f"Estimate annual revenue for a new bicycle repair service in a city of {population:,} residents. No single estimate is expected. State assumptions about bicycle ownership, paid repairs per bicycle per year, achievable market share and revenue per repair. Give a range and explain what you would validate first.",
                "rubric": [
                    {
                        "label": "Structure",
                        "criterion": "Separate population, ownership, repair frequency, addressable share and price; avoid double-counting.",
                    },
                    {
                        "label": "Arithmetic and units",
                        "criterion": "Show a consistent multiplication chain ending in annual currency, with a sanity check.",
                    },
                    {
                        "label": "Uncertainty",
                        "criterion": "Provide a low/base/high range and identify the assumption with the largest effect.",
                    },
                    {
                        "label": "Evidence plan",
                        "criterion": "Name a practical source or paid pilot to test the key assumption; distinguish demand from interest.",
                    },
                ],
                "reference": f"Illustrative structure: {population:,} residents × 0.4 bicycles/resident × 0.5 paid repairs/bicycle/year × 0.1 captured share × £30/repair = £{population * 0.4 * 0.5 * 0.1 * 30:,.0f}/year. These are assumptions, not measured market facts. Different justified estimates are valid.",
                "explanation": "This is an open estimation exercise. Review your assumptions, range and evidence plan; the example is not a unique answer or an automated quality grade.",
            }
        ]
        title = "Market sizing with uncertainty"
    elif kind == "case":
        volume, price, cost = rng.randint(12, 30) * 100, rng.randint(12, 20) * 2, rng.randint(5, 9)
        fixed, saving, fee = rng.randint(4, 9) * 1000, rng.randint(2, 5), rng.randint(3, 9) * 1000
        baseline = volume * (price - cost) - fixed
        change = volume * saving - fee
        proposed = baseline + change
        intro = f"Cedar Service handles {volume:,} orders per month. Management wants higher monthly operating profit while preserving service quality. Work through the exhibits as they are released. Ignore tax and financing."
        current = {
            "caption": "Exhibit 1: current monthly operation",
            "columns": ["Measure", "Value"],
            "rows": [
                ["Orders/month", volume],
                ["Price (£/order)", price],
                ["Variable cost (£/order)", cost],
                ["Fixed cost (£/month)", fixed],
            ],
        }
        proposal = {
            "caption": "Exhibit 2: automation proposal",
            "columns": ["Measure", "Value"],
            "rows": [
                ["Variable-cost saving (£/order)", saving],
                ["Additional fee (£/month)", fee],
                ["Order volume and price", "Unchanged forecast"],
                ["Quality effect", "Not yet verified"],
            ],
        }
        recommendation_rubric = [
            {
                "label": "Recommendation",
                "criterion": "Give a clear conditional adopt/decline recommendation tied to incremental operating profit.",
            },
            {
                "label": "Quantitative support",
                "criterion": f"Use current £{baseline:,}, proposed £{proposed:,}, and incremental £{change:,} monthly profit, with units.",
            },
            {
                "label": "Risk and uncertainty",
                "criterion": "Recognise unchanged demand as an assumption and service quality as unverified; separate a forecast from certainty.",
            },
            {
                "label": "Next step",
                "criterion": "Specify a controlled pilot and a decision threshold for profit and quality, rather than requesting unspecified more data.",
            },
        ]
        stages = [
            {
                "kind": "written",
                "question": "Before receiving financial exhibits, outline the analysis you would use. Include revenue, variable/fixed costs, implementation effects, quality and demand risk.",
                "rubric": [
                    {
                        "label": "Structure",
                        "criterion": "Separate revenue, unit economics, fixed/one-off costs and risks without overlap.",
                    },
                    {
                        "label": "Decision criteria",
                        "criterion": "Define incremental profit and service quality as joint requirements.",
                    },
                ],
                "reference": "Compare current and proposed revenue less all incremental costs, then test quality and demand assumptions. Request cost and operating-volume exhibits before recommending a decision.",
                "explanation": "There are several defensible structures. Use the rubric to review coverage and avoid inventing unseen numbers.",
            },
            {
                "kind": "numeric",
                "question": "Using Exhibit 1, calculate current monthly operating profit (£).",
                "data_table": current,
                "answer": baseline,
                "tolerance": 0.01,
                "explanation": f"{volume} × ({price} − {cost}) − {fixed} = £{baseline:,}/month.",
            },
            {
                "kind": "numeric",
                "question": "Exhibit 2 has now arrived. Calculate proposed monthly profit (£) at the forecast volume. Quality remains unverified.",
                "data_table": proposal,
                "context_tables": [current],
                "answer": proposed,
                "tolerance": 0.01,
                "explanation": f"Incremental saving = {volume} × {saving} − {fee} = £{change:,}. Proposed profit = £{baseline:,} + £{change:,} = £{proposed:,}/month.",
            },
            {
                "kind": "numeric",
                "question": "At what minimum whole monthly order volume does the saving cover the added automation fee?",
                "data_table": proposal,
                "answer": math.ceil(fee / saving),
                "tolerance": 0,
                "explanation": f"Round up the fee divided by unit saving: ceiling({fee}/{saving}). Existing fixed costs cancel.",
            },
            {
                "kind": "choice",
                "question": "Which next evidence best tests the unverified quality constraint before committing?",
                "options": [
                    "A representative controlled pilot measuring error rates, rework and realised costs at the intended operating volume.",
                    "A larger revenue forecast that assumes quality is unchanged.",
                    "Supplier testimonials selected only from successful customers.",
                    "A staff preference survey with no output or cost measures.",
                ],
                "answer": "A representative controlled pilot measuring error rates, rework and realised costs at the intended operating volume.",
                "explanation": "A representative controlled pilot can test quality and realised economics; the other options do not verify the binding quality constraint.",
            },
            {
                "kind": "written",
                "question": "Write a concise recommendation to management. Include the decision, quantitative support, a caveat and a specific next step. Do not treat unverified quality as a fact.",
                "data_table": proposal,
                "context_tables": [current],
                "rubric": recommendation_rubric,
                "reference": f"At forecast volume, automation changes monthly profit by £{change:,} (from £{baseline:,} to £{proposed:,}). {'Consider adoption' if change > 0 else 'Do not adopt on these economics'} subject to verifying demand, costs and service quality. Use a representative pilot with explicit profit and quality thresholds before committing.",
                "explanation": "The rubric supports self or human review. It does not award an automated communication or hiring score.",
            },
        ]
        title = "Progressive consulting case"
        return {"title": title, "intro": intro, "key": f"case:{seed}", "stages": stages}
    elif kind == "passage":
        passage = passage or rng.choice(PASSAGES)
        stages = [
            {**q, "instruction": INSTRUCTIONS[q["skill"]], "passage": passage["body"]}
            for q in passage["items"]
        ]
        title = passage["title"]
        return {
            "title": title,
            "intro": "Read the shared passage. Each question uses its own critical-thinking decision rule. Judge each claim independently.",
            "key": passage["key"],
            "stages": stages,
            "editorial_snapshot": passage,
        }
    else:
        raise ValueError("Unknown workshop.")
    return {
        "title": title,
        "intro": "Original independent skill practice. Your work is saved after each submission.",
        "key": f"{kind}:{seed}",
        "stages": stages,
    }
