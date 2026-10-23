from __future__ import annotations

from django.urls import reverse

from backend.apps.assessments.config import ASSESSMENT_CCAT, ASSESSMENT_PREPGIA

ASSESSMENT_GUIDES = {
    "thomas-gia": {
        "assessment_type": ASSESSMENT_PREPGIA,
        "title": "Thomas GIA assessment test guide",
        "page_title": "Thomas GIA Test Guide: Format, Sections & Practice | MindMetric",
        "meta_description": (
            "Learn the Thomas GIA test format, five sections, timing, practice pattern "
            "and preparation strategies before starting free GIA practice questions."
        ),
        "eyebrow": "Thomas International GIA",
        "intro": (
            "A practical guide to the General Intelligence Assessment: what each test "
            "measures, how the session is structured, and how to prepare for its speed."
        ),
        "facts": [
            ("5", "timed tests"),
            ("2-5 min", "per test"),
            ("30-45 min", "including instructions"),
            ("8", "practice examples before each test"),
        ],
        "overview": (
            "Thomas describes the GIA as five short tests covering reasoning, perceptual "
            "speed, number speed and accuracy, word meaning, and spatial visualisation. "
            "The official example booklet says speed and accuracy are equally important."
        ),
        "format_points": [
            "Each test begins with instructions and eight practice examples before the scored section.",
            "The individual tests are short, usually two to five minutes, so quick recognition matters.",
            "The official example booklet describes a mouse-driven assessment; follow the instructions in your invitation.",
            "MindMetric practice is representative preparation, not a copy of proprietary live questions.",
        ],
        "scoring": (
            "GIA reports are interpreted by the organisation administering the assessment. "
            "Rather than chasing a fixed pass mark, train both reliable accuracy and faster "
            "decision-making across all five areas."
        ),
        "preparation_steps": [
            "Learn one question mechanic at a time without time pressure.",
            "Review errors and identify whether wording, calculation, or visual comparison slowed you down.",
            "Repeat short timed drills, then use a full test to practise switching between sections.",
            "Read every official instruction screen carefully because the interaction changes by section.",
        ],
        "faqs": [
            ("What is the Thomas GIA assessment?", "The Thomas General Intelligence Assessment, commonly called the Thomas GIA, is a timed cognitive aptitude assessment with five short sections. It measures reasoning, perceptual speed, number speed and accuracy, word meaning, and spatial visualisation."),
            ("How long is the Thomas GIA?", "Thomas says the complete session, including instructions, usually takes 30 to 45 minutes; each of the five tests lasts about two to five minutes."),
            ("How many sections are in the GIA?", "There are five: Reasoning, Perceptual Speed, Number Speed and Accuracy, Word Meaning, and Spatial Visualisation."),
            ("Is there one fixed pass score?", "No universal pass mark is published. Employers interpret results for their role and selection process."),
        ],
        "sources": [
            ("Thomas: Aptitude assessment basics", "https://knowledge.thomas.co/assess-connect/aptitude-the-basics"),
            ("Thomas GIA example booklet", "https://www.thomas.co/sites/default/files/2019-08/GIA-Example-Booklet-2018.pdf"),
        ],
    },
    "ccat": {
        "assessment_type": ASSESSMENT_CCAT,
        "title": "CCAT assessment test guide",
        "page_title": "CCAT Test Guide: 50 Questions, 15 Minutes & Practice | MindMetric",
        "meta_description": (
            "Learn the Criteria Cognitive Aptitude Test format, 50-question and 15-minute "
            "pattern, scoring, question categories, and practical CCAT preparation strategies."
        ),
        "eyebrow": "Criteria Cognitive Aptitude Test",
        "intro": (
            "A clear guide to the CCAT's fast 50-question format, its verbal, mathematical "
            "and spatial content, and the pacing decisions that matter most."
        ),
        "facts": [
            ("50", "questions"),
            ("15 min", "total time"),
            ("18 sec", "average available per question"),
            ("No", "calculator"),
        ],
        "overview": (
            "Criteria describes the CCAT as a measure of critical thinking, problem solving, "
            "learning ability, and applying new information. Questions draw from verbal, "
            "math and logic, and spatial reasoning categories."
        ),
        "format_points": [
            "You have 15 minutes for 50 questions and are not expected to finish every item.",
            "There is no penalty for a wrong answer, according to Criteria's candidate preparation page.",
            "Calculators are not permitted, so practise mental arithmetic and estimation.",
            "Criteria uses a dynamic item bank, so a guaranteed category-by-category question split is not published.",
        ],
        "scoring": (
            "Criteria reports a raw score based on correct answers and a percentile ranking "
            "against a comparison group. Because unanswered questions do not help and wrong "
            "answers are not penalised, pacing and sensible elimination are important."
        ),
        "preparation_steps": [
            "Build fluency in percentages, ratios, sequences, vocabulary, analogies, and visual patterns.",
            "Skip a question when the solution path is not clear; return only if time remains.",
            "Practise without a calculator and use estimation before exact arithmetic.",
            "Complete full 15-minute simulations after learning each category separately.",
        ],
        "faqs": [
            ("How should I use a CCAT practice test?", "Use untimed practice questions to learn each question type, review why an answer was incorrect, then complete a timed 15-minute practice test to build pacing and confidence."),
            ("How many questions are on the CCAT?", "The official CCAT has 50 questions to be attempted in 15 minutes."),
            ("Do I need to finish all 50 questions?", "No. Criteria says fewer than one percent of candidates answer all 50, so focus on efficient, accurate progress."),
            ("Can I use a calculator?", "No. Criteria's candidate guidance says calculators are not permitted."),
        ],
        "sources": [
            ("Criteria: official CCAT overview", "https://www.criteriacorp.com/assess/cognitive-aptitude/criteria-cognitive-aptitude-test-ccat"),
            ("Criteria: candidate CCAT preparation", "https://www.criteriacorp.com/candidates/ccat-prep"),
        ],
    },
}


MODULE_GUIDES = {
    ASSESSMENT_PREPGIA: {
        "reasoning": {
            "slug": "reasoning",
            "title": "Thomas GIA Reasoning guide",
            "subtitle": "Remember verbal comparisons and infer the correct relationship.",
            "official_task": "Thomas describes this test as holding verbal information in short-term memory and using it to draw a conclusion.",
            "pattern": ["Read and simplify the comparison.", "Keep the direction of the relationship clear.", "Answer after the original information is no longer visible."],
            "example": "If Mira is faster than Leo, and the question asks who is slower, the answer is Leo.",
            "strategies": ["Translate comparative wording into a simple ordered pair.", "Watch for reversals such as less, slower, or not as strong.", "Answer from the relationship rather than the order of names."],
            "watch_out": "Negative and reversed wording can invert an otherwise simple relationship.",
            "quick_tip": "Mentally put the stronger or greater item first.",
        },
        "perceptual_speed": {
            "slug": "perceptual-speed",
            "title": "Thomas GIA Perceptual Speed guide",
            "subtitle": "Compare character pairs quickly while ignoring irrelevant detail.",
            "official_task": "Thomas says this test measures rapid matching of letters and symbols, error detection, and the ability to ignore irrelevant information.",
            "pattern": ["Scan each pair in a consistent direction.", "Count only exact matches.", "Confirm the count before selecting an answer."],
            "example": "AB/AB is a match, while PQ/QP is not; swapped order matters.",
            "strategies": ["Use the same left-to-right scan every time.", "Treat reversed characters as different unless instructed otherwise.", "Keep a small running count instead of rescanning."],
            "watch_out": "Near-identical pairs and reversed order are designed to attract a fast mistake.",
            "quick_tip": "Move your eyes, not your whole attention, one pair at a time.",
        },
        "number_speed_accuracy": {
            "slug": "number-speed-and-accuracy",
            "title": "Thomas GIA Number Speed & Accuracy guide",
            "subtitle": "Manipulate simple numerical information accurately at speed.",
            "official_task": "Thomas describes this area as identifying numerical distance and manipulating numerical information.",
            "pattern": ["Identify exactly what comparison or operation is requested.", "Use mental arithmetic rather than writing a long solution.", "Check the sign and direction before answering."],
            "example": "The distance between 17 and 12 is 5; numerical distance is always the size of the gap.",
            "strategies": ["Memorise common differences and number bonds.", "Estimate first so an impossible result stands out.", "Do not overcomplicate a short arithmetic operation."],
            "watch_out": "Choosing the larger number instead of the distance between numbers.",
            "quick_tip": "Think in gaps on a number line.",
        },
        "word_meaning": {
            "slug": "word-meaning",
            "title": "Thomas GIA Word Meaning guide",
            "subtitle": "Recognise meaning relationships between words quickly.",
            "official_task": "Thomas says this test asks candidates to identify two words with similar meaning from a group of three.",
            "pattern": ["Read all words before committing.", "Find the closest pair in meaning.", "Use context and word roots when a word is unfamiliar."],
            "example": "Rapid and swift are closer in meaning than rapid and quiet.",
            "strategies": ["Build vocabulary through synonyms and antonyms.", "Compare precise meaning, not just emotional tone.", "Eliminate the clearly unrelated word first."],
            "watch_out": "Words that occur in the same context are not always synonyms.",
            "quick_tip": "Ask whether the two words could replace each other in a sentence.",
        },
        "spatial_visualization": {
            "slug": "spatial-visualisation",
            "title": "Thomas GIA Spatial Visualisation guide",
            "subtitle": "Mentally manipulate and compare symbols and shapes.",
            "official_task": "Thomas describes this area as the ability to mentally manipulate symbols and shapes.",
            "pattern": ["Choose one distinctive feature as an anchor.", "Track rotation separately from reflection.", "Compare orientation only after checking the internal marks."],
            "example": "A clockwise rotation preserves handedness; a mirror reflection reverses it.",
            "strategies": ["Track one corner, notch, or dot through the movement.", "Use quarter-turns instead of imagining a continuous spin.", "Eliminate options with impossible reflections first."],
            "watch_out": "A reflected shape can look like a rotation at first glance.",
            "quick_tip": "Follow one asymmetrical detail rather than the whole figure.",
        },
    },
    ASSESSMENT_CCAT: {
        "ccat_numerical": {
            "slug": "numerical-reasoning",
            "title": "CCAT Math & Numerical Reasoning guide",
            "subtitle": "Solve short arithmetic, ratio, percentage, and sequence problems without a calculator.",
            "official_task": "Numerical questions form part of the CCAT's math and logic category within the overall 50-question, 15-minute assessment.",
            "pattern": ["Identify the operation or number pattern.", "Estimate the likely range.", "Calculate only what is required and eliminate unsuitable options."],
            "example": "If a price rises from 40 to 50, the increase is 10/40 = 25%.",
            "strategies": ["Know common fractions, percentages, and multiplication facts.", "Test differences and ratios quickly in number sequences.", "Use answer choices to avoid unnecessary precision."],
            "watch_out": "Spending too long on exact arithmetic when estimation separates the options.",
            "quick_tip": "Check units and direction before calculating.",
        },
        "ccat_verbal": {
            "slug": "verbal-reasoning",
            "title": "CCAT Verbal Reasoning guide",
            "subtitle": "Work with vocabulary, analogies, sentence logic, and verbal relationships.",
            "official_task": "Verbal questions are one of Criteria's three broad CCAT categories and test how quickly you understand and apply word relationships.",
            "pattern": ["Identify the exact relationship in the prompt.", "Apply the same relationship to each option.", "Eliminate choices that fit the topic but not the logic."],
            "example": "Bird is to nest as bee is to hive: the relationship is animal to home.",
            "strategies": ["State analogy relationships as a short sentence.", "Use prefixes, suffixes, and roots for unfamiliar vocabulary.", "Read sentence-completion choices back in context."],
            "watch_out": "An option may be associated with a word without sharing the required relationship.",
            "quick_tip": "Name the relationship before looking at the answers.",
        },
        "ccat_spatial": {
            "slug": "spatial-reasoning",
            "title": "CCAT Spatial & Abstract Reasoning guide",
            "subtitle": "Recognise visual sequences, transformations, and non-verbal rules.",
            "official_task": "Spatial reasoning is one of the CCAT's three broad categories and assesses rapid recognition of visual rules and relationships.",
            "pattern": ["Compare position, count, fill, and orientation independently.", "Find the feature that changes consistently each step.", "Apply that rule once to predict the missing figure."],
            "example": "If a shape gains one side at each step, triangle, square, pentagon is followed by a hexagon.",
            "strategies": ["Check simple changes before combining multiple rules.", "Track rotation angle and fill state separately.", "Eliminate options that break any established rule."],
            "watch_out": "Decorative differences can distract from the single feature controlling the sequence.",
            "quick_tip": "Make a short checklist: count, position, rotation, fill.",
        },
    },
}


def _assessment_slug_for_type(assessment_type: str) -> str | None:
    return next((slug for slug, guide in ASSESSMENT_GUIDES.items() if guide["assessment_type"] == assessment_type), None)


def get_assessment_guide_url(assessment_type: str) -> str:
    slug = _assessment_slug_for_type(assessment_type)
    return reverse("pages:assessment-guide", args=[slug]) if slug else ""


def get_module_guide_url(assessment_type: str, module_key: str) -> str:
    assessment_slug = _assessment_slug_for_type(assessment_type)
    module = MODULE_GUIDES.get(assessment_type, {}).get(module_key)
    if not assessment_slug or not module:
        return ""
    return reverse("pages:module-guide", args=[assessment_slug, module["slug"]])


def resolve_assessment_guide(slug: str) -> dict | None:
    guide = ASSESSMENT_GUIDES.get(slug)
    return {**guide, "slug": slug} if guide else None


def resolve_module_guide(assessment_slug: str, module_slug: str) -> tuple[dict, dict] | None:
    assessment = resolve_assessment_guide(assessment_slug)
    if not assessment:
        return None
    for key, module in MODULE_GUIDES.get(assessment["assessment_type"], {}).items():
        if module["slug"] == module_slug:
            return assessment, {**module, "key": key}
    return None


def iter_assessment_guides():
    return (resolve_assessment_guide(slug) for slug in ASSESSMENT_GUIDES)


def iter_module_guides():
    for assessment_slug, assessment in ASSESSMENT_GUIDES.items():
        for module in MODULE_GUIDES.get(assessment["assessment_type"], {}).values():
            yield assessment_slug, module["slug"]
