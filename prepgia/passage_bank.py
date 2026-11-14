"""Original linked passages. Independent editorial approval is tracked in admin."""


def item(skill, claim, answer, explanation):
    choices = (
        ["True", "Probably true", "Insufficient data", "Probably false", "False"]
        if skill == "inference"
        else ["Assumption made", "Assumption not made"]
        if skill == "assumptions"
        else ["Strong", "Weak"]
        if skill == "arguments"
        else ["Follows", "Does not follow"]
    )
    return {
        "skill": skill,
        "question": claim,
        "kind": "choice",
        "options": choices,
        "answer": answer,
        "explanation": explanation,
    }


PASSAGES = [
    {
        "key": "library-access",
        "title": "Library booking and equitable access",
        "body": "A city library is considering replacing its staffed room-booking desk with an online service. In a random survey of 400 current users, with full response, 76% said online booking would be convenient. The survey's stated margin of error was five percentage points, and it is assumed representative of current users. A separate accessibility audit identified 28 current users who cannot complete the online process without assistance. Staff confirmed that all 28 currently use the desk. The proposed plan would remove the desk and provide no telephone or assisted alternative. The board's binding objective is to preserve each current user's ability to book independently; average convenience alone is not sufficient. A manager nevertheless recommends the online-only proposal because most survey respondents like it. The survey did not ask whether users would pay a booking fee. The library has not yet priced a modified proposal that retains assistance.",
        "items": [
            item(
                "inference",
                "Most current users would find online booking convenient.",
                "Probably true",
                "The representative 76% sample supports a population majority, without establishing every user's preference.",
            ),
            item(
                "assumptions",
                "The manager's argument takes for granted that majority convenience is enough to justify a plan under the board's all-user access objective.",
                "Assumption made",
                "The recommendation relies on treating the majority result as sufficient, despite a stricter all-user requirement.",
            ),
            item(
                "deduction",
                "At least one user who currently books independently would lose that ability under the online-only plan.",
                "Follows",
                "The audit establishes 28 such users, and the proposal removes their only usable channel.",
            ),
            item(
                "interpretation",
                "The convenience survey establishes willingness to pay a new booking fee.",
                "Does not follow",
                "Convenience and willingness to pay are different constructs; the latter was not measured.",
            ),
            item(
                "arguments",
                "Against the online-only plan: the audited users would lose independent access, violating the board's binding objective.",
                "Strong",
                "This is an important, direct objection to the exact objective, even though most respondents favour online convenience.",
            ),
        ],
    },
    {
        "key": "clinic-triage",
        "title": "Clinic waiting times and case mix",
        "body": "A clinic introduced a new triage process in April. Complete records show that average waiting time among completed visits fell from 40 minutes in March to 28 minutes in April. At the same time, an additional clinician joined, and the share of routine rather than complex visits increased. No comparison clinic was observed. The records omit patients who left before seeing a clinician, and no follow-up survey contacted them. A clinical policy requires every urgent patient to receive a nurse assessment before treatment; every nurse-assessed patient receives a recorded priority code. Patient K has no priority code in a complete, error-free record. The director recommends keeping the new process because of the apparent improvement in service. Her stated reason uses the two months' recorded averages, rather than a controlled estimate of the process's effect. The clinic's objective is to reduce waiting without preventing urgent patients from being assessed. No evidence about next month's staffing has been collected.",
        "items": [
            item(
                "inference",
                "Average waiting time for completed visits was lower in April.",
                "True",
                "The complete records explicitly report 28 rather than 40 minutes for that defined group.",
            ),
            item(
                "assumptions",
                "The director assumes that the entire apparent improvement is not merely a change in who remains in the recorded group.",
                "Assumption made",
                "If only the composition of recorded patients changed, the stated averages would not support the claimed service improvement.",
            ),
            item(
                "deduction",
                "Patient K has not had the required nurse assessment.",
                "Follows",
                "All nurse assessments imply a code, and K's complete record has none. Apply the contrapositive.",
            ),
            item(
                "interpretation",
                "The triage process alone caused the twelve-minute reduction.",
                "Does not follow",
                "Staffing and case mix changed too; the observational comparison does not isolate the cause.",
            ),
            item(
                "arguments",
                "For permanent adoption: the average among completers fell, so outcomes for patients who left without treatment need not be investigated.",
                "Weak",
                "The missing group matters to the stated urgent-access objective; a better recorded average cannot dismiss it.",
            ),
        ],
    },
    {
        "key": "training-pilot",
        "title": "A controlled training pilot",
        "body": "A manufacturer randomly assigned 120 comparable workers equally between a training pilot and a control group. Both groups started at 50 completed units per worker per day. After six weeks the trained group averaged 60 and the control group averaged 54. Attendance and measurement were complete, and no differential change other than training affected the groups during the pilot. Defect rates were unchanged. The programme costs £18,000 to expand, and the pilot's estimated annual contribution gain after recurring costs is £30,000. That annual forecast assumes the observed productivity effect lasts; the pilot itself ran for only six weeks. Management recommends expansion on the basis of a positive first-year net contribution, with defect rates no worse than today. Workers were not asked about job satisfaction. A supplier says that the training is popular at other firms, but supplies no comparison data about those firms. No benefits outside contribution and defect performance are required by management's decision rule.",
        "items": [
            item(
                "inference",
                "The pilot establishes that trained workers were more satisfied with their jobs.",
                "Insufficient data",
                "Job satisfaction was not measured; productivity does not establish satisfaction.",
            ),
            item(
                "assumptions",
                "The expansion recommendation assumes the forecast gain persists long enough to cover the implementation cost in year one.",
                "Assumption made",
                "If the realised first-year gain cannot cover implementation, the stated positive-net-contribution justification fails.",
            ),
            item(
                "deduction",
                "The observed productivity uplift net of the control-group change is six units per worker per day.",
                "Follows",
                "The trained group gained ten units and the control group four; the difference is six under the explicit pilot assumptions.",
            ),
            item(
                "interpretation",
                "The annual gain is guaranteed because the six-week pilot was controlled.",
                "Does not follow",
                "Control strengthens causal attribution during the observed period, not a guarantee of effect persistence over an unobserved year.",
            ),
            item(
                "arguments",
                "For expansion under the forecast: £30,000 annual contribution less £18,000 implementation leaves £12,000 in year one, with unchanged defects.",
                "Strong",
                "It directly addresses both stated criteria, conditional on the forecast rather than pretending it is certain.",
            ),
        ],
    },
    {
        "key": "delivery-mix",
        "title": "Delivery performance and changing weights",
        "body": "A delivery firm reports complete results for two disjoint service segments. Before a routing change, the express segment delivered 900 of 1,000 parcels on time and the economy segment delivered 100 of 1,000 on time. After the change, express delivered 90 of 100 on time and economy delivered 380 of 1,900 on time. On-time definitions and measurement did not change. The express rate was unchanged, the economy rate increased, and a much larger share of parcels moved through economy. The business does not know why customers changed service type. Every express parcel receives a tracking code, but economy parcels may also receive codes. Parcel R has a tracking code; its service type is not otherwise recorded. Management's sole objective is to improve the combined on-time rate without increasing total monthly spending. A proposal cites only the economy rate improvement. The firm's total spending for the two periods has not yet been supplied.",
        "items": [
            item(
                "inference",
                "The economy segment's on-time rate rose from 10% to 20%.",
                "True",
                "Compute 100/1000 and 380/1900; these are exactly 10% and 20%.",
            ),
            item(
                "assumptions",
                "The proposal's use of the economy improvement as sufficient evidence takes for granted that a segment improvement is enough to meet the combined-rate objective.",
                "Assumption made",
                "A component improvement alone is insufficient if the combined outcome is what matters; that bridge is taken for granted.",
            ),
            item(
                "deduction",
                "Parcel R must be an express parcel.",
                "Does not follow",
                "Tracking is necessary for express, not exclusive to express; the implication cannot be reversed.",
            ),
            item(
                "interpretation",
                "The combined on-time rate fell despite the improved economy rate.",
                "Follows",
                "Before: 1000/2000 = 50%. After: 470/2000 = 23.5%. The service mix explains why a segment improvement need not improve the total.",
            ),
            item(
                "arguments",
                "Against claiming the objective is met: the combined rate fell and the spending condition has not been checked.",
                "Strong",
                "The objection addresses both the observed failure of the rate criterion and a missing required cost check.",
            ),
        ],
    },
    {
        "key": "energy-retrofit",
        "title": "Retrofit savings and measurement",
        "body": "A housing association trialled insulation in 200 occupied homes over winter. Meter readings were complete for all participating homes, and measured heating energy use fell by 15% relative to the previous winter. The later winter was milder; occupancy and heating tariffs also changed. There was no untreated comparison group or weather-adjusted analysis. Residents who joined the trial volunteered, and most had previously requested insulation. The association wants to estimate savings across all 5,000 homes, including homes with different construction types. A finance manager recommends a full rollout because the measured energy reduction should cover the rollout cost. The financial forecast has not yet adjusted for construction-specific installation costs. Every property approved for installation must pass a safety survey. Property M has not passed that survey. Resident comments were collected only from those who completed an optional satisfaction form; nonrespondents' views are unknown.",
        "items": [
            item(
                "inference",
                "The participating homes' measured heating energy use fell by 15%.",
                "True",
                "This is the recorded before-and-after observation for participants, not an isolated causal effect.",
            ),
            item(
                "assumptions",
                "The finance manager assumes that achievable net savings across the rollout population are sufficient to cover its costs.",
                "Assumption made",
                "Negating that assumption removes the manager's stated financial justification; an unadjusted pilot alone does not establish it.",
            ),
            item(
                "deduction",
                "Property M cannot yet be approved for installation under the stated rule.",
                "Follows",
                "Passing the survey is necessary for approval; M has not passed.",
            ),
            item(
                "interpretation",
                "The trial establishes a 15% insulation-caused reduction for every construction type across all homes.",
                "Does not follow",
                "Voluntary selection, concurrent weather changes and untested construction types limit both causality and generalisation.",
            ),
            item(
                "arguments",
                "For immediate universal rollout: satisfied optional-form respondents liked the installation, so population costs and weather adjustment are irrelevant.",
                "Weak",
                "Selected satisfaction responses cannot establish the net financial savings on which the recommendation depends.",
            ),
        ],
    },
    {
        "key": "subscription-pricing",
        "title": "Pricing, retention and contribution",
        "body": "A software service tested a higher subscription price in one region. Monthly price increased from £20 to £22, while subscribers fell from 1,000 to 950. Variable service cost remained £5 per subscriber and fixed costs were unchanged. All figures cover complete monthly records; there was no tax or currency change. A competitor launched a promotion during the same month, and no comparable untreated region was measured. A random, fully responding sample of 300 remaining subscribers found that 80% valued a newly introduced support feature; its margin of error was five percentage points. Former subscribers were excluded. The pricing committee's stated objective is higher monthly contribution rather than subscriber growth alone. Every account receiving priority support must be verified. Some verified accounts do not receive priority support. Account S is verified, but no record states its support level. No annual renewal outcomes have yet been observed.",
        "items": [
            item(
                "inference",
                "Most remaining subscribers value the new support feature.",
                "Probably true",
                "The representative sample of remaining subscribers supports a majority in that group, not all past customers.",
            ),
            item(
                "assumptions",
                "A recommendation based solely on this month's higher contribution assumes contribution is the criterion the committee should apply.",
                "Assumption made",
                "The justification relies on that decision criterion; it is also explicitly consistent with the committee's stated objective.",
            ),
            item(
                "deduction",
                "Account S must receive priority support.",
                "Does not follow",
                "Verification is necessary but not sufficient for priority support; some verified accounts lack it.",
            ),
            item(
                "interpretation",
                "Monthly contribution increased from £15,000 to £16,150 despite fewer subscribers.",
                "Follows",
                "1000 × (20−5) = 15,000; 950 × (22−5) = 16,150. Subscriber growth and contribution growth differ.",
            ),
            item(
                "arguments",
                "Against claiming guaranteed annual success: no annual renewals were observed and the one-region comparison does not isolate the price effect.",
                "Strong",
                "The objection is directly relevant to a guarantee about longer-term causal performance, without denying the observed monthly gain.",
            ),
        ],
    },
]
