"""Interface translations for the Thomas GIA practice in German and Spanish.

The English text is the key and the fallback, so English pages render exactly
as before. Only Thomas GIA is localized; every other test stays English.
Translations are Beta, pending native review.
"""
from __future__ import annotations

import copy
import re

LANGUAGES = {"en": "English", "de": "Deutsch", "es": "Español"}
BETA_LANGUAGES = frozenset({"de", "es"})
LOCALIZED_ASSESSMENTS = frozenset({"prepgia"})
SESSION_KEY = "gia_language"

_DE = {
    # Assessment and module configuration
    "Thomas International GIA cognitive ability practice with timed tests and section-wise drills.":
        "Übung für den kognitiven Fähigkeitstest Thomas International GIA mit Zeittests und Übungen je Abschnitt.",
    "Full test": "Gesamttest",
    "All five sections in one flow, designed to feel very close to the real GIA.":
        "Alle fünf Abschnitte in einem Durchgang, so nah wie möglich am echten GIA.",
    "Each section is shown one by one. First you get instructions, then eight practice questions with instant feedback, then the timed test for that section.":
        "Die Abschnitte folgen nacheinander. Zuerst erhalten Sie die Anleitung, dann acht Übungsfragen mit sofortiger Rückmeldung und anschließend den Zeittest für diesen Abschnitt.",
    "Modules": "Module",
    "Reasoning": "Logisches Denken",
    "Perceptual Speed": "Wahrnehmungsgeschwindigkeit",
    "Number Speed & Accuracy": "Zahlen: Tempo und Genauigkeit",
    "Word Meaning": "Wortbedeutung",
    "Spatial Visualization": "Räumliches Vorstellungsvermögen",
    "Comparative and transitive logic questions under timed conditions.":
        "Vergleichs- und Schlussfolgerungsaufgaben unter Zeitdruck.",
    "Fast letter-pair matching built to simulate GIA-style pressure.":
        "Schnelles Vergleichen von Buchstabenpaaren unter GIA-typischem Zeitdruck.",
    "Find the number furthest from the median with speed and accuracy.":
        "Finden Sie schnell und genau die Zahl, die am weitesten vom mittleren Wert entfernt ist.",
    "Odd-one-out vocabulary sets backed by a curated word bank.":
        "Finden Sie das unpassende Wort in Dreiergruppen aus einer kuratierten Wortsammlung.",
    "Decide whether abstract shapes are rotated matches or mirrored variants.":
        "Entscheiden Sie, ob Figuren nur gedreht oder gespiegelt sind.",
    "Read the context statements first. Once you understand the relationship, reveal the question and choose the correct person or thing.":
        "Lesen Sie zuerst die Aussage. Wenn Sie die Beziehung verstanden haben, blenden Sie die Frage ein und wählen Sie die richtige Person.",
    "Look at the letter pairs carefully. Count the matching pairs quickly before selecting the correct number.":
        "Sehen Sie sich die Buchstabenpaare genau an. Zählen Sie schnell die übereinstimmenden Paare und wählen Sie dann die richtige Zahl.",
    "Review the three numbers, identify the middle value mentally, and choose the number furthest from it.":
        "Betrachten Sie die drei Zahlen, bestimmen Sie im Kopf den mittleren Wert und wählen Sie die Zahl, die am weitesten davon entfernt ist.",
    "Read the words shown in the context, spot the odd one out, and then choose it from the answer options.":
        "Lesen Sie die drei Wörter, finden Sie das unpassende Wort und wählen Sie es aus den Antworten aus.",
    "Study the shapes first, then decide whether they are the same when rotated or if one is mirrored.":
        "Betrachten Sie die Figuren und entscheiden Sie, ob sie gedreht gleich sind oder ob eine gespiegelt ist.",
    "Remember a comparison, then answer a question about the relationship without seeing the original statement.":
        "Merken Sie sich einen Vergleich und beantworten Sie dann eine Frage dazu, ohne die Aussage noch einmal zu sehen.",
    "Identify the people or things being compared.": "Erkennen Sie, wer miteinander verglichen wird.",
    "Restate the comparison in simpler words.": "Formulieren Sie den Vergleich in einfacheren Worten.",
    "Keep the direction of the relationship clear when the question appears.":
        "Behalten Sie die Richtung des Vergleichs im Kopf, wenn die Frage erscheint.",
    "Reversed or negative wording such as less careful instead of more careful.":
        "Umgedrehte oder verneinte Formulierungen wie „nicht so vorsichtig wie“ statt „vorsichtiger als“.",
    "Mentally place the stronger or greater item first before revealing the question.":
        "Stellen Sie sich die Person mit „mehr“ zuerst vor, bevor Sie die Frage einblenden.",
    "Compare the letter pairs and count how many are exact matches.":
        "Vergleichen Sie die Buchstabenpaare und zählen Sie, wie viele übereinstimmen.",
    "Scan the pairs from left to right.": "Gehen Sie die Paare von links nach rechts durch.",
    "Compare both characters in each pair.": "Vergleichen Sie in jedem Paar beide Buchstaben.",
    "Keep a running count and answer once the row is complete.":
        "Zählen Sie mit und antworten Sie, sobald die Reihe fertig ist.",
    "Do not count a pair when only one of its characters matches.":
        "Zählen Sie kein Paar, bei dem nur ein Buchstabe passt.",
    "Use a steady scan rhythm instead of repeatedly checking earlier pairs.":
        "Lesen Sie in gleichmäßigem Rhythmus, statt frühere Paare erneut zu prüfen.",
    "Find the middle value, then choose the number furthest away from it.":
        "Bestimmen Sie den mittleren Wert und wählen Sie die Zahl, die am weitesten davon entfernt ist.",
    "Order the three values from smallest to largest.": "Ordnen Sie die drei Zahlen der Größe nach.",
    "Identify the middle value.": "Bestimmen Sie den mittleren Wert.",
    "Compare the distance from the middle to both outer values.":
        "Vergleichen Sie den Abstand vom mittleren Wert zu den beiden äußeren Zahlen.",
    "The correct answer is not always the largest number.": "Die richtige Antwort ist nicht immer die größte Zahl.",
    "Ignore the middle value after identifying it and compare only the two gaps.":
        "Vergleichen Sie nach dem Bestimmen des mittleren Werts nur noch die beiden Abstände.",
    "Identify the word that does not belong with the others.": "Finden Sie das Wort, das nicht zu den anderen passt.",
    "Look for a meaning or category shared by most words.": "Suchen Sie die Bedeutung, die zwei Wörter gemeinsam haben.",
    "Test each word against that shared relationship.": "Prüfen Sie jedes Wort an dieser Gemeinsamkeit.",
    "Choose the word that falls outside the group.": "Wählen Sie das Wort, das aus der Reihe fällt.",
    "Do not choose a word only because it is less familiar.": "Wählen Sie ein Wort nicht nur, weil es weniger bekannt ist.",
    "Describe the shared group in one short phrase before selecting the odd word.":
        "Beschreiben Sie die Gemeinsamkeit in wenigen Worten, bevor Sie wählen.",
    "Decide whether two shapes are the same after rotation or whether one has been mirrored.":
        "Entscheiden Sie, ob zwei Figuren nach einer Drehung gleich sind oder ob eine gespiegelt wurde.",
    "Choose one distinctive corner, mark, or feature.": "Merken Sie sich eine markante Ecke oder ein Merkmal.",
    "Mentally rotate the first shape to align that feature.": "Drehen Sie die erste Figur im Kopf, bis das Merkmal übereinstimmt.",
    "Check whether the remaining features keep the same arrangement.":
        "Prüfen Sie, ob die übrigen Merkmale gleich angeordnet sind.",
    "A mirrored shape cannot be matched by rotation alone.": "Eine gespiegelte Figur lässt sich nicht allein durch Drehen zur Deckung bringen.",
    "Track an asymmetric feature rather than comparing the whole outline at once.":
        "Verfolgen Sie ein asymmetrisches Merkmal, statt die ganze Form auf einmal zu vergleichen.",
    "Five short timed sections": "Fünf kurze Abschnitte mit Zeitlimit",
    "Practice questions before each section": "Übungsfragen vor jedem Abschnitt",
    "Speed matters as much as accuracy": "Tempo zählt genauso viel wie Genauigkeit",
    # Practice page
    "The real test": "Der echte Test",
    "About the real test": "Über den echten Test",
    "Recommended way to prepare": "Empfohlene Vorbereitung",
    "Practice each section untimed and read the explanations": "Üben Sie jeden Abschnitt ohne Zeitlimit und lesen Sie die Erklärungen",
    "Take a timed test in your weakest section": "Machen Sie einen Zeittest in Ihrem schwächsten Abschnitt",
    "Finish with a full timed test": "Schließen Sie mit einem vollständigen Zeittest ab",
    "{n} section": "{n} Abschnitt",
    "{n} sections": "{n} Abschnitte",
    "{n} min": "{n} Min.",
    "Unlimited attempts": "Unbegrenzte Versuche",
    "{n} free attempt left": "Noch {n} kostenloser Versuch",
    "{n} free attempts left": "Noch {n} kostenlose Versuche",
    "Start full test": "Gesamttest starten",
    "{n} of {total} modules started": "{n} von {total} Modulen begonnen",
    "{n} free questions": "{n} kostenlose Fragen",
    "{n} solved": "{n} gelöst",
    "{n} test taken": "{n} Test absolviert",
    "{n} tests taken": "{n} Tests absolviert",
    "Completed": "Abgeschlossen",
    "In progress": "In Bearbeitung",
    "Not started": "Nicht begonnen",
    "Resume": "Fortsetzen",
    "Start": "Starten",
    "Language": "Sprache",
    "Beta": "Beta",
    "German and Spanish questions are new. Spotted a mistake? Use “Report a question issue” below any question.":
        "Die deutschen und spanischen Fragen sind neu. Fehler gefunden? Nutzen Sie „Problem mit der Frage melden“ unter jeder Frage.",
    # Section player (template and JS)
    "← Back to practice": "← Zurück zur Übersicht",
    "How this works": "So funktioniert es",
    "You're practicing as a guest, so progress lasts only for this visit.":
        "Sie üben als Gast, Ihr Fortschritt gilt daher nur für diesen Besuch.",
    "Sign in to save your progress": "Anmelden, um den Fortschritt zu speichern",
    "Loading": "Wird geladen",
    "Mode switch": "Modus wechseln",
    "Practice mode": "Übungsmodus",
    "Test mode": "Testmodus",
    "No timer. You'll see the answer and an explanation after each question.":
        "Ohne Zeitlimit. Nach jeder Frage sehen Sie die Lösung und eine Erklärung.",
    "Timed, like the real test. Opens fullscreen, and results are shown at the end.":
        "Mit Zeitlimit wie im echten Test. Läuft im Vollbild, das Ergebnis sehen Sie am Ende.",
    "Test": "Test",
    "Practice": "Übung",
    "Question {n} of {total}": "Frage {n} von {total}",
    "End test": "Test beenden",
    "Ready when you are": "Bereit, wenn Sie es sind",
    "We track your average time per question so you can compare your pace with the timed test.":
        "Wir messen Ihre durchschnittliche Zeit pro Frage, damit Sie Ihr Tempo mit dem Zeittest vergleichen können.",
    "Start practice": "Übung starten",
    "Enter fullscreen to begin": "Zum Starten in den Vollbildmodus wechseln",
    "The timer starts when the test opens fullscreen. You can't pause once it begins.":
        "Die Zeit läuft, sobald der Test im Vollbild startet. Danach können Sie nicht pausieren.",
    "Enter fullscreen and start": "Vollbild öffnen und starten",
    "Context": "Aussage",
    "Show question": "Frage anzeigen",
    "Question": "Frage",
    "Section complete": "Abschnitt abgeschlossen",
    "You have reached the end of this question set.": "Sie haben das Ende dieser Fragen erreicht.",
    "Refresh the page to practice this section again.": "Laden Sie die Seite neu, um diesen Abschnitt erneut zu üben.",
    "Leaving test mode": "Testmodus wird beendet",
    "Saving your progress and returning to practice...": "Ihr Fortschritt wird gespeichert, zurück zur Übung …",
    "Please wait a moment.": "Bitte warten Sie einen Moment.",
    "Free practice complete": "Kostenlose Übung abgeschlossen",
    "You have completed all {n} free questions for this module. Upgrade to continue practising.":
        "Sie haben alle {n} kostenlosen Fragen dieses Moduls bearbeitet. Mit einem Pass können Sie weiter üben.",
    "View plans": "Preise ansehen",
    "Timed tests are part of membership.": "Zeittests sind Teil der Mitgliedschaft.",
    "See membership": "Mitgliedschaft ansehen",
    "Ready": "Bereit",
    "Could not start test mode.": "Der Testmodus konnte nicht gestartet werden.",
    "Your session has expired. This answer was not saved.": "Ihre Sitzung ist abgelaufen. Diese Antwort wurde nicht gespeichert.",
    "This answer could not be saved. Check your connection before continuing; the dashboard may be incomplete.":
        "Diese Antwort konnte nicht gespeichert werden. Prüfen Sie Ihre Verbindung; die Übersicht ist eventuell unvollständig.",
    "Saving your section test result...": "Ergebnis des Abschnittstests wird gespeichert …",
    "Could not save the section test result.": "Das Ergebnis des Abschnittstests konnte nicht gespeichert werden.",
    "Fullscreen is required to start test mode.": "Für den Testmodus ist der Vollbildmodus erforderlich.",
    "You answered {correct} out of {total} correctly.": "Sie haben {correct} von {total} Fragen richtig beantwortet.",
    "Practice mode shows immediate feedback after each answer.": "Im Übungsmodus erhalten Sie nach jeder Antwort sofort eine Rückmeldung.",
    "Test mode finished without per-question feedback.": "Der Testmodus wurde ohne Rückmeldung zu einzelnen Fragen beendet.",
    "Final section score: {score}.": "Ergebnis des Abschnitts: {score}.",
    "{solved} of {total} practice questions solved": "{solved} von {total} Übungsfragen gelöst",
    "Correct.": "Richtig.",
    "Wrong: “{selected}” does not satisfy the rule.": "Falsch: „{selected}“ erfüllt die Bedingung nicht.",
    "The correct answer is {correct}.": "Die richtige Antwort ist {correct}.",
    "Option {n}": "Antwort {n}",
    "{minutes} minutes {seconds} seconds left": "Noch {minutes} Minuten {seconds} Sekunden",
    "Next question ": "Nächste Frage ",
    "Choose one answer.": "Wählen Sie eine Antwort.",
    "How many matching pairs are there?": "Wie viele Paare stimmen überein?",
    "How many pairs show the same image?": "Wie viele Paare zeigen dasselbe Bild?",
    "Count only pairs whose letters match apart from upper- and lower-case.":
        "Zählen Sie nur Paare, deren Buchstaben bis auf Groß- und Kleinschreibung gleich sind.",
    "Order the three values, identify the middle one, then compare each outer value's distance from it.":
        "Ordnen Sie die drei Zahlen, bestimmen Sie die mittlere und vergleichen Sie die Abstände der äußeren Zahlen.",
    "Find the relationship shared by two words; choose the third word that does not fit that relationship.":
        "Finden Sie die Gemeinsamkeit zweier Wörter und wählen Sie das dritte Wort, das nicht dazu passt.",
    "A figure can be rotated and still match, but a mirror image reverses its handedness.":
        "Eine gedrehte Figur kann übereinstimmen, ein Spiegelbild kehrt sie jedoch seitenverkehrt um.",
    "Use the comparison statement to determine the relationship before choosing the named person or thing.":
        "Klären Sie anhand der Aussage die Beziehung, bevor Sie eine Person wählen.",
    "Report a question issue": "Problem mit der Frage melden",
    "Issue type": "Art des Problems",
    "Ambiguous wording": "Missverständliche Formulierung",
    "Answer key": "Lösung",
    "Display problem": "Darstellungsproblem",
    "Other": "Sonstiges",
    "Describe the issue": "Beschreiben Sie das Problem",
    "Send issue for review": "Zur Prüfung senden",
    "Could not send the report. Sign in and retry.": "Die Meldung konnte nicht gesendet werden. Bitte melden Sie sich an und versuchen Sie es erneut.",
    "Saved for editorial review.": "Zur redaktionellen Prüfung gespeichert.",
    # Full test (template and JS)
    "Section": "Abschnitt",
    "Skip question": "Frage überspringen",
    "Section intro": "Einführung",
    "Enter fullscreen and start full test": "Vollbild öffnen und Gesamttest starten",
    "Timed test": "Zeittest",
    "The timed part of each section starts only after fullscreen mode is enabled.":
        "Der zeitgemessene Teil jedes Abschnitts beginnt erst im Vollbildmodus.",
    "Enter fullscreen and start test": "Vollbild öffnen und Test starten",
    "Leave test": "Test verlassen",
    "End the full test?": "Gesamttest beenden?",
    "Your score so far will be saved, and you will leave the current fullscreen session.":
        "Ihr bisheriges Ergebnis wird gespeichert und der Vollbildmodus beendet.",
    "Keep going": "Weitermachen",
    "Full test complete": "Gesamttest abgeschlossen",
    "You have completed all sections.": "Sie haben alle Abschnitte abgeschlossen.",
    "Refresh the page if you want to run the guided full test again.": "Laden Sie die Seite neu, um den Gesamttest erneut zu starten.",
    "Read the prompt, reveal the question, then move fast and stay accurate.":
        "Aussage lesen, Frage einblenden, dann schnell und genau antworten.",
    "The full test is not ready yet.": "Der Gesamttest ist noch nicht bereit.",
    "Full test is temporarily unavailable. Please try again in a moment.":
        "Der Gesamttest ist vorübergehend nicht verfügbar. Bitte versuchen Sie es gleich noch einmal.",
    "Section test is temporarily unavailable. Please try again in a moment.":
        "Der Abschnittstest ist vorübergehend nicht verfügbar. Bitte versuchen Sie es gleich noch einmal.",
    "Assessment": "Test",
    "Intro": "Einführung",
    "Could not load the current test section.": "Der aktuelle Testabschnitt konnte nicht geladen werden.",
    "Could not load the full test section.": "Der Abschnitt des Gesamttests konnte nicht geladen werden.",
    "Could not load {title}.": "{title} konnte nicht geladen werden.",
    "an assessment section": "ein Testabschnitt",
    "There was a problem loading the test question.": "Beim Laden der Frage ist ein Problem aufgetreten.",
    "Work quickly and accurately. Calculators are not permitted.": "Arbeiten Sie schnell und genau. Taschenrechner sind nicht erlaubt.",
    "Enter fullscreen and start {title}": "Vollbild öffnen und {title} starten",
    "Could not save the completed section.": "Der abgeschlossene Abschnitt konnte nicht gespeichert werden.",
    "Practice complete": "Übung abgeschlossen",
    "{title} practice complete": "Übung „{title}“ abgeschlossen",
    "Next, start the timed test for this section.": "Starten Sie nun den Zeittest für diesen Abschnitt.",
    "Start timed test": "Zeittest starten",
    "{title} test complete": "Test „{title}“ abgeschlossen",
    "Continue directly into the next section practice flow.": "Fahren Sie direkt mit der Übung des nächsten Abschnitts fort.",
    "Next section": "Nächster Abschnitt",
    "The test could not be loaded. Please try again.": "Der Test konnte nicht geladen werden. Bitte versuchen Sie es erneut.",
    "Fullscreen is required to start the full test.": "Für den Gesamttest ist der Vollbildmodus erforderlich.",
    "Fullscreen is required to start timed test mode.": "Für den Zeittest ist der Vollbildmodus erforderlich.",
    "Fullscreen is required to continue into the next section.": "Für den nächsten Abschnitt ist der Vollbildmodus erforderlich.",
    "Submission failed.": "Das Absenden ist fehlgeschlagen.",
    "Final score: {score}.": "Endergebnis: {score}.",
    "There was a problem submitting the test.": "Beim Absenden des Tests ist ein Problem aufgetreten.",
    "Avg {time}": "Ø {time}",
    "{n} questions": "{n} Fragen",
    "Adaptive": "Adaptiv",
    "Every section, back to back, in {minutes} minutes.": "Alle Abschnitte direkt hintereinander in {minutes} Minuten.",
    "Timed like the real test, with a score for every section at the end.":
        "Mit Zeitlimit wie im echten Test und mit einem Ergebnis für jeden Abschnitt am Ende.",
    "Timed like the real test, and the difficulty adjusts to your answers.":
        "Mit Zeitlimit wie im echten Test; der Schwierigkeitsgrad passt sich Ihren Antworten an.",
}

_ES = {
    # Assessment and module configuration
    "Thomas International GIA cognitive ability practice with timed tests and section-wise drills.":
        "Práctica para la prueba de aptitud cognitiva Thomas International GIA, con pruebas cronometradas y ejercicios por sección.",
    "Full test": "Prueba completa",
    "All five sections in one flow, designed to feel very close to the real GIA.":
        "Las cinco secciones seguidas, lo más parecido posible al GIA real.",
    "Each section is shown one by one. First you get instructions, then eight practice questions with instant feedback, then the timed test for that section.":
        "Las secciones aparecen una a una. Primero verá las instrucciones, luego ocho preguntas de práctica con corrección inmediata y después la prueba cronometrada de esa sección.",
    "Modules": "Módulos",
    "Reasoning": "Razonamiento",
    "Perceptual Speed": "Velocidad perceptiva",
    "Number Speed & Accuracy": "Números: velocidad y precisión",
    "Word Meaning": "Significado de palabras",
    "Spatial Visualization": "Visualización espacial",
    "Comparative and transitive logic questions under timed conditions.":
        "Preguntas de comparación y lógica con tiempo limitado.",
    "Fast letter-pair matching built to simulate GIA-style pressure.":
        "Comparación rápida de pares de letras con la presión de tiempo del GIA.",
    "Find the number furthest from the median with speed and accuracy.":
        "Encuentre con rapidez y precisión el número más alejado del valor intermedio.",
    "Odd-one-out vocabulary sets backed by a curated word bank.":
        "Encuentre la palabra que sobra en grupos de tres, de un banco de palabras seleccionado.",
    "Decide whether abstract shapes are rotated matches or mirrored variants.":
        "Decida si dos figuras son iguales tras girarlas o si una está reflejada.",
    "Read the context statements first. Once you understand the relationship, reveal the question and choose the correct person or thing.":
        "Lea primero la afirmación. Cuando entienda la relación, muestre la pregunta y elija a la persona correcta.",
    "Look at the letter pairs carefully. Count the matching pairs quickly before selecting the correct number.":
        "Observe los pares de letras con atención. Cuente rápidamente los pares que coinciden y elija el número correcto.",
    "Review the three numbers, identify the middle value mentally, and choose the number furthest from it.":
        "Mire los tres números, identifique mentalmente el valor intermedio y elija el número más alejado de él.",
    "Read the words shown in the context, spot the odd one out, and then choose it from the answer options.":
        "Lea las tres palabras, encuentre la que sobra y elíjala entre las respuestas.",
    "Study the shapes first, then decide whether they are the same when rotated or if one is mirrored.":
        "Observe las figuras y decida si son iguales al girarlas o si una está reflejada.",
    "Remember a comparison, then answer a question about the relationship without seeing the original statement.":
        "Memorice una comparación y responda después a una pregunta sobre ella sin volver a ver la afirmación.",
    "Identify the people or things being compared.": "Identifique a quién se compara.",
    "Restate the comparison in simpler words.": "Reformule la comparación con palabras más sencillas.",
    "Keep the direction of the relationship clear when the question appears.":
        "Tenga clara la dirección de la comparación cuando aparezca la pregunta.",
    "Reversed or negative wording such as less careful instead of more careful.":
        "Frases invertidas o negativas, como «no es tan cuidadoso como» en lugar de «es más cuidadoso que».",
    "Mentally place the stronger or greater item first before revealing the question.":
        "Ordene mentalmente primero a quien tiene «más» antes de mostrar la pregunta.",
    "Compare the letter pairs and count how many are exact matches.":
        "Compare los pares de letras y cuente cuántos coinciden.",
    "Scan the pairs from left to right.": "Recorra los pares de izquierda a derecha.",
    "Compare both characters in each pair.": "Compare las dos letras de cada par.",
    "Keep a running count and answer once the row is complete.": "Lleve la cuenta y responda al terminar la fila.",
    "Do not count a pair when only one of its characters matches.": "No cuente un par en el que solo coincide una letra.",
    "Use a steady scan rhythm instead of repeatedly checking earlier pairs.":
        "Mantenga un ritmo constante en lugar de volver a revisar los pares anteriores.",
    "Find the middle value, then choose the number furthest away from it.":
        "Encuentre el valor intermedio y elija el número más alejado de él.",
    "Order the three values from smallest to largest.": "Ordene los tres números de menor a mayor.",
    "Identify the middle value.": "Identifique el valor intermedio.",
    "Compare the distance from the middle to both outer values.":
        "Compare la distancia del valor intermedio a cada uno de los extremos.",
    "The correct answer is not always the largest number.": "La respuesta correcta no siempre es el número más grande.",
    "Ignore the middle value after identifying it and compare only the two gaps.":
        "Una vez identificado el valor intermedio, compare solo las dos diferencias.",
    "Identify the word that does not belong with the others.": "Identifique la palabra que no encaja con las demás.",
    "Look for a meaning or category shared by most words.": "Busque el significado que comparten dos de las palabras.",
    "Test each word against that shared relationship.": "Compruebe cada palabra con esa relación.",
    "Choose the word that falls outside the group.": "Elija la palabra que queda fuera del grupo.",
    "Do not choose a word only because it is less familiar.": "No elija una palabra solo porque le resulte menos conocida.",
    "Describe the shared group in one short phrase before selecting the odd word.":
        "Describa en pocas palabras qué tienen en común antes de elegir.",
    "Decide whether two shapes are the same after rotation or whether one has been mirrored.":
        "Decida si dos figuras son iguales tras girarlas o si una se ha reflejado.",
    "Choose one distinctive corner, mark, or feature.": "Fíjese en una esquina o un rasgo característico.",
    "Mentally rotate the first shape to align that feature.": "Gire mentalmente la primera figura hasta alinear ese rasgo.",
    "Check whether the remaining features keep the same arrangement.":
        "Compruebe si el resto de rasgos mantiene la misma disposición.",
    "A mirrored shape cannot be matched by rotation alone.": "Una figura reflejada no coincide solo con girarla.",
    "Track an asymmetric feature rather than comparing the whole outline at once.":
        "Siga un rasgo asimétrico en lugar de comparar toda la figura a la vez.",
    "Five short timed sections": "Cinco secciones breves cronometradas",
    "Practice questions before each section": "Preguntas de práctica antes de cada sección",
    "Speed matters as much as accuracy": "La velocidad cuenta tanto como la precisión",
    # Practice page
    "The real test": "La prueba real",
    "About the real test": "Sobre la prueba real",
    "Recommended way to prepare": "Preparación recomendada",
    "Practice each section untimed and read the explanations": "Practique cada sección sin tiempo y lea las explicaciones",
    "Take a timed test in your weakest section": "Haga una prueba cronometrada de su sección más débil",
    "Finish with a full timed test": "Termine con una prueba completa cronometrada",
    "{n} section": "{n} sección",
    "{n} sections": "{n} secciones",
    "{n} min": "{n} min",
    "Unlimited attempts": "Intentos ilimitados",
    "{n} free attempt left": "Le queda {n} intento gratuito",
    "{n} free attempts left": "Le quedan {n} intentos gratuitos",
    "Start full test": "Empezar prueba completa",
    "{n} of {total} modules started": "{n} de {total} módulos empezados",
    "{n} free questions": "{n} preguntas gratuitas",
    "{n} solved": "{n} resueltas",
    "{n} test taken": "{n} prueba realizada",
    "{n} tests taken": "{n} pruebas realizadas",
    "Completed": "Completado",
    "In progress": "En curso",
    "Not started": "Sin empezar",
    "Resume": "Continuar",
    "Start": "Empezar",
    "Language": "Idioma",
    "Beta": "Beta",
    "German and Spanish questions are new. Spotted a mistake? Use “Report a question issue” below any question.":
        "Las preguntas en alemán y español son nuevas. ¿Ha visto un error? Use «Informar de un problema» debajo de cualquier pregunta.",
    # Section player (template and JS)
    "← Back to practice": "← Volver a la práctica",
    "How this works": "Cómo funciona",
    "You're practicing as a guest, so progress lasts only for this visit.":
        "Está practicando como invitado, así que el progreso solo se guarda durante esta visita.",
    "Sign in to save your progress": "Inicie sesión para guardar su progreso",
    "Loading": "Cargando",
    "Mode switch": "Cambiar modo",
    "Practice mode": "Modo práctica",
    "Test mode": "Modo prueba",
    "No timer. You'll see the answer and an explanation after each question.":
        "Sin tiempo. Después de cada pregunta verá la respuesta y una explicación.",
    "Timed, like the real test. Opens fullscreen, and results are shown at the end.":
        "Con tiempo, como la prueba real. Se abre en pantalla completa y verá el resultado al final.",
    "Test": "Prueba",
    "Practice": "Práctica",
    "Question {n} of {total}": "Pregunta {n} de {total}",
    "End test": "Terminar prueba",
    "Ready when you are": "Cuando esté listo",
    "We track your average time per question so you can compare your pace with the timed test.":
        "Medimos su tiempo medio por pregunta para que pueda comparar su ritmo con la prueba cronometrada.",
    "Start practice": "Empezar práctica",
    "Enter fullscreen to begin": "Abra la pantalla completa para empezar",
    "The timer starts when the test opens fullscreen. You can't pause once it begins.":
        "El tiempo empieza a contar cuando la prueba se abre en pantalla completa. No se puede pausar.",
    "Enter fullscreen and start": "Pantalla completa y empezar",
    "Context": "Afirmación",
    "Show question": "Mostrar pregunta",
    "Question": "Pregunta",
    "Section complete": "Sección completada",
    "You have reached the end of this question set.": "Ha llegado al final de estas preguntas.",
    "Refresh the page to practice this section again.": "Recargue la página para volver a practicar esta sección.",
    "Leaving test mode": "Saliendo del modo prueba",
    "Saving your progress and returning to practice...": "Guardando su progreso y volviendo a la práctica…",
    "Please wait a moment.": "Espere un momento, por favor.",
    "Free practice complete": "Práctica gratuita completada",
    "You have completed all {n} free questions for this module. Upgrade to continue practising.":
        "Ha completado las {n} preguntas gratuitas de este módulo. Consiga un pase para seguir practicando.",
    "View plans": "Ver precios",
    "Timed tests are part of membership.": "Las pruebas cronometradas forman parte de la membresía.",
    "See membership": "Ver membresía",
    "Ready": "Listo",
    "Could not start test mode.": "No se pudo iniciar el modo prueba.",
    "Your session has expired. This answer was not saved.": "Su sesión ha caducado. Esta respuesta no se ha guardado.",
    "This answer could not be saved. Check your connection before continuing; the dashboard may be incomplete.":
        "No se pudo guardar esta respuesta. Compruebe su conexión; es posible que el panel esté incompleto.",
    "Saving your section test result...": "Guardando el resultado de la sección…",
    "Could not save the section test result.": "No se pudo guardar el resultado de la sección.",
    "Fullscreen is required to start test mode.": "El modo prueba requiere pantalla completa.",
    "You answered {correct} out of {total} correctly.": "Ha respondido bien {correct} de {total}.",
    "Practice mode shows immediate feedback after each answer.": "El modo práctica corrige cada respuesta al momento.",
    "Test mode finished without per-question feedback.": "El modo prueba ha terminado sin corrección pregunta a pregunta.",
    "Final section score: {score}.": "Puntuación de la sección: {score}.",
    "{solved} of {total} practice questions solved": "{solved} de {total} preguntas de práctica resueltas",
    "Correct.": "Correcto.",
    "Wrong: “{selected}” does not satisfy the rule.": "Incorrecto: «{selected}» no cumple la condición.",
    "The correct answer is {correct}.": "La respuesta correcta es {correct}.",
    "Option {n}": "Opción {n}",
    "{minutes} minutes {seconds} seconds left": "Quedan {minutes} minutos y {seconds} segundos",
    "Next question ": "Siguiente pregunta ",
    "Choose one answer.": "Elija una respuesta.",
    "How many matching pairs are there?": "¿Cuántos pares coinciden?",
    "How many pairs show the same image?": "¿Cuántos pares muestran la misma imagen?",
    "Count only pairs whose letters match apart from upper- and lower-case.":
        "Cuente solo los pares cuyas letras coinciden salvo por mayúsculas y minúsculas.",
    "Order the three values, identify the middle one, then compare each outer value's distance from it.":
        "Ordene los tres números, identifique el intermedio y compare la distancia de los extremos.",
    "Find the relationship shared by two words; choose the third word that does not fit that relationship.":
        "Encuentre la relación entre dos palabras y elija la tercera, que no encaja.",
    "A figure can be rotated and still match, but a mirror image reverses its handedness.":
        "Una figura girada puede coincidir, pero una imagen reflejada queda invertida.",
    "Use the comparison statement to determine the relationship before choosing the named person or thing.":
        "Use la afirmación para entender la relación antes de elegir a una persona.",
    "Report a question issue": "Informar de un problema",
    "Issue type": "Tipo de problema",
    "Ambiguous wording": "Redacción ambigua",
    "Answer key": "Respuesta correcta",
    "Display problem": "Problema de visualización",
    "Other": "Otro",
    "Describe the issue": "Describa el problema",
    "Send issue for review": "Enviar para revisión",
    "Could not send the report. Sign in and retry.": "No se pudo enviar el informe. Inicie sesión e inténtelo de nuevo.",
    "Saved for editorial review.": "Guardado para revisión editorial.",
    # Full test (template and JS)
    "Section": "Sección",
    "Skip question": "Saltar pregunta",
    "Section intro": "Introducción",
    "Enter fullscreen and start full test": "Pantalla completa y empezar la prueba completa",
    "Timed test": "Prueba cronometrada",
    "The timed part of each section starts only after fullscreen mode is enabled.":
        "La parte cronometrada de cada sección empieza solo en pantalla completa.",
    "Enter fullscreen and start test": "Pantalla completa y empezar la prueba",
    "Leave test": "Salir de la prueba",
    "End the full test?": "¿Terminar la prueba completa?",
    "Your score so far will be saved, and you will leave the current fullscreen session.":
        "Se guardará su puntuación hasta ahora y saldrá de la pantalla completa.",
    "Keep going": "Seguir",
    "Full test complete": "Prueba completa terminada",
    "You have completed all sections.": "Ha completado todas las secciones.",
    "Refresh the page if you want to run the guided full test again.": "Recargue la página si quiere volver a hacer la prueba completa.",
    "Read the prompt, reveal the question, then move fast and stay accurate.":
        "Lea la afirmación, muestre la pregunta y responda con rapidez y precisión.",
    "The full test is not ready yet.": "La prueba completa aún no está lista.",
    "Full test is temporarily unavailable. Please try again in a moment.":
        "La prueba completa no está disponible en este momento. Inténtelo de nuevo en unos instantes.",
    "Section test is temporarily unavailable. Please try again in a moment.":
        "La prueba de sección no está disponible en este momento. Inténtelo de nuevo en unos instantes.",
    "Assessment": "Prueba",
    "Intro": "Introducción",
    "Could not load the current test section.": "No se pudo cargar la sección actual.",
    "Could not load the full test section.": "No se pudo cargar la sección de la prueba completa.",
    "Could not load {title}.": "No se pudo cargar {title}.",
    "an assessment section": "una sección de la prueba",
    "There was a problem loading the test question.": "Hubo un problema al cargar la pregunta.",
    "Work quickly and accurately. Calculators are not permitted.": "Trabaje con rapidez y precisión. No se permiten calculadoras.",
    "Enter fullscreen and start {title}": "Pantalla completa y empezar {title}",
    "Could not save the completed section.": "No se pudo guardar la sección completada.",
    "Practice complete": "Práctica completada",
    "{title} practice complete": "Práctica de «{title}» completada",
    "Next, start the timed test for this section.": "Ahora empiece la prueba cronometrada de esta sección.",
    "Start timed test": "Empezar prueba cronometrada",
    "{title} test complete": "Prueba de «{title}» completada",
    "Continue directly into the next section practice flow.": "Continúe directamente con la práctica de la siguiente sección.",
    "Next section": "Siguiente sección",
    "The test could not be loaded. Please try again.": "No se pudo cargar la prueba. Inténtelo de nuevo.",
    "Fullscreen is required to start the full test.": "La prueba completa requiere pantalla completa.",
    "Fullscreen is required to start timed test mode.": "La prueba cronometrada requiere pantalla completa.",
    "Fullscreen is required to continue into the next section.": "Para pasar a la siguiente sección se requiere pantalla completa.",
    "Submission failed.": "No se pudo enviar.",
    "Final score: {score}.": "Puntuación final: {score}.",
    "There was a problem submitting the test.": "Hubo un problema al enviar la prueba.",
    "Avg {time}": "Media {time}",
    "{n} questions": "{n} preguntas",
    "Adaptive": "Adaptativa",
    "Every section, back to back, in {minutes} minutes.": "Todas las secciones seguidas en {minutes} minutos.",
    "Timed like the real test, with a score for every section at the end.":
        "Con tiempo, como la prueba real, y con una puntuación por sección al final.",
    "Timed like the real test, and the difficulty adjusts to your answers.":
        "Con tiempo, como la prueba real; la dificultad se adapta a sus respuestas.",
}

TRANSLATIONS = {"de": _DE, "es": _ES}


def is_localized(assessment_type: str | None) -> bool:
    return assessment_type in LOCALIZED_ASSESSMENTS


def normalize(language: str | None) -> str:
    return language if language in LANGUAGES else "en"


def request_language(request, assessment_type: str | None) -> str:
    """The student's chosen language for a localized test, remembered in the session.

    ``?lang=de`` / ``?lang=es`` / ``?lang=en`` switches it; tests that are not
    localized are always English.
    """
    if not is_localized(assessment_type):
        return "en"
    requested = request.GET.get("lang")
    if requested in LANGUAGES:
        request.session[SESSION_KEY] = requested
        return requested
    return normalize(request.session.get(SESSION_KEY))


def translate(text, language: str, **values) -> str:
    text = "" if text is None else str(text)
    translated = TRANSLATIONS.get(language, {}).get(text, text)
    if values:
        translated = re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), translated)
    return translated


def localize(value, language: str):
    """Deep copy of a config dict/list with every known English string translated."""
    if language == "en" or language not in TRANSLATIONS:
        return value
    table = TRANSLATIONS[language]
    if isinstance(value, str):
        return table.get(value, value)
    if isinstance(value, dict):
        return {key: localize(item, language) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(localize(item, language) for item in value)
    return copy.copy(value)


def localize_assessment(config: dict, language: str) -> dict:
    """Localize a runtime assessment config, including its computed sentences."""
    localized = localize(config, language)
    if language not in TRANSLATIONS or "full_test_question_total" not in config:
        return localized
    adaptive = config.get("full_test_adaptive", False)
    localized["full_test_meta_tail"] = translate("{n} questions", language, n=config["full_test_question_total"]) + (
        f" · {translate('Adaptive', language)}" if adaptive else ""
    )
    minutes = f"{config['full_test_duration_minutes']:g}"
    localized["full_test_description"] = " ".join([
        translate("Every section, back to back, in {minutes} minutes.", language, minutes=minutes),
        translate(
            "Timed like the real test, and the difficulty adjusts to your answers."
            if adaptive
            else "Timed like the real test, with a score for every section at the end.",
            language,
        ),
    ])
    return localized


def player_strings(language: str) -> dict[str, str]:
    """Translation table for the browser player; empty for English."""
    return dict(TRANSLATIONS.get(language, {}))


def language_links(request, current: str) -> list[dict]:
    """Links for the language switcher on localized test pages."""
    links = []
    for code, label in LANGUAGES.items():
        query = request.GET.copy()
        query["lang"] = code
        links.append({
            "code": code,
            "label": label,
            "beta": code in BETA_LANGUAGES,
            "current": code == current,
            "url": f"{request.path}?{query.urlencode()}",
        })
    return links
