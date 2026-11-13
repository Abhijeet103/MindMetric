"""Original practice content; publisher samples are linked separately."""

import math
import uuid
from prepgia.question_types import (
    BaseQuestionGenerator,
    GeneratedQuestion,
    _build_ccat_number_options,
    _choose_batch_balanced_variant,
)
from prepgia.shl_generators import SHLNumericalGenerator

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
                "generator_version": 1,
            },
        },
        {"answer": answer},
    )


class ConsultingMathGenerator(SHLNumericalGenerator):
    section_type = "consulting_math"

    def generate(self, difficulty, seed, conn=None):
        result = super().generate(difficulty, seed, conn)
        rows = result.payload["prompt"]["data_table"]["rows"]
        result.payload["prompt"]["chart"] = {
            "title": "Current-year regional revenue (£)",
            "labels": [r[0] for r in rows],
            "values": [r[2] * r[3] for r in rows],
        }
        result.payload["prompt"]["instruction"] = (
            "Use the chart and table. A calculator is allowed; round to two decimal places where necessary."
        )
        return result


class CriticalThinkingGenerator(BaseQuestionGenerator):
    def __init__(self, section_type):
        self.section_type = section_type

    def generate(self, difficulty, seed, conn=None):
        rng = self.rng(seed)
        level = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
        firm, objects, code_name = rng.choice(DOMAINS)
        total = rng.randint(8, 30) * 20 * level
        proportion = rng.choice([20, 30, 70, 80])
        flagged = total * proportion // 100
        group = rng.choice(["online", "renewal", "priority", "weekend", "corporate", "local"])
        code = rng.randint(10, 999)
        subtype = self.section_type.removeprefix("wg_")
        prompt = {"instruction": "Use only the passage and the stated decision rule."}
        if subtype == "inference":
            kind = _choose_batch_balanced_variant(
                rng, seed, ["true", "false", "probable", "unknown"]
            )
            passage = f"A {firm} processed exactly {total} {objects}. Exactly {flagged} were {group}; all the others were not {group}. One is selected uniformly at random."
            if level == 3:
                half, flagged_half = total // 2, flagged // 2
                passage = f"A {firm} processed {half} {objects} at office A, of which {flagged_half} were {group}, and {total - half} at office B, of which {flagged - flagged_half} were {group}. These are complete disjoint groups, and all other items were not {group}. One item is selected uniformly at random from the combined group."
            if kind == "true":
                claim, answer = f"Exactly {total - flagged} were not {group}.", "True"
                explanation = f"Subtract the {flagged} {group} items from the total {total}. The exact remainder is {total - flagged}."
            elif kind == "false":
                claim, answer = f"All {total} were {group}.", "False"
                explanation = f"Only {flagged} of {total} were {group}; the passage explicitly rules out the conclusion."
            elif kind == "probable":
                claim = f"The randomly selected item is {group}."
                answer = "Probably true" if proportion > 50 else "Probably false"
                explanation = f"The probability is {proportion}%. That makes the claim {'more' if proportion > 50 else 'less'} likely than not, but not certain."
            else:
                claim, answer = (
                    "The new processing system reduced operating costs.",
                    "Insufficient data",
                )
                explanation = "The passage reports counts, not the costs or effect of a new system."
            options = ["True", "Probably true", "Insufficient data", "Probably false", "False"]
            prompt["instruction"] = (
                "Classify the conclusion: True/False means certain from the passage; Probably true/false means more/less likely than not; Insufficient data means the relevant facts are missing."
            )
        elif subtype == "assumptions":
            budget = rng.randint(10, 40) * 1000
            necessary = rng.choice([True, False])
            passage = f"A {firm} has a fixed £{budget:,} budget and cannot obtain extra funds. Its manager recommends buying a new system immediately using only this budget, without reducing any other spending. No supplier credit or free system is available."
            claim = (
                "The system can be purchased within the available uncommitted budget."
                if necessary
                else "Every employee prefers the new system to the current one."
            )
            answer = "Assumption made" if necessary else "Assumption not made"
            explanation = (
                "If there is not enough available budget, the stated recommendation cannot be implemented under its constraints."
                if necessary
                else "Employee preferences need not be unanimous for the purchase recommendation to be feasible."
            )
            options = ["Assumption made", "Assumption not made"]
            prompt["instruction"] = (
                "Decide whether the proposed assumption is required by the recommendation, rather than merely helpful."
            )
        elif subtype == "deduction":
            labels = list(range(code, code + level + 1))
            rules = [f"Every {group} item receives label {labels[0]}."] + [
                f"Every item with label {a} also receives label {b}."
                for a, b in zip(labels, labels[1:])
            ]
            forward = rng.choice([True, False])
            passage = f"At a {firm}, " + " ".join(rules)
            if forward:
                passage += f" Item K is {group}."
                claim, answer = f"K receives label {labels[-1]}.", "Follows"
                explanation = "Apply each inclusion rule in order; the final label is required."
            else:
                passage += f" Item K has label {labels[-1]}."
                claim, answer = f"K must be {group}.", "Does not follow"
                explanation = "The rules do not say that only the initial group receives the labels. Reversing the implication is invalid."
            options = ["Follows", "Does not follow"]
        elif subtype == "interpretation":
            second = rng.randint(8, 30) * 20 * level
            prompt["data_table"] = {
                "caption": "Complete counts of processed items",
                "columns": ["Period", "Processed", "Flagged"],
                "rows": [["A", total, flagged], ["B", second, second * proportion // 100]],
            }
            valid = rng.choice([True, False])
            passage = f"The table contains complete data for the {firm} in two periods. Flagged items were counted consistently in both periods."
            claim = (
                "The proportion flagged was equal in the two periods."
                if valid
                else "The equal proportions prove the same proportion will occur in every future period."
            )
            answer = "Follows" if valid else "Does not follow"
            explanation = (
                f"Both proportions are exactly {proportion}%."
                if valid
                else "Two past observations do not establish that every future period must have the same proportion."
            )
            options = ["Follows", "Does not follow"]
        else:
            good = rng.choice([True, False])
            savings = rng.randint(2, 15) * 1000
            passage = f"Question: Should a {firm} replace its manual {code_name} process if the aim is to reduce annual operating costs without lowering accuracy?"
            claim = (
                f"Yes. A representative controlled pilot found £{savings:,} annual net savings after all implementation costs, with unchanged accuracy."
                if good
                else "Yes. The new labels use the same font size as the current labels, regardless of any cost or accuracy effects."
            )
            answer = "Strong" if good else "Weak"
            explanation = (
                "The argument addresses both stated decision criteria with relevant evidence about net savings and accuracy."
                if good
                else "Matching the font size does not establish any benefit against the stated cost and accuracy criteria."
            )
            options = ["Strong", "Weak"]
            prompt["instruction"] = (
                "Assume the argument's factual statements are true. Judge its importance and relevance to the stated question."
            )
        if level == 3 and subtype in {"assumptions", "arguments"}:
            passage += f" The organisation also processed {total} {objects} last month; that volume is not a purchase or cost-reduction criterion."
        prompt.update(
            question=f"{passage}\n\n{'Proposed assumption' if subtype == 'assumptions' else 'Argument' if subtype == 'arguments' else 'Conclusion'}: {claim}",
            explanation=explanation,
        )
        rng.shuffle(options)
        return question(self.section_type, difficulty, seed, prompt, options, answer, subtype)


class ConsultingEvidenceGenerator(BaseQuestionGenerator):
    section_type = "consulting_evidence"

    def generate(self, difficulty, seed, conn=None):
        rng = self.rng(seed)
        level = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty, 2)
        firm, objects, _ = rng.choice(DOMAINS)
        before = rng.randint(20, 60)
        after = before + rng.randint(5, 25)
        sample = rng.randint(5, 20) * 20 * level
        family = _choose_batch_balanced_variant(rng, seed, ["causality", "sampling", "decision"])
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
            wrong = [volume * (price - variable), volume * price - fixed, baseline + fixed]
            explanation = f"Profit = {volume} × ({price} − {variable}) − {fixed} = £{baseline:,}."
        elif step == 1:
            answer = proposed
            text = "What would monthly operating profit be after automation?"
            wrong = [baseline + volume * saving, baseline - fee, proposed + fee]
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
                "Adopt because the proposal increases the price per order.",
                "Adopt because the current fixed cost disappears entirely.",
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
            self.section_type, difficulty, seed, prompt, options, answer, f"case_step_{step + 1}"
        )


class ConsultingShortCaseGenerator(LinkedCaseGenerator):
    section_type = "consulting_case"
