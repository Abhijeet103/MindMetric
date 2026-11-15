"""German and Spanish content for the Thomas GIA-style generators.

English stays in prepgia/generators.py. Everything here is original wording;
the languages are released as Beta pending native review.
"""
from __future__ import annotations

GIA_LANGUAGES = ("en", "de", "es")

# ---------------------------------------------------------------- German
# German predicate comparatives do not inflect, so one form per trait works for
# every name. (greater comparative, lesser comparative, greater base, lesser base)
DE_TRAITS = [
    ("größer", "kleiner", "groß", "klein"),
    ("schwerer", "leichter", "schwer", "leicht"),
    ("stärker", "schwächer", "stark", "schwach"),
    ("schneller", "langsamer", "schnell", "langsam"),
    ("älter", "jünger", "alt", "jung"),
    ("glücklicher", "trauriger", "glücklich", "traurig"),
    ("reicher", "ärmer", "reich", "arm"),
    ("lauter", "leiser", "laut", "leise"),
    ("mutiger", "ängstlicher", "mutig", "ängstlich"),
    ("geduldiger", "ungeduldiger", "geduldig", "ungeduldig"),
    ("freundlicher", "unfreundlicher", "freundlich", "unfreundlich"),
    ("vorsichtiger", "unvorsichtiger", "vorsichtig", "unvorsichtig"),
    ("fleißiger", "fauler", "fleißig", "faul"),
    ("zuverlässiger", "weniger zuverlässig", "zuverlässig", None),
    ("kreativer", "weniger kreativ", "kreativ", None),
    ("großzügiger", "weniger großzügig", "großzügig", None),
]
DE_NAMES = [
    "Lukas", "Anna", "Felix", "Lena", "Jonas", "Marie", "Paul", "Sophie", "Leon", "Emma",
    "Finn", "Mia", "Ben", "Hannah", "Elias", "Lea", "Noah", "Clara", "Moritz", "Laura",
    "Jan", "Julia", "Tim", "Lisa", "David", "Sarah", "Max", "Nina", "Erik", "Greta",
    "Karl", "Ida", "Oskar", "Frieda", "Theo", "Lina",
]
DE_COMPARISON_TEMPLATES = [
    ("{first} ist {greater} als {second}.", "greater"),
    ("{first} ist {lesser} als {second}.", "lesser"),
    ("{first} ist nicht so {greater_base} wie {second}.", "lesser"),
    ("{first} ist nicht so {lesser_base} wie {second}.", "greater"),
]
DE_QUESTION_TEMPLATES = ["Wer ist {comparative}?", "Wer von beiden ist {comparative}?"]
DE_REASONING_EXPLANATION = "{greater} ist {greater_word} als {lesser}; die Antwort lautet daher {answer}."

# ---------------------------------------------------------------- Spanish
# Spanish adjectives agree with the subject, so both people in a question share
# a gender and every form is stored as (masculine, feminine). Comparative
# forms include "más" so irregular ones (mayor/menor) fit the same templates.
ES_NAMES = {
    "m": ["Pablo", "Diego", "Javier", "Mateo", "Lucas", "Daniel", "Carlos", "Andrés", "Hugo", "Martín",
          "Sergio", "Tomás", "Alejandro", "Gabriel", "Iván", "Raúl", "Óscar", "Adrián"],
    "f": ["Lucía", "María", "Sofía", "Elena", "Carmen", "Paula", "Valeria", "Marta", "Laura", "Julia",
          "Ana", "Sara", "Irene", "Claudia", "Inés", "Noelia", "Alba", "Rocío"],
}


def _es(adjective_m: str, adjective_f: str | None = None) -> tuple[str, str]:
    return adjective_m, adjective_f or adjective_m


ES_TRAITS = [
    # greater comparative, lesser comparative, greater base, lesser base
    (("más alto", "más alta"), ("más bajo", "más baja"), _es("alto", "alta"), _es("bajo", "baja")),
    (("más pesado", "más pesada"), ("más ligero", "más ligera"), _es("pesado", "pesada"), _es("ligero", "ligera")),
    (_es("más fuerte"), _es("más débil"), _es("fuerte"), _es("débil")),
    (("más rápido", "más rápida"), ("más lento", "más lenta"), _es("rápido", "rápida"), _es("lento", "lenta")),
    (_es("mayor"), _es("menor"), None, None),
    (_es("más feliz"), _es("más triste"), _es("feliz"), _es("triste")),
    (("más rico", "más rica"), ("más pobre", "más pobre"), _es("rico", "rica"), _es("pobre")),
    (("más ruidoso", "más ruidosa"), ("más silencioso", "más silenciosa"), _es("ruidoso", "ruidosa"), _es("silencioso", "silenciosa")),
    (_es("más valiente"), ("más miedoso", "más miedosa"), _es("valiente"), _es("miedoso", "miedosa")),
    (_es("más paciente"), _es("más impaciente"), _es("paciente"), _es("impaciente")),
    (_es("más amable"), _es("menos amable"), _es("amable"), None),
    (("más cuidadoso", "más cuidadosa"), ("más descuidado", "más descuidada"), _es("cuidadoso", "cuidadosa"), _es("descuidado", "descuidada")),
    (("más trabajador", "más trabajadora"), ("más perezoso", "más perezosa"), _es("trabajador", "trabajadora"), _es("perezoso", "perezosa")),
    (_es("más fiable"), _es("menos fiable"), _es("fiable"), None),
    (_es("más creativo", "más creativa"), _es("menos creativo", "menos creativa"), _es("creativo", "creativa"), None),
    (("más generoso", "más generosa"), _es("menos generoso", "menos generosa"), _es("generoso", "generosa"), None),
]
ES_COMPARISON_TEMPLATES = [
    ("{first} es {greater} que {second}.", "greater"),
    ("{first} es {lesser} que {second}.", "lesser"),
    ("{first} no es tan {greater_base} como {second}.", "lesser"),
    ("{first} no es tan {lesser_base} como {second}.", "greater"),
]
ES_QUESTION_TEMPLATES = {
    "m": ["¿Quién es {comparative}?", "¿Cuál de los dos es {comparative}?"],
    "f": ["¿Quién es {comparative}?", "¿Cuál de las dos es {comparative}?"],
}
ES_REASONING_EXPLANATION = "{greater} es {greater_word} que {lesser}; por lo tanto, la respuesta es {answer}."

# ------------------------------------------------- other sections, by language
PERCEPTUAL_INSTRUCTIONS = {
    "de": [
        "Wie viele Paare zeigen denselben Buchstaben, einmal groß und einmal klein geschrieben?",
        "Zählen Sie die Paare, deren Buchstaben bis auf die Groß- und Kleinschreibung gleich sind.",
        "Wie viele Paare bestehen aus demselben Buchstaben in Groß- und Kleinschreibung?",
    ],
    "es": [
        "¿Cuántos pares muestran la misma letra, una vez en mayúscula y otra en minúscula?",
        "Cuente los pares cuyas letras coinciden salvo por las mayúsculas y minúsculas.",
        "¿Cuántos pares contienen la misma letra en mayúscula y en minúscula?",
    ],
}
# (matches listed, no matches, one match, several matches)
PERCEPTUAL_EXPLANATION = {
    "de": ("Übereinstimmende Paare: {pairs}.", "Kein Paar stimmt überein.", " Das ist 1 Übereinstimmung.", " Das sind {count} Übereinstimmungen."),
    "es": ("Pares que coinciden: {pairs}.", "Ningún par coincide.", " Hay 1 coincidencia.", " Hay {count} coincidencias."),
}


def perceptual_explanation(language: str, matching: str, count: int) -> str:
    listed, none, one, several = PERCEPTUAL_EXPLANATION[language]
    if count == 0:
        return none
    return listed.format(pairs=matching) + (one if count == 1 else several.format(count=count))
NUMBER_INSTRUCTION = {
    "de": "Welche Zahl ist am weitesten vom mittleren Wert entfernt?",
    "es": "¿Qué número está más lejos del valor intermedio?",
}
NUMBER_EXPLANATION = {
    "de": "Der Größe nach: {a}, {b}, {c}. Die Abstände betragen {low} und {high}; {answer} liegt weiter von {b} entfernt.",
    "es": "En orden: {a}, {b}, {c}. Las diferencias son {low} y {high}; {answer} está más lejos de {b}.",
}
WORD_MEANING_INSTRUCTIONS = {
    "de": [
        "Welches Wort passt nicht zu den anderen beiden?",
        "Wählen Sie das Wort, das nicht dazugehört.",
        "Welches Wort fällt aus der Reihe?",
    ],
    "es": [
        "¿Qué palabra no encaja con las otras dos?",
        "Elija la palabra que no pertenece al grupo.",
        "¿Qué palabra es la que sobra?",
    ],
}
WORD_MEANING_ODD_SUFFIX = {
    "de": "; „{odd}“ passt nicht dazu.",
    "es": "; «{odd}» no comparte ese significado.",
}
SPATIAL_INSTRUCTION = {
    "de": "Wie viele Paare zeigen dasselbe Bild?",
    "es": "¿Cuántos pares muestran la misma imagen?",
}
SPATIAL_PAIR_EXPLANATION = {
    "de": ("Paar {n} ist dasselbe Bild, nur gedreht.", "Paar {n} ist ein gedrehtes Spiegelbild."),
    "es": ("El par {n} es la misma imagen, solo girada.", "El par {n} es una imagen especular girada."),
}
SPATIAL_TOTAL = {
    "de": " Übereinstimmende Paare insgesamt: {count}.",
    "es": " Total de pares que coinciden: {count}.",
}


def normalize_language(language: str | None) -> str:
    return language if language in GIA_LANGUAGES else "en"
