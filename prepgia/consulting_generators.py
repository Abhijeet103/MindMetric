"""Original practice content; publisher samples are linked separately."""

import math
import uuid
from prepgia.question_types import (
    BaseQuestionGenerator,
    GeneratedQuestion,
    _build_ccat_number_options,
    _choose_batch_balanced_variant,
)

DOMAINS = [
    ("delivery depot", "parcels", "dispatch labels"),
    ("library", "books", "catalogue labels"),
    ("retailer", "orders", "tracking codes"),
    ("training provider", "applications", "review codes"),
    ("equipment rental company", "reservations", "booking codes"),
    ("software company", "support requests", "priority labels"),
    ("manufacturer", "components", "quality labels"),
    ("travel company", "bookings", "confirmation codes"),
]


def question(section, difficulty, seed, prompt, options, answer, subtype):
    return GeneratedQuestion(
        section,
        difficulty,
        seed,
        {
            "question_id": str(uuid.uuid4()),
            "section_type": section,
            "prompt": prompt,
            "options": options,
            "metadata": {
                "difficulty": difficulty,
                "subtype": subtype,
                "provenance": "original",
                "generator_version": 2,
            },
        },
        {"answer": answer},
    )


class ConsultingMathGenerator(BaseQuestionGenerator):
    section_type = "consulting_math"

    def generate(self, difficulty, seed, conn=None):
        from prepgia.business_scenarios import business_math

        rng = self.rng(seed)
        prompt, answer, wrong, family = business_math(rng, difficulty, seed)
        options, answer = _build_ccat_number_options(rng, answer, wrong)
        return question(self.section_type, difficulty, seed, prompt, options, answer, family)


class CriticalThinkingGenerator(BaseQuestionGenerator):
    def __init__(self, section_type):
        self.section_type = section_type

    def generate(self, difficulty, seed, conn=None):
        from prepgia.critical_scenarios import build_critical

        rng = self.rng(seed)
        prompt, options, answer, family = build_critical(
            rng, self.section_type, difficulty, seed, rng.choice(DOMAINS)[0]
        )
        rng.shuffle(options)
        return question(self.section_type, difficulty, seed, prompt, options, answer, family)


class ConsultingEvidenceGenerator(BaseQuestionGenerator):
    section_type = "consulting_evidence"

    def generate(self, difficulty, seed, conn=None):
        rng = self.rng(seed)
        level = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
        firm, objects, _ = rng.choice(DOMAINS)
        before = rng.randint(20, 60)
        after = before + rng.randint(5, 25)
        sample = rng.randint(5, 20) * 20 * level
        family = _choose_batch_balanced_variant(
            rng,
            seed,
            ["causality", "sampling", "decision", "comparison", "base_rate", "opportunity_cost"],
        )
        if family == "causality":
            passage = f"A {firm} introduced a training programme. Productivity rose from {before} to {after} {objects} per employee per day. During the same period, demand and staffing changed."
            query = "Which evidence would best isolate the effect of the training?"
            answer = "A randomly assigned comparison with a similar untrained group over the same period."
            options = [
                answer,
                "A larger before-and-after chart with no comparison group.",
                "Testimonials from the employees who liked the training most.",
                "The training supplier's total sales across all clients.",
            ]
            explanation = "A contemporaneous randomised comparison helps separate the training effect from other changes. A before-and-after increase alone cannot do that."
        elif family == "sampling":
            passage = f"A {firm} surveyed {sample} customers who had voluntarily joined its loyalty club; {after}% wanted a premium service. It wants to estimate demand among all customers."
            query = "Which additional evidence most directly addresses the sampling limitation?"
            answer = "A representative random sample including customers who are not in the loyalty club."
            options = [
                answer,
                "Surveying more members of the same club only.",
                "Repeating the same question to the same respondents.",
                "Using only responses from customers who have already bought premium services.",
            ]
            explanation = "The issue is selection bias, not just sample size. Non-members must be represented when estimating all-customer demand."
        elif family == "comparison":
            treated = rng.randint(8, 20) * level
            control = rng.randint(2, 7) * level
            passage = f"A {firm} tested a workflow. Output per worker rose by {treated}% in the pilot group and {control}% in an otherwise comparable group without the workflow. The groups had equal initial output, and assume no differential influences other than the workflow."
            query = "What uplift in percentage points is attributable to the workflow under these assumptions?"
            options, answer = _build_ccat_number_options(
                rng, treated - control, [treated, control, treated / control]
            )
            explanation = f"Subtract the contemporaneous comparison-group change: {treated} − {control} = {treated - control} percentage points. The pilot's entire gain includes the shared trend."
        elif family == "base_rate":
            total = rng.randint(10, 40) * 100 * level
            defects = total // 100
            caught = defects * 80 // 100
            false_alerts = (total - defects) * 10 // 100
            passage = f"A {firm} checked a complete batch of {total} items. The inspection raised {caught} alerts on genuinely defective items and {false_alerts} alerts on sound items. Each alert refers to one different item."
            query = "What percentage of alerts identified a genuine defect? Round to two decimal places."
            options, answer = _build_ccat_number_options(
                rng, 100 * caught / (caught + false_alerts), [80, 90, 100 * caught / total]
            )
            explanation = f"Use all alerts as the denominator: {caught} / ({caught} + {false_alerts}) × 100 = {100 * caught / (caught + false_alerts):.2f}%. Sensitivity or overall accuracy does not answer the question."
        elif family == "opportunity_cost":
            gross = rng.randint(20, 40) * 1000 * level
            direct = rng.randint(5, 10) * 1000 * level
            displaced = rng.randint(2, 6) * 1000 * level
            passage = f"A {firm} can accept a special contract worth £{gross:,}. It adds £{direct:,} direct costs and uses capacity that would otherwise earn £{displaced:,} contribution on existing work. Existing fixed overhead is unchanged."
            query = (
                "What is the contract's incremental operating profit (£), including displaced work?"
            )
            options, answer = _build_ccat_number_options(
                rng,
                gross - direct - displaced,
                [gross - direct, gross - displaced, gross + displaced - direct],
            )
            explanation = f"Incremental profit = £{gross:,} − £{direct:,} − £{displaced:,} = £{gross - direct - displaced:,}. Lost contribution is a real opportunity cost; unchanged overhead is not incremental."
        else:
            saving = rng.randint(5, 20) * 1000 * level
            cost = rng.randint(2, 8) * 1000 * level
            passage = f"A {firm} can automate processing. Verified annual gross savings are £{saving:,}; recurring fees are £{cost:,}. A one-time implementation cost has not yet been estimated."
            query = "What additional figure is needed to calculate first-year net savings?"
            answer = "The one-time implementation cost."
            options = [
                answer,
                "The supplier's gross global revenue.",
                "The annual recurring fee, which is already included in the passage.",
                "The current volume of orders, assuming the verified savings remain unchanged.",
            ]
            explanation = "First-year net savings equal gross savings minus recurring fees and the one-time implementation cost."
        rng.shuffle(options)
        return question(
            self.section_type,
            difficulty,
            seed,
            {
                "instruction": "Select the evidence or calculation relevant to the decision.",
                "question": passage + " " + query,
                "explanation": explanation,
            },
            options,
            answer,
            family,
        )


class LinkedCaseGenerator(BaseQuestionGenerator):
    section_type = "linked_case"
    group_size = 4

    def generate(self, difficulty, seed, conn=None):
        prefix, _, index = seed.rpartition(":")
        index = int(index) if index.isdigit() else 0
        case_rng = self.rng(f"{prefix}:case:{index // 4}")
        level = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
        company = case_rng.choice(
            [
                "Harbour Rentals",
                "Cedar Services",
                "Orbit Supplies",
                "Maple Logistics",
                "Aster Packaging",
                "Beacon Print",
                "Ridge Dispatch",
                "Willow Equipment",
            ]
        )
        from prepgia.business_scenarios import CASE_FAMILIES, additional_case

        family = _choose_batch_balanced_variant(case_rng, f"{prefix}:{index // 4}", CASE_FAMILIES)
        if family != "automation":
            prompt, answer, wrong = additional_case(
                case_rng, family, level, company, f"{company}:{prefix}:{index // 4}", index % 4
            )
            if isinstance(answer, str):
                options = [answer, *wrong]
                self.rng(seed).shuffle(options)
            else:
                options, answer = _build_ccat_number_options(self.rng(seed), answer, wrong)
            return question(
                self.section_type,
                difficulty,
                seed,
                prompt,
                options,
                answer,
                f"{family}_step_{index % 4 + 1}",
            )
        volume = case_rng.randint(5, 25) * 100 * level
        price = case_rng.randint(10, 25) * 2
        variable = case_rng.randint(3, 8) * 2
        fixed = case_rng.randint(2, 6) * 1000
        saving = case_rng.randint(2, 6)
        fee = case_rng.randint(2, 15) * 500 * level
        baseline = volume * (price - variable) - fixed
        proposed = volume * (price - variable + saving) - fixed - fee
        step = index % 4
        rng = self.rng(seed)
        case = {
            "id": f"{company}:{prefix}:{index // 4}",
            "title": f"{company}: automation decision",
            "background": f"{company} processes {volume:,} orders monthly. Price, demand and product quality are expected to stay unchanged. An automation proposal reduces variable cost per order by £{saving}, but adds a fixed £{fee:,} monthly fee. All figures are monthly; ignore tax and financing.",
            "question_index": step + 1,
            "question_total": 4,
        }
        prompt = {
            "instruction": "Use the shared case exhibits. A calculator is allowed.",
            "case_study": case,
            "data_table": {
                "caption": "Monthly operating plan",
                "columns": ["Measure", "Current", "Proposed"],
                "rows": [
                    ["Orders", volume, volume],
                    ["Price per order (£)", price, price],
                    ["Variable cost per order (£)", variable, variable - saving],
                    ["Fixed costs (£)", fixed, fixed + fee],
                ],
            },
            "chart": {
                "title": "Revenue and operating costs (£ per month)",
                "labels": ["Current revenue", "Current costs", "Proposed costs"],
                "values": [
                    volume * price,
                    volume * variable + fixed,
                    volume * (variable - saving) + fixed + fee,
                ],
            },
        }
        if step == 0:
            answer = baseline
            text = "What is current monthly operating profit?"
            wrong = [volume * (price - variable), volume * price - fixed, baseline - fixed]
            explanation = f"Profit = {volume} × ({price} − {variable}) − {fixed} = £{baseline:,}."
        elif step == 1:
            answer = proposed
            text = "What would monthly operating profit be after automation?"
            wrong = [baseline + volume * saving, baseline - fee, proposed - fee]
            explanation = f"Proposed profit = {volume} × ({price} − {variable - saving}) − ({fixed} + {fee}) = £{proposed:,}. Include the additional fee."
        elif step == 2:
            answer = math.ceil(fee / saving)
            text = "What is the minimum whole number of monthly orders at which the variable-cost saving covers the additional monthly automation fee?"
            wrong = [math.floor(fee / saving), fee * saving, math.ceil(fee / (price - variable))]
            explanation = f"Incremental break-even volume = ceiling({fee}/{saving}) = {answer:,} orders. The existing fixed cost is unchanged and cancels from this comparison."
        else:
            adopt = proposed > baseline
            answer = (
                "Adopt automation under the stated assumptions."
                if adopt
                else "Keep the current process under the stated assumptions."
            )
            text = "The sole decision criterion is higher monthly operating profit. Which recommendation follows from the exhibits?"
            options = [
                "Adopt automation under the stated assumptions.",
                "Keep the current process under the stated assumptions.",
                "Adopt because gross variable-cost savings are positive, regardless of the fee.",
                "Keep the current process because any additional fixed fee makes automation unprofitable.",
            ]
            if proposed == baseline:
                answer = "Both plans give equal operating profit under the stated assumptions."
                options[1] = answer
            explanation = f"Current profit is £{baseline:,}; proposed profit is £{proposed:,}. The monthly change is £{proposed - baseline:,}; choose the plan with higher profit, or recognise equality."
        prompt.update(question=text, explanation=explanation)
        if step < 3:
            options, answer = _build_ccat_number_options(rng, answer, wrong)
        else:
            rng.shuffle(options)
        return question(
            self.section_type,
            difficulty,
            seed,
            prompt,
            options,
            answer,
            f"automation_step_{step + 1}",
        )


class ConsultingShortCaseGenerator(LinkedCaseGenerator):
    section_type = "consulting_case"
