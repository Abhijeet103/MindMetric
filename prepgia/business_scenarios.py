"""Original business maths and multi-step case exercises with explicit units."""

import math
from prepgia.question_types import _choose_batch_balanced_variant

MATH_FAMILIES = [
    "market_funnel",
    "break_even",
    "price_volume",
    "capacity_yield",
    "weighted_margin",
    "currency",
    "compound_growth",
    "opportunity_cost",
]
CASE_FAMILIES = ["automation", "market_entry", "capacity"]


def business_math(rng, difficulty, seed):
    level = {"easy": 1, "medium": 2, "hard": 3}[difficulty]
    family = _choose_batch_balanced_variant(rng, seed, MATH_FAMILIES)
    units = rng.randint(10, 60) * 100 * level
    price = rng.randint(12, 30) * 5
    cost = price - rng.randint(3, 10) * 2
    fixed = rng.randint(5, 20) * 1000
    prompt = {
        "instruction": "Use the exhibits and stated assumptions. A calculator is allowed. Round only the final answer to two decimal places unless whole units are requested."
    }
    if family == "market_funnel":
        eligible, adoption = rng.choice([20, 40, 60]), rng.choice([10, 20, 30])
        frequency = 1 if level == 1 else rng.randint(2, 5)
        rows = [
            ["Population (people)", units * 100],
            ["Eligible (%)", eligible],
            ["Buying among eligible (%)", adoption],
            ["Purchases per buyer annually", frequency],
            ["Revenue per purchase (£)", price],
        ]
        answer = units * 100 * eligible / 100 * adoption / 100 * frequency * price
        query = "What annual sales revenue (£) is implied by this market-sizing funnel? Assume the buying rate applies only to eligible people."
        wrong = [
            answer * 100 / eligible,
            answer * 100 / adoption,
            answer / frequency if frequency > 1 else answer / price,
        ]
        explanation = f"Eligible population = {units * eligible:,}; buyers = {units * eligible * adoption / 100:g}. Multiply buyers × {frequency} purchases × £{price}: £{answer:,.2f} annually. Apply conditional percentages sequentially, not by addition."
    elif family == "break_even":
        fee = 0 if level == 1 else rng.randint(1, 4)
        rows = [
            ["Price per unit (£)", price],
            ["Variable cost per unit (£)", cost],
            ["Transaction fee per unit (£)", fee],
            ["Annual fixed cost (£)", fixed],
        ]
        answer = math.ceil(fixed / (price - cost - fee))
        query = "What is the minimum whole number of units that must be sold annually to cover all listed costs?"
        wrong = [math.floor(fixed / (price - cost - fee)), fixed / price, fixed / (price - cost)]
        explanation = f"Unit contribution after all per-unit costs = {price} − {cost} − {fee} = £{price - cost - fee}. Divide £{fixed:,} by this amount, then round up to {answer:,} whole units. Revenue alone does not pay variable costs."
    elif family == "price_volume":
        rise, fall = rng.choice([5, 10, 15, 20]), rng.choice([5, 10, 20, 25])
        rows = [
            ["Current monthly units", units],
            ["Current price per unit (£)", price],
            ["Variable cost per unit (£)", cost],
            ["Proposed price increase (%)", rise],
            ["Expected volume reduction (%)", fall],
        ]
        if level == 1:
            answer = 100 * ((1 + rise / 100) * (1 - fall / 100) - 1)
            query = "What is the percentage change in monthly revenue after both changes? Use a negative number for a decline."
            wrong = [rise - fall, abs(answer), 100 + answer]
            explanation = f"New revenue / old revenue = {1 + rise / 100:g} × {1 - fall / 100:g}. Subtract 1, then multiply by 100: {answer:.2f}%. Percentage changes have different bases."
        else:
            answer = units * (1 - fall / 100) * (price * (1 + rise / 100) - cost) - units * (
                price - cost
            )
            query = "What is the change in monthly contribution (£) after the price and volume changes? Variable cost per unit stays unchanged; fixed costs cancel."
            wrong = [
                units * price * ((1 + rise / 100) * (1 - fall / 100) - 1),
                units * price * rise / 100,
                -answer,
            ]
            explanation = f"Compare new units × new unit contribution with the original contribution. {units * (1 - fall / 100):g} × ({price * (1 + rise / 100):g} − {cost}) − {units} × ({price} − {cost}) = £{answer:,.2f}. A revenue change is not the same as a contribution change."
    elif family == "capacity_yield":
        days, hours = rng.randint(18, 25), rng.randint(6, 9)
        yield_pct = 100 if level == 1 else rng.choice([80, 90, 95])
        rate = rng.randint(20, 70)
        rows = [
            ["Operating days per month", days],
            ["Hours per day", hours],
            ["Units processed per hour", rate],
            ["Saleable yield (%)", yield_pct],
            ["Demand (saleable units/month)", units],
        ]
        capacity = math.floor(days * hours * rate * yield_pct / 100)
        answer = min(capacity, units)
        query = "What is the maximum number of saleable units that can be sold this month? There is no opening inventory; sales cannot exceed demand or saleable capacity."
        wrong = [days * hours * rate, max(capacity, units), capacity * 100 / yield_pct]
        explanation = f"Gross capacity = {days} × {hours} × {rate}; saleable capacity = floor(gross × {yield_pct}%) = {capacity:,}. Sales are the smaller of this and demand {units:,}: {answer:,}."
    elif family == "weighted_margin":
        other_units = rng.randint(5, 30) * 100 * level
        other_price = price + rng.randint(1, 5) * 10
        other_cost = other_price - rng.randint(2, 8) * 5
        rows = [["Standard", units, price, cost], ["Premium", other_units, other_price, other_cost]]
        revenue = units * price + other_units * other_price
        contribution = units * (price - cost) + other_units * (other_price - other_cost)
        answer = contribution / revenue * 100
        query = "What is the combined contribution margin as a percentage of total revenue?"
        wrong = [
            ((price - cost) / price + (other_price - other_cost) / other_price) * 50,
            contribution / (units + other_units),
            contribution / (revenue - contribution) * 100,
        ]
        explanation = f"Total contribution = £{contribution:,}; total revenue = £{revenue:,}. Margin = contribution / revenue × 100 = {answer:.2f}%. Weight by revenue, not by averaging the two percentages."
    elif family == "currency":
        fx = rng.choice([1.10, 1.20, 1.25, 1.40])
        duty = 0 if level == 1 else rng.choice([5, 10, 15])
        freight = rng.randint(2, 9) * 100
        rows = [
            ["Invoice (EUR)", units],
            ["Exchange rate: EUR per GBP", fx],
            ["Import duty (% of converted invoice only)", duty],
            ["Freight, not subject to duty (GBP)", freight],
        ]
        answer = units / fx * (1 + duty / 100) + freight
        query = "What is the total landed cost in GBP? Apply duty only to the converted invoice, then add freight."
        wrong = [
            units * fx * (1 + duty / 100) + freight,
            (units / fx + freight) * (1 + duty / 100),
            units / fx + freight,
        ]
        explanation = f"EUR per GBP means divide euros by {fx:g}. Cost = ({units}/{fx:g}) × {1 + duty / 100:g} + {freight} = £{answer:,.2f}. Freight is outside the duty base."
    elif family == "compound_growth":
        first, second = rng.choice([5, 10, 15, 20]), rng.choice([-20, -10, 5, 15])
        rows = [
            ["Initial annual revenue (£)", units * price],
            ["Year 1 change (%)", first],
            ["Year 2 change (%)", second],
        ]
        answer = units * price * (1 + first / 100) * (1 + second / 100)
        query = "What is annual revenue (£) at the end of year 2? Each change applies to the preceding year's revenue."
        wrong = [
            units * price * (1 + (first + second) / 100),
            units * price * (1 + second / 100),
            units * price * (1 + first / 100),
        ]
        explanation = f"£{units * price:,} × {1 + first / 100:g} × {1 + second / 100:g} = £{answer:,.2f}. Apply successive changes multiplicatively."
    else:
        hours_a, hours_b = rng.randint(1, 3), rng.randint(4, 7)
        contribution_a = rng.randint(8, 18) * hours_a
        contribution_b = rng.randint(20, 30) * hours_b
        available = units * hours_a
        rows = [["A", contribution_a, hours_a], ["B", contribution_b, hours_b]]
        answer = contribution_b / hours_b - contribution_a / hours_a
        query = f"There are {available:,} scarce machine-hours and unlimited demand for both products. How much more contribution (£) is earned per scarce hour by choosing B instead of A? Ignore changeover costs."
        wrong = [
            contribution_b - contribution_a,
            contribution_a / hours_a - contribution_b / hours_b,
            contribution_b / hours_b,
        ]
        explanation = f"A yields £{contribution_a / hours_a:g}/hour and B £{contribution_b / hours_b:g}/hour. The advantage is £{answer:g}/hour. Contribution per unit ignores scarce time."
    columns = ["Measure", "Value"]
    if family == "weighted_margin":
        columns = ["Product", "Units", "Price (£/unit)", "Variable cost (£/unit)"]
    elif family == "opportunity_cost":
        columns = ["Product", "Contribution (£/unit)", "Machine-hours/unit"]
    prompt.update(
        question=query,
        explanation=explanation,
        data_table={
            "caption": "Business planning assumptions; no unlisted costs",
            "columns": columns,
            "rows": rows,
        },
    )
    # The exhibit is used directly by the question, rather than a decorative copy
    # of an unrelated sales chart. Tables remain available for exact values.
    if family in {"weighted_margin", "opportunity_cost"}:
        prompt["chart"] = {
            "title": "Revenue by product (£)"
            if family == "weighted_margin"
            else "Contribution per scarce machine-hour (£)",
            "labels": [r[0] for r in rows],
            "values": [r[1] * r[2] for r in rows]
            if family == "weighted_margin"
            else [r[1] / r[2] for r in rows],
        }
    return prompt, answer, wrong, family


def additional_case(rng, family, level, company, case_id, step):
    """Return all exhibits for the group and one independently answerable step."""
    if family == "market_entry":
        population = rng.randint(12, 40) * 1000 * level
        eligible, capture = rng.choice([20, 40, 50]), rng.choice([5, 10, 20])
        price, variable = rng.randint(12, 20) * 5, rng.randint(3, 8) * 5
        fixed = rng.randint(5, 25) * 1000
        cannibal = 0 if level == 1 else rng.choice([10, 20, 30])
        lost_margin = rng.randint(2, 6) * 5
        buyers = population * eligible * capture // 10000
        effective = price - variable - cannibal / 100 * lost_margin
        contribution = buyers * effective
        profit = contribution - fixed
        rows = [
            ["Population (people)", population],
            ["Eligible segment (%)", eligible],
            ["Capture of eligible segment (%)", capture],
            ["Annual purchases per captured buyer", 1],
            ["Price per purchase (£)", price],
            ["Variable cost per purchase (£)", variable],
            ["Annual entry fixed costs (£)", fixed],
            ["Captured buyers switching from existing business (%)", cannibal],
            ["Lost annual contribution per switching buyer (£)", lost_margin],
        ]
        background = f"{company} is considering entry into a new market. Each captured buyer buys once annually. Some buyers switch from its existing business, losing the stated existing contribution. All capture assumptions are forecasts, not guaranteed demand. Ignore tax, financing and unlisted costs."
        if step == 0:
            text, answer = "How many annual buyers does the entry forecast imply?", buyers
            wrong = [
                population * capture / 100,
                population * eligible / 100,
                population * (eligible + capture) / 100,
            ]
            explanation = f"{population:,} × {eligible}% × {capture}% = {buyers:,} buyers. Capture applies to the eligible segment, not the whole population."
        elif step == 1:
            text, answer = (
                "What is forecast annual incremental operating profit (£), after cannibalisation?",
                profit,
            )
            wrong = [buyers * (price - variable) - fixed, contribution, buyers * price - fixed]
            explanation = f"Incremental contribution per buyer = {price} − {variable} − {cannibal}% × {lost_margin} = £{effective:g}. Profit = {buyers} × {effective:g} − {fixed} = £{profit:,.2f}. Deduct lost existing contribution only for switching buyers."
        elif step == 2:
            answer = math.ceil(fixed / effective)
            text = "What minimum whole number of captured annual buyers covers entry fixed costs, holding the forecast switching mix constant?"
            wrong = [math.floor(fixed / effective), fixed / price, fixed / (price - variable)]
            explanation = f"Use net incremental contribution £{effective:g} per buyer. Ceiling({fixed}/{effective:g}) = {answer:,} buyers."
        else:
            text = "Before relying on this forecast to commit the entry fixed costs, which evidence most directly tests the revenue assumption?"
            answer = "A representative paid pilot in the eligible segment measuring realised capture and switching from existing products."
            wrong = [
                "A larger estimate of the total population without testing purchase behaviour.",
                "A survey of existing enthusiasts that asks only whether they like the concept.",
                "A confirmed fixed-cost quote without evidence about customer purchases.",
            ]
            explanation = f"Forecast profit is £{profit:,.2f}, but it depends on paid demand and cannibalisation. A representative paid pilot tests both; a population estimate or cost quote does not."
        chart = {
            "title": "Annual buyers by funnel stage (people)",
            "labels": ["Population", "Eligible", "Captured"],
            "values": [population, population * eligible / 100, buyers],
        }
        title = "market entry and cannibalisation"
    else:
        days, hours = rng.randint(18, 24), rng.randint(6, 8)
        rate_a, rate_b = rng.randint(45, 65), rng.randint(20, 35)
        yield_pct = 100 if level == 1 else rng.choice([80, 90, 95])
        added = rng.randint(10, 30)
        demand = rng.randint(6, 14) * 1000
        price, variable = rng.randint(15, 25), rng.randint(5, 12)
        fee = rng.randint(3, 12) * 1000
        old_capacity = math.floor(days * hours * min(rate_a, rate_b) * yield_pct / 100)
        new_capacity = math.floor(days * hours * min(rate_a, rate_b + added) * yield_pct / 100)
        old_sales, new_sales = min(demand, old_capacity), min(demand, new_capacity)
        added_sales = new_sales - old_sales
        change = added_sales * (price - variable) - fee
        rows = [
            ["Operating days/month", days],
            ["Operating hours/day", hours],
            ["Stage A gross units/hour", rate_a],
            ["Stage B current gross units/hour", rate_b],
            ["Stage B added gross units/hour", added],
            ["Final saleable yield (%)", yield_pct],
            ["Monthly demand (saleable units)", demand],
            ["Selling price (£/saleable unit)", price],
            ["Variable cost (£/saleable unit)", variable],
            ["Additional upgrade fee (£/month)", fee],
        ]
        background = f"{company} has two production stages in series with no inventory buffers. An upgrade increases only stage B's rate. Both stages operate the same hours; the slowest stage limits gross throughput. Apply final yield once after the bottleneck. Sales cannot exceed demand; there is no opening inventory. All figures are monthly. The upgrade changes no costs other than the stated fee; variable cost is per saleable unit."
        if step == 0:
            text, answer = (
                "What is current maximum saleable output per month, before the demand limit?",
                old_capacity,
            )
            wrong = [
                days * hours * (rate_a + rate_b) * yield_pct / 100,
                days * hours * rate_a * yield_pct / 100,
                days * hours * rate_b,
            ]
            explanation = f"Bottleneck rate = min({rate_a}, {rate_b}). Floor({days} × {hours} × {min(rate_a, rate_b)} × {yield_pct}%) = {old_capacity:,} saleable units. Do not add serial-stage capacities."
        elif step == 1:
            text, answer = (
                "How many additional saleable units can actually be sold monthly after the upgrade?",
                added_sales,
            )
            wrong = [new_capacity - old_capacity, days * hours * added, new_capacity]
            explanation = f"Current sales = min({demand:,}, {old_capacity:,}) = {old_sales:,}; upgraded sales = min({demand:,}, {new_capacity:,}) = {new_sales:,}. Additional sales = {added_sales:,}. Check the new bottleneck and demand."
        elif step == 2:
            text, answer = (
                "What is the monthly incremental operating profit (£) from the upgrade?",
                change,
            )
            wrong = [added_sales * price - fee, added_sales * (price - variable), change + fee]
            explanation = f"{added_sales:,} extra units × (£{price} − £{variable}) − £{fee:,} fee = £{change:,}. Unchanged existing fixed costs cancel."
        else:
            text = "Under the sole criterion of higher monthly operating profit, which recommendation is supported?"
            answer = (
                "Upgrade: demand-constrained incremental contribution exceeds the fee."
                if change > 0
                else "Keep the current line: the upgrade does not increase monthly profit."
            )
            wrong = [
                "Upgrade: all added stage B capacity automatically becomes extra sales.",
                "Upgrade: revenue from all existing units is an incremental benefit.",
                "Keep the current line: any positive upgrade fee makes investment unprofitable.",
            ]
            explanation = f"Incremental monthly profit is £{change:,}. Base the decision on incremental contribution after the bottleneck, yield, demand and fee, not on headline capacity."
        chart = {
            "title": "Gross stage rates (units/hour)",
            "labels": ["Stage A", "Stage B current", "Stage B upgraded"],
            "values": [rate_a, rate_b, rate_b + added],
        }
        title = "capacity and bottlenecks"
    prompt = {
        "instruction": "Use the shared exhibits. A calculator is allowed; round only the final result. Each question can be answered from the exhibits without your earlier answer.",
        "question": text,
        "explanation": explanation,
        "case_study": {
            "id": case_id,
            "title": f"{company}: {title}",
            "background": background,
            "question_index": step + 1,
            "question_total": 4,
        },
        "data_table": {
            "caption": "Case operating assumptions",
            "columns": ["Measure", "Value"],
            "rows": rows,
        },
        "chart": chart,
    }
    return prompt, answer, wrong
