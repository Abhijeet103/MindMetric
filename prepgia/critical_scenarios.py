"""Original critical-thinking scenarios, organised by reasoning operation.

No publisher passages are reproduced. Parameters vary the evidence; answer rules
are explicit so editorial judgement can be audited separately from arithmetic.
"""

from prepgia.question_types import _choose_batch_balanced_variant

INFERENCE_OPTIONS = ["True", "Probably true", "Insufficient data", "Probably false", "False"]
FAMILIES = {
    "inference": ["audit_record", "representative_survey", "service_records"],
    "assumptions": ["access", "capacity", "measurement"],
    "deduction": ["conditional", "overlap", "exclusion"],
    "interpretation": ["weighted_rates", "before_after", "scope"],
    "arguments": ["cost", "access", "reliability"],
}
INSTRUCTIONS = {
    "inference": "Treat the passage as true. True/False means established/contradicted by its facts; Probably true/false means the evidence favours/opposes the conclusion without establishing it; Insufficient data means there is no adequate basis either way. Use the stated sampling assumptions; do not invent facts.",
    "assumptions": "Is the proposed assumption taken for granted by the stated reasoning? Use the negation test: if it were false, would the reason given for the recommendation fail? A merely desirable outcome is not enough.",
    "deduction": "Assume all premises are true. Select Follows only if the conclusion must be true in every situation satisfying them. Do not reverse an implication or assume that a group exists unless stated.",
    "interpretation": "Assume the evidence is true. Does the conclusion follow beyond reasonable doubt? Distinguish supported interpretation from claims about unobserved groups, causes or future results.",
    "arguments": "Assume each argument's factual statements are true. A strong argument is important and directly relevant to the precise decision, whether it supports or opposes it. Judge the argument, not your personal opinion.",
}


def build_critical(rng, section, difficulty, seed, firm):
    skill = section.removeprefix("wg_")
    level = {"easy": 1, "medium": 2, "hard": 3}[difficulty]
    family = _choose_batch_balanced_variant(rng, seed, FAMILIES[skill])
    n = rng.randint(12, 48) * 20 * level
    yes = rng.choice([True, False])
    table = None
    if skill == "inference":
        outcome = rng.choice(INFERENCE_OPTIONS)
        if family == "representative_survey":
            share = rng.choice([70, 75, 80, 85])
            passage = f"A {firm} randomly sampled {n} customers from its complete customer list. {share}% preferred evening appointments. The survey had full response, no known bias and a margin of error of 5 percentage points. It did not record willingness to pay. Treat the sample as representative, while recognising sampling uncertainty."
            claims = {
                "True": (
                    "More than half of the surveyed customers preferred evening appointments.",
                    "The sample's stated percentage exceeds 50%; this conclusion refers only to respondents.",
                ),
                "False": (
                    "Most surveyed customers did not prefer evening appointments.",
                    "This contradicts the reported majority among respondents.",
                ),
                "Probably true": (
                    "A majority of all customers prefer evening appointments.",
                    "The representative sample is well above 50%, even allowing the stated margin. It supports a population majority without proving it.",
                ),
                "Probably false": (
                    "A majority of all customers prefer appointments other than evening appointments.",
                    "This runs against a large representative majority; sampling uncertainty prevents an absolute verdict.",
                ),
                "Insufficient data": (
                    "Customers would pay a premium for evening appointments.",
                    "Preference is not willingness to pay; no payment evidence was collected.",
                ),
            }
        elif family == "audit_record":
            missing = rng.randint(2, 9) * level
            passage = f"An independent audit checked all {n} invoices issued by a {firm} in June. Exactly {missing} lacked a required reference; every other invoice contained it. The audit did not examine July invoices."
            claims = {
                "True": (
                    f"Exactly {n - missing} June invoices contained the reference.",
                    "The audit covered the entire June population; subtract the exceptions from the total.",
                ),
                "False": (
                    "Every June invoice contained the reference.",
                    "The audit explicitly identified exceptions.",
                ),
                "Probably true": (
                    "A June invoice selected uniformly at random contained the reference.",
                    f"{n - missing} of {n} have it, a proportion above one half but below one.",
                ),
                "Probably false": (
                    "A June invoice selected uniformly at random lacked the reference.",
                    f"Only {missing} of {n} lack it. This is possible but much less likely than the alternative.",
                ),
                "Insufficient data": (
                    "The proportion missing references fell in July.",
                    "July was not examined; June results cannot determine a later rate.",
                ),
            }
        else:
            ontime = rng.choice([75, 80, 90])
            passage = f"A {firm} recorded all {n} completed repairs last month. {ontime}% finished within two days; the remainder took longer. Completion dates were verified, but no information about customer satisfaction or previous months was collected."
            claims = {
                "True": (
                    f"Exactly {n * (100 - ontime) // 100} repairs took longer than two days.",
                    "Use the complement of the recorded on-time proportion on the complete set.",
                ),
                "False": (
                    "No repair took longer than two days.",
                    "The stated remainder took longer, so the claim is contradicted.",
                ),
                "Probably true": (
                    "A repair selected uniformly from last month's records took no more than two days.",
                    "The verified on-time rate exceeds one half, but includes exceptions.",
                ),
                "Probably false": (
                    "A repair selected uniformly from last month's records took longer than two days.",
                    "The recorded late proportion is below one half, not zero.",
                ),
                "Insufficient data": (
                    "Faster repairs made customers more satisfied than in the previous month.",
                    "Neither satisfaction nor prior-month results were measured; the causal comparison is unsupported.",
                ),
            }
        claim, explanation = claims[outcome]
        answer, options = outcome, INFERENCE_OPTIONS.copy()
    elif skill == "assumptions":
        if family == "access":
            passage = f"A {firm} will close its staffed booking desk and move all bookings to a website. The manager argues that this will preserve the ability of every current customer to book without assistance. No telephone or in-person alternative will remain."
            claim = (
                "Every current customer can use the booking website without assistance."
                if yes
                else "Every current customer will find the website more convenient than the desk."
            )
            explanation = (
                "If even one current customer cannot use the sole remaining channel unassisted, the manager's stated guarantee fails."
                if yes
                else "Equal ability to book does not require greater convenience or preference; negating that preference leaves the stated reason intact."
            )
        elif family == "capacity":
            extra = n * level
            passage = f"A {firm} plans to accept {extra} additional orders next month. It will neither hire staff nor buy equipment. The manager says the additional work can be completed on time because the existing operation has enough unused capacity; no other work will be cancelled."
            claim = (
                "The spare capacity is sufficient at the times when the additional orders must be processed."
                if yes
                else "The additional orders will have a higher profit margin than existing orders."
            )
            explanation = (
                "Capacity available only outside the delivery window cannot justify the promise to complete the extra work on time."
                if yes
                else "Higher margin may make the work attractive, but it is not required by the stated capacity and timing argument."
            )
        else:
            rate = rng.randint(15, 35)
            passage = f"A {firm} reports that complaints fell by {rate}% after a policy change. Management recommends keeping the policy on the ground that the fall reflects improved service. Its comparison uses complaint records from the two periods."
            claim = (
                "The fall is not entirely explained by a change that made complaints less likely to be recorded."
                if yes
                else "No customer complained after the policy change."
            )
            explanation = (
                "If the entire fall came from reduced recording rather than service, the evidence offered for the recommendation would disappear."
                if yes
                else "An improvement can coexist with remaining complaints; a percentage reduction does not require complete elimination."
            )
        if level > 1:
            passage += " A fallback route may be considered later, but it is not funded or available under this recommendation."
        if level == 3:
            passage += " The board requires the manager's stated guarantee, rather than merely an average improvement."
        answer = "Assumption made" if yes else "Assumption not made"
        options = ["Assumption made", "Assumption not made"]
    elif skill == "deduction":
        tag = rng.randint(100, 999)
        if family == "conditional":
            passage = f"For applications in batch {tag}, an application is approved only if it has been reviewed. Every reviewed application has an identity check. Application K has not had an identity check."
            if level > 1:
                passage += " Some identity-checked applications are not reviewed."
            claim = (
                "K is not approved." if yes else "Every identity-checked application is approved."
            )
            explanation = (
                "Approval requires review, which requires an identity check. With no identity check, K cannot be approved."
                if yes
                else "An identity check is necessary, not sufficient, for approval; the converse is not given."
            )
        elif family == "overlap":
            passage = f"In project {tag}, all analysts are trained reviewers. Some analysts are remote workers."
            if level > 1:
                passage += " All remote workers use secure connections."
            claim = (
                (
                    "Some trained reviewers use secure connections."
                    if level > 1
                    else "Some trained reviewers are remote workers."
                )
                if yes
                else "All trained reviewers are analysts."
            )
            explanation = (
                "The stated existence of remote analysts supplies at least one trained reviewer with the required property."
                if yes
                else "All analysts being reviewers does not make all reviewers analysts. The larger group can contain other people."
            )
        else:
            passage = f"In shipment {tag}, no fragile item is sent by ordinary post. All glass items are fragile. Some glass items are insured."
            if level == 3:
                passage += " All insured items receive tracking, but tracking alone does not determine their delivery method."
            claim = (
                "Some insured items are not sent by ordinary post."
                if yes
                else "No insured item is sent by ordinary post."
            )
            explanation = (
                "At least one insured glass item exists; it is fragile and therefore excluded from ordinary post."
                if yes
                else "Only some insured items are established as glass. Other insured items may use ordinary post, so the universal conclusion is not necessary."
            )
        answer, options = ("Follows" if yes else "Does not follow"), ["Follows", "Does not follow"]
    elif skill == "interpretation":
        if family == "weighted_rates":
            # Same improvement in both segments; weights reverse the aggregate.
            scale = rng.randint(2, 15) * level
            rows = [
                ["A", 90 * scale, 81 * scale, 10 * scale, 10 * scale],
                ["B", 10 * scale, 1 * scale, 90 * scale, 18 * scale],
            ]
            table = {
                "caption": "All cases; the two segments are disjoint and exhaustive",
                "columns": [
                    "Segment",
                    "Before: cases",
                    "Before: successes",
                    "After: cases",
                    "After: successes",
                ],
                "rows": rows,
            }
            passage = f"A {firm} reports complete results in the table. Success is defined identically in both periods. The mix of cases between the two segments changed."
            claim = (
                "The combined success rate fell even though each segment's success rate rose."
                if yes
                else "Because each segment improved, the combined success rate must also have risen."
            )
            explanation = "Segment A rises from 90% to 100% and B from 10% to 20%, but the combined rate falls from 82% to 28% as more cases enter B. Weight the rates by case counts."
        elif family == "before_after":
            old = rng.randint(20, 40)
            new = old - rng.randint(3, 10) * (1 if level == 1 else 2)
            passage = f"A {firm} measured average processing time for all completed requests: {old} minutes before a new workflow and {new} minutes after. The mix of request types and staffing also changed. No comparison group was observed."
            claim = (
                "Average time per completed request was lower in the later period."
                if yes
                else "The new workflow alone caused the whole reduction in average processing time."
            )
            explanation = f"The observed average fell by {old - new} minutes, but concurrent changes prevent attribution to the workflow alone. A descriptive comparison is supported; an exclusive causal explanation is not."
        else:
            completed = n - rng.randint(2, 8) * level
            passage = f"A {firm} invited {n} customers to a service trial. Exactly {completed} completed it, and every completer rated the service satisfactory. No ratings were obtained from those who did not complete it."
            claim = (
                "Every recorded rating from trial completers was satisfactory."
                if yes
                else "Every customer invited to the trial found the service satisfactory."
            )
            explanation = "The observation covers completers only. Missing responses cannot be treated as positive ratings, and completers need not represent all invited customers."
        answer, options = ("Follows" if yes else "Does not follow"), ["Follows", "Does not follow"]
    else:
        adverse = rng.choice([True, False])
        amount = rng.randint(10, 40) * 1000 * level
        if family == "cost":
            passage = f"Should a {firm} consolidate two offices if the aim is to reduce total annual costs without reducing service capacity?"
            if yes:
                claim = (
                    f"No. Verified recurring travel costs would rise by £{amount:,} annually, exceeding all rent savings, while capacity would be unchanged."
                    if adverse
                    else f"Yes. After including relocation, travel and rent, total annual costs would fall by £{amount:,}, with unchanged capacity."
                )
                explanation = "The argument directly evaluates total cost and capacity. An evidence-based argument against the proposal can be just as strong as one supporting it."
            else:
                claim = f"Yes. The rent alone would be £{amount:,} lower, although verified additional travel costs would be still larger."
                explanation = "The argument uses a genuine saving but ignores the stated larger offsetting cost, so it does not support the total-cost objective."
        elif family == "access":
            passage = f"Should a {firm} replace every staffed booking desk with online-only booking if the objective is to preserve access for all existing customers?"
            if yes:
                claim = f"No. An audited group of {n} current customers cannot use online booking and would have no remaining way to book."
                explanation = "A documented loss of access for existing customers directly contradicts the all-customer access objective, even if the group is small."
            else:
                claim = f"Yes. A survey found that {n} digitally confident customers prefer online booking; it excluded all other customers."
                explanation = "Preference among selected users does not establish preserved access for every existing customer, especially those excluded from the survey."
        else:
            limit = rng.choice([95, 97, 99])
            passage = f"Should a {firm} adopt supplier R if it must achieve at least {limit}% on-time deliveries at the current volume, without increasing total spending?"
            if yes:
                claim = (
                    f"No. R's contract caps on-time performance below {limit}% at the required volume, with no backup provision."
                    if adverse
                    else f"Yes. A representative trial at the required volume achieved {limit + 1}% on-time delivery and the binding total price is lower than current spending."
                )
                explanation = "The argument addresses a binding reliability threshold and, when recommending adoption, the spending constraint as well."
            else:
                claim = f"Yes. R delivered {n} orders on time in a trial, but the total number of trial orders and the delivery rate are unknown."
                explanation = "An on-time count without its denominator cannot demonstrate the minimum delivery rate, and it says nothing about the spending limit."
        if level > 1:
            passage += " The decision must satisfy the stated constraints for the whole relevant group, not just improve an average."
        if level == 3:
            passage += " Implementation speed is desirable but cannot override those constraints."
        answer, options = ("Strong" if yes else "Weak"), ["Strong", "Weak"]
    label = (
        "Proposed assumption"
        if skill == "assumptions"
        else "Argument"
        if skill == "arguments"
        else "Conclusion"
    )
    prompt = {
        "instruction": INSTRUCTIONS[skill],
        "question": f"{passage}\n\n{label}: {claim}",
        "explanation": explanation,
    }
    if table:
        prompt["data_table"] = table
    return prompt, options, answer, family
