"""Original MindMetric practice. No employer or examination question bank is reproduced."""

from prepgia.question_types import BaseQuestionGenerator, _build_ccat_number_options, _choose_batch_balanced_variant
from prepgia.consulting_generators import question

LEVELS = {"easy": 1, "medium": 2, "hard": 3}
TEAMS = ["Harbour Services", "Cedar Support", "Maple Operations", "Beacon Projects", "Willow Accounts", "Orchard Logistics", "Aster Studio", "Ridge Learning"]


class SituationalJudgementGenerator(BaseQuestionGenerator):
    section_type = "sjt_workplace"

    def generate(self, difficulty, seed, conn=None):
        rng = self.rng(seed)
        level = LEVELS[difficulty]
        team = rng.choice(TEAMS)
        minutes = rng.randint(2, 12) * 5
        family = _choose_batch_balanced_variant(rng, seed, ["privacy", "capacity", "error", "customer", "conflict", "accessibility"])
        # The stated rubric defines the best action; this is skills practice, not a personality score.
        cases = {
            "privacy": (
                f"At {team}, a colleague asks you to send a customer's identity document to their personal email because the secure portal is slow. The customer needs an update within {minutes} minutes.",
                "Use approved channels for personal data. If a tool fails, contact the authorised support team and give the customer a realistic update.",
                "Use the approved support route to restore secure access and update the customer without sending personal data elsewhere.",
                ["Send it to the personal address, then ask the colleague to delete it.", "Send a password-protected file to the personal address without approval.", "Ignore the request and leave the customer without an update."],
                "The deadline does not override the data-handling rule. Restore an approved route and communicate the delay; a password alone does not authorise a personal mailbox."),
            "capacity": (
                f"At {team}, you have {minutes} minutes left today. Two managers each give you a task that takes {minutes} minutes and both want it today. Neither knows about the other request.",
                "Make capacity conflicts visible early. Confirm business impact and agree priorities with the people responsible; do not promise impossible delivery.",
                "Explain the conflict to both managers, confirm the impact of each task and agree the order and revised deadline.",
                ["Promise both tasks today and hope one is cancelled.", "Choose the manager you like more without discussing the conflict.", "Wait until the end of the day to report that one task is unfinished."],
                "Two tasks need twice the available time. Early, explicit prioritisation allows the responsible managers to make an informed trade-off."),
            "error": (
                f"At {team}, you find an incorrect cost figure in a report due to be sent to a client in {minutes} minutes. You can identify the affected calculation, but you cannot approve a replacement report yourself.",
                "Prevent known inaccurate information from being released. Tell the accountable owner, identify the impact and obtain approval for corrections.",
                "Alert the report owner immediately, identify the affected calculation and request a hold while the correction is checked and approved.",
                ["Send the report because the deadline matters more than accuracy.", "Change the report and send it yourself without the required approval.", "Keep quiet because somebody else entered the figure."],
                "The owner needs enough information to stop an inaccurate release and approve a checked correction. Neither concealment nor bypassing approval meets the rule."),
            "customer": (
                f"A customer of {team} says a delayed order has disrupted their plans. Your system has no confirmed delivery time. The next verified update is expected in {minutes} minutes.",
                "Acknowledge the impact, check verified information and agree a specific follow-up. Never invent delivery promises or compensation authority.",
                f"Acknowledge the disruption, explain what is confirmed and commit to an update in {minutes} minutes while checking the order.",
                ["Promise delivery today even though you cannot verify it.", "Tell the customer delays are normal and close the conversation.", "Offer a refund you are not authorised to approve."],
                "A useful response combines empathy, accurate information and a clear next action. Unsupported promises can create another failure."),
            "conflict": (
                f"At {team}, a colleague disagrees with your proposed workflow during a meeting. You have {minutes} minutes before the decision is due and the disagreement concerns the evidence, not misconduct.",
                "Resolve evidence-based disagreement respectfully. Clarify the concern, compare relevant evidence and involve the decision owner if the issue remains unresolved.",
                "Ask which evidence concerns them, compare both proposals against the objective and take any unresolved trade-off to the decision owner.",
                ["Dismiss their objection because you presented first.", "Agree immediately without checking whether their alternative meets the objective.", "Complain publicly about the colleague instead of discussing the evidence."],
                "The rubric rewards constructive evaluation, not automatic agreement or winning the argument. Escalate the decision rather than attacking the person."),
            "accessibility": (
                f"At {team}, a participant says the only registration form is inaccessible to their screen reader. Registration closes in {minutes} minutes and an approved assisted-registration route exists.",
                "Use approved accessible alternatives, preserve consent and confidentiality, and report access barriers for repair.",
                "Offer the approved assisted-registration route with their consent and report the form barrier to its owner.",
                ["Tell them to ask a stranger to complete the form with their private information.", "Say everyone must use the same form without exception.", "Register them without asking for their consent."],
                "An approved alternative enables participation now, while reporting the defect supports future access. Consent and confidentiality still apply."),
        }
        situation, policy, answer, wrong, explanation = cases[family]
        if level >= 2:
            situation += " A senior colleague suggests taking a shortcut to protect today's service target; they cannot waive the policy."
            wrong[1] = "Follow the senior colleague's shortcut and document the policy exception afterwards."
        if level == 3:
            situation += " You must also keep a factual record of the agreed action, without disclosing unnecessary personal information."
            answer += " Record the decision and agreed follow-up in the approved system."
            wrong[2] = "Apply the relevant rule but share the full incident and personal details in an unrestricted team chat."
            explanation += " Seniority does not create waiver authority, and an audit trail should contain only necessary information."
        options = [answer, *wrong]
        rng.shuffle(options)
        prompt = {"scenario": situation, "principles": policy, "instruction": f"Workplace principles: {policy}\n\nScenario: {situation}", "question": "Which is the most effective response under the stated principles?", "explanation": explanation}
        return question(self.section_type, difficulty, seed, prompt, options, answer, family)


class WorkSimulationGenerator(BaseQuestionGenerator):
    section_type = "work_simulation"

    def generate(self, difficulty, seed, conn=None):
        prefix, _, raw_index = seed.rpartition(":")
        index = int(raw_index) if raw_index.isdigit() else 0
        case_seed = f"{prefix}:inbox:{index // 4}"
        rng = self.rng(case_seed)
        level = LEVELS[difficulty]
        team = rng.choice(TEAMS)
        case_ref = rng.randint(1000, 9999)
        priority_time = rng.randint(2, 6) * 5
        regular_time = priority_time + rng.randint(2, 5) * 5
        available = rng.randint(3, 8) * 20
        demand = available + rng.randint(2, 6) * 10
        unit = rng.randint(2, 8) * level
        reserve = rng.randint(2, 5) * 5 if level >= 2 else 0
        per_pack = 5 if level == 3 else 1
        step = index % 4
        usable = available - reserve
        shortage = demand - usable
        packs = (shortage + per_pack - 1) // per_pack
        cost = packs * per_pack * unit
        case = {"id": case_seed, "title": f"{team}: morning inbox #{case_ref}", "background": f"You coordinate today's orders. Policy: resolve a possible data exposure before routine requests, using the restricted incident channel. Escalate any dispatch shortfall to the operations owner before promising delivery. Only the owner can approve purchases; never exceed approved authority. Quotes are estimates until approved. Purchase units in packs of {per_pack}; a whole pack costs £{per_pack * unit}. No tax or delivery fees apply.", "question_index": step + 1, "question_total": 4}
        table = {"caption": "Inbox and dispatch snapshot", "columns": ["Item", "Information"], "rows": [
            ["A — possible data exposure", f"Report due in {priority_time} minutes; use restricted incident channel"],
            ["B — dispatch shortfall", f"Decision due in {regular_time} minutes; approval owner available"],
            ["C — routine brochure update", "Due tomorrow; no immediate service or safety impact"],
            ["Physical units in stock", str(available)], ["Units reserved for another confirmed order", str(reserve)],
            ["Units needed for today's dispatch", str(demand)], ["Supplier estimate per unit", f"£{unit}"],
        ]}
        if step == 0:
            query = "Which inbox item should you handle first under the stated policy?"
            answer, wrong = "A — report the possible data exposure through the restricted incident channel.", ["B — purchase stock immediately without approval.", "C — update the brochure before dealing with incidents.", "A — forward the full customer data to every team member."]
            explanation = "Policy explicitly places a possible data exposure ahead of routine requests. Report it through the restricted route; do not broaden the exposure."
        elif step == 1:
            query = "How many additional units are required for today's dispatch after respecting the existing reservation?"
            answer, wrong = shortage, [demand - available, available, demand + reserve]
            explanation = f"Usable stock = {available} − {reserve} = {usable}. Shortfall = {demand} − {usable} = {shortage} units."
        elif step == 2:
            query = "What supplier cost (£) should you submit for approval to cover that shortfall, respecting pack sizes?"
            answer, wrong = cost, [shortage * unit, demand * unit, cost + per_pack * unit]
            explanation = f"Shortfall is {shortage} units. Buy {packs} whole pack(s) of {per_pack} units: {packs} × {per_pack} × £{unit} = £{cost}. This is a request for approval, not authority to purchase."
        else:
            query = "Which email reply to the dispatch requester is best supported by the evidence and policy?"
            answer = f"We need {shortage} additional units. I have requested approval for {packs} pack(s), estimated at £{cost}, and will confirm delivery after approval and supplier confirmation."
            wrong = ["All units are available and delivery is guaranteed today.", "I have purchased the stock without approval because the request is urgent.", "The reserved units can be used without checking the existing commitment."]
            explanation = "The reply states the verified shortfall, distinguishes an estimate from approval and avoids an unsupported delivery promise."
        item_rng = self.rng(seed)
        if isinstance(answer, int):
            options, answer = _build_ccat_number_options(item_rng, answer, wrong)
        else:
            options = [answer, *wrong]
            item_rng.shuffle(options)
        prompt = {"instruction": "Use the shared inbox, policy and figures. A calculator is allowed. Each question is scored independently.", "case_study": case, "data_table": table, "question": query, "explanation": explanation}
        return question(self.section_type, difficulty, seed, prompt, options, answer, f"inbox_step_{step + 1}")


class VerbalPassageGenerator(BaseQuestionGenerator):
    section_type = "verbal_passages"

    def generate(self, difficulty, seed, conn=None):
        rng = self.rng(seed)
        level = LEVELS[difficulty]
        team = rng.choice(TEAMS)
        total = rng.randint(8, 40) * 10
        first = total // 2
        day = rng.choice(["Monday", "Tuesday", "Wednesday", "Thursday"])
        family = _choose_batch_balanced_variant(rng, seed, ["allocation", "policy", "sample", "change", "ordering", "conditional"])
        target = rng.choice(["True", "False", "Cannot say"])
        if family == "allocation":
            passage = f"{team} received {total} requests. Exactly {first} were assigned to Team A; every remaining request was assigned to Team B. No request was assigned to both teams."
            claims = {"True": f"Team B received {total-first} requests.", "False": "At least one request was assigned to both teams.", "Cannot say": "Team A completed its requests faster than Team B."}
            reason = {"True": "Subtract Team A's allocation from the total.", "False": "The passage explicitly states there were no shared assignments.", "Cannot say": "Allocation counts do not establish completion times."}
        elif family == "policy":
            passage = f"At {team}, every approved supplier must have a current security review. Having a current review does not by itself guarantee approval. Supplier R has been approved; Supplier S has a current review."
            claims = {"True": "Supplier R has a current security review.", "False": "An approved supplier may have no current security review.", "Cannot say": "Supplier S has been approved."}
            reason = {"True": "The necessary review condition applies to every approved supplier, including R.", "False": "This contradicts the universal requirement.", "Cannot say": "A necessary condition is not sufficient for approval."}
        elif family == "sample":
            passage = f"{team} invited {total} customers to a voluntary survey. Exactly {first} replied, and all respondents favoured the proposed opening time. No information was collected about non-respondents' preferences."
            claims = {"True": "Every customer who replied favoured the proposal.", "False": "No respondent favoured the proposal.", "Cannot say": "Every invited customer favoured the proposal."}
            reason = {"True": "This restates the result for respondents only.", "False": "It directly contradicts the reported response.", "Cannot say": "The preferences of non-respondents are unknown."}
        elif family == "change":
            passage = f"{team} processed {total} orders in April and {total + first} in May. Its staffing, prices and working hours were not reported."
            claims = {"True": "More orders were processed in May than in April.", "False": "Fewer orders were processed in May than in April.", "Cannot say": "The increase in orders was caused by hiring more staff."}
            reason = {"True": "Compare the two stated totals.", "False": "May's stated total exceeds April's.", "Cannot say": "A change in output does not identify its cause; staffing is not reported."}
        elif family == "ordering":
            passage = f"At {team}, the inspection occurred on {day}. Packing began after inspection ended. Dispatch began only after packing ended. None of these activities overlapped."
            claims = {"True": "The inspection ended before dispatch began.", "False": "Dispatch began before the inspection ended.", "Cannot say": "Dispatch began on the same day as the inspection."}
            reason = {"True": "The inspection precedes packing, which precedes dispatch.", "False": "This reverses the stated sequence.", "Cannot say": "The order is given, but not the dates of packing or dispatch."}
        else:
            passage = f"At {team}, a request is automatically escalated if it is both overdue and unresolved. Request P is overdue and unresolved. Request Q was escalated, but the reason is not stated; manual escalation is also possible."
            claims = {"True": "Request P meets the automatic escalation rule.", "False": "Request P fails the automatic escalation rule.", "Cannot say": "Request Q is overdue."}
            reason = {"True": "P satisfies both necessary parts of this stated trigger.", "False": "The passage says P meets both trigger conditions.", "Cannot say": "An escalated request may have been escalated manually for another reason."}
        if level >= 2:
            passage += f" A separate pilot handled {rng.randint(2, 9)*10} archived cases; its records are excluded from the figures and rules above."
        if level == 3:
            # Add a genuine conditional scope distinction, rather than only longer wording.
            passage += " From next month a revised policy may apply, but its terms have not been agreed and no change applies to the period described."
            if rng.choice([True, False]):
                claims[target] = {"True": "The proposed policy change is not in force for the period described.", "False": "The revised policy is already in force for the period described.", "Cannot say": "Next month's revised policy will retain every current rule."}[target]
                reason[target] = {"True": "The passage explicitly limits the change to a possible future period.", "False": "It explicitly says no change applies to the period described.", "Cannot say": "The future policy's terms have not been agreed."}[target]
        prompt = {"passage": passage, "instruction": "Use only this passage. True means supported, False means contradicted, and Cannot say means insufficient information.\n\n" + passage, "question": claims[target], "explanation": reason[target]}
        return question(self.section_type, difficulty, seed, prompt, ["True", "False", "Cannot say"], target, family)


class ArithmeticGenerator(BaseQuestionGenerator):
    section_type = "aptitude_arithmetic"

    def generate(self, difficulty, seed, conn=None):
        rng = self.rng(seed)
        level = LEVELS[difficulty]
        family = _choose_batch_balanced_variant(rng, seed, ["percentage", "ratio", "average", "rate", "profit", "series"])
        a, b = rng.randint(3, 18), rng.randint(2, 9)
        if family == "percentage":
            base, rate = a * 100, b * 5
            if level == 1:
                query = f"What is {rate}% of {base}?"
                answer = base * rate / 100
                explanation = f"Multiply {base} by {rate}/100 to get {answer:g}."
            else:
                second = rng.randint(2, 8) * 5
                query = f"A price of £{base} rises by {rate}% and then falls by {second}%. What is the final price (£)?"
                answer = base * (1 + rate/100) * (1-second/100)
                if level == 3:
                    query += " Then apply a further 10% discount."
                    answer *= .9
                explanation = f"Apply each percentage to the updated base: {base} × {1+rate/100:g} × {1-second/100:g}" + (" × 0.9" if level == 3 else "") + f" = {answer:.2f}."
        elif family == "ratio":
            total = (a + b) * rng.randint(5, 25)
            query = f"A fund of £{total} is split between A and B in the ratio {a}:{b}. How much (£) does A receive?"
            answer = total * a / (a+b)
            if level >= 2:
                query += f" A then transfers {20 if level == 2 else 35}% of its share to B. Give A's remaining amount."
                answer *= .8 if level == 2 else .65
            explanation = f"A starts with {a}/({a}+{b}) of £{total}." + (" Multiply by the retained fraction after the transfer." if level >= 2 else "") + f" The result is £{answer:.2f}."
        elif family == "average":
            values = [rng.randint(5, 45) for _ in range(level + 2)]
            if level < 3:
                query = f"What is the arithmetic mean of {', '.join(map(str, values))}? Round to two decimal places."
                answer = sum(values)/len(values)
                explanation = f"Sum the values ({sum(values)}) and divide by their count ({len(values)}): {answer:.2f}."
            else:
                target = rng.randint(20, 40)
                query = f"Five values are {', '.join(map(str, values))}. What sixth value gives an overall mean of {target}?"
                answer = 6 * target - sum(values)
                explanation = f"Required total = 6 × {target}. Subtract the existing total {sum(values)} to get {answer:g}."
        elif family == "rate":
            workers, hours = b, a
            volume = workers * hours * rng.randint(2, 8)
            if level == 1:
                query = f"{workers} workers produce {volume} items in {hours} hours. At equal constant rates, how many items does one worker produce per hour?"
                answer = volume / (workers*hours)
            else:
                new_workers = workers + level
                query = f"{workers} workers produce {volume} items in {hours} hours. At the same equal constant rates, how long (hours) would {new_workers} workers take to produce {volume * level} items?"
                answer = hours * workers * level / new_workers
            explanation = f"The rate is {volume}/({workers} × {hours}) = {volume/(workers*hours):g} items per worker-hour. Divide the requested output by the total new rate." + f" Answer: {answer:.2f}."
        elif family == "profit":
            cost, markup = a * 20, b * 5
            discount = (rng.randint(1, 4) * 5) if level >= 2 else 0
            sale = cost * (1+markup/100) * (1-discount/100)
            query = f"An item costs £{cost} and is marked up by {markup}%." + (f" A {discount}% discount is then applied to the marked price." if discount else "")
            if level == 3:
                query += " What is profit as a percentage of the original cost? Round to two decimal places."
                answer = 100*(sale-cost)/cost
            else:
                query += " What is the profit (£)?"
                answer = sale-cost
            explanation = f"Selling price = {cost} × {1+markup/100:g} × {1-discount/100:g} = £{sale:.2f}. Subtract original cost" + (" and divide by original cost, then multiply by 100" if level == 3 else "") + f": {answer:.2f}."
        else:
            start, step = a, b
            if level == 1:
                values = [start + step*i for i in range(5)]
                answer = start + step*5
                explanation = f"Add {step} each time."
            elif level == 2:
                values = [start * b**i for i in range(5)]
                answer = start * b**5
                explanation = f"Multiply by {b} each time."
            else:
                values = [start]
                for i in range(1, 5):
                    values.append(values[-1] + step*i)
                answer = values[-1] + step*5
                explanation = f"The gaps increase by {step}: {step}, {2*step}, {3*step}, {4*step}, then {5*step}."
            query = f"What number comes next: {', '.join(map(str, values))}, ?"
        options, answer = _build_ccat_number_options(rng, answer, [answer + b, answer - a, answer * 1.1, answer/2])
        return question(self.section_type, difficulty, seed, {"instruction": "Solve the arithmetic problem. Round money and non-integer results to two decimal places.", "question": query, "explanation": explanation}, options, answer, family)


class VerbalLogicGenerator(BaseQuestionGenerator):
    section_type = "aptitude_verbal"

    def generate(self, difficulty, seed, conn=None):
        rng = self.rng(seed)
        level = LEVELS[difficulty]
        names = rng.sample(["Amira", "Ben", "Chloe", "Dev", "Elena", "Farah", "Gareth", "Hana", "Ivo", "Jules"], level+2)
        family = _choose_batch_balanced_variant(rng, seed, ["ordering", "conditional", "coding"])
        if family == "conditional":
            groups = rng.sample(["editors", "reviewers", "planners", "designers", "coordinators", "analysts", "auditors", "trainers"], level + 2)
            rules = [f"Every {groups[i][:-1]} is a member of the {groups[i+1]} group." for i in range(len(groups)-1)]
            person = names[0]
            rules.append(f"{person} is a member of the {groups[0]} group.")
            answer = f"{person} is a member of the {groups[-1]} group."
            options = [answer, f"Every {groups[-1][:-1]} must be a member of the {groups[0]} group.", f"No {groups[0][:-1]} can be a member of the {groups[-1]} group.", f"All {groups[-1]} are the same person as {person}."]
            rng.shuffle(options)
            return question(self.section_type, difficulty, seed,
                {"statements": rules, "instruction": "Use only these rules.\n\n" + " ".join(rules), "question": "Which conclusion must follow?", "explanation": f"Follow the inclusion chain from {groups[0]} to {groups[-1]}. It applies to {person}. Reversing an inclusion is not justified."}, options, answer, family)
        if family == "coding":
            import string
            shift = rng.randint(1, 5) * (1 if level == 1 else -1)
            word = rng.choice(["PLANT", "BRICK", "WATER", "CLOUD", "FRAME", "LIGHT", "STONE", "TRACK", "WHEEL", "NORTH"])
            def encode(text):
                if level == 3:
                    text = text[::-1]
                return "".join(string.ascii_uppercase[(ord(c)-65+shift) % 26] for c in text)
            answer = encode(word)
            direction = "forward" if shift > 0 else "backward"
            rule = ("Reverse the word, then move" if level == 3 else "Move") + f" each letter {abs(shift)} place(s) {direction} in the alphabet, wrapping between A and Z."
            options = [answer, word, encode(word)[::-1], "".join(string.ascii_uppercase[(ord(c)-65-shift) % 26] for c in word)]
            options = list(dict.fromkeys(options))
            for offset in range(1, 5):
                extra = "".join(string.ascii_uppercase[(ord(c)-65+offset) % 26] for c in answer)
                if extra not in options and len(options) < 4:
                    options.append(extra)
            rng.shuffle(options)
            return question(self.section_type, difficulty, seed,
                {"instruction": rule, "question": f"How is {word} encoded?", "explanation": f"Apply the stated rule to every letter: {word} becomes {answer}."}, options, answer, family)
        attribute = rng.choice(["taller than", "older than", "faster than"])
        statements = [f"{names[i]} is {attribute} {names[i+1]}." for i in range(len(names)-1)]
        rng.shuffle(statements)
        reverse = rng.choice([True, False])
        order = names[::-1] if reverse else names
        rank = rng.randint(1, len(names))
        label = {"taller than": "shortest" if reverse else "tallest", "older than": "youngest" if reverse else "oldest", "faster than": "slowest" if reverse else "fastest"}[attribute]
        answer = order[rank-1]
        options = list(names)
        rng.shuffle(options)
        prompt = {"statements": statements, "instruction": "Use only these relationships.\n\n" + " ".join(statements), "question": f"Who is number {rank} when the people are ordered from {label} first?", "explanation": f"The required order is {' → '.join(order)}. Position {rank} is {answer}."}
        return question(self.section_type, difficulty, seed, prompt, options, answer, "ordering")
