from django.db import migrations

from prepgia import gia_languages
from prepgia.word_banks import fr as french_bank

FRENCH_LABEL = "Français (Beta)"


def seed_french(apps, schema_editor):
    alias = schema_editor.connection.alias
    WordMeaningItem = apps.get_model("assessments", "WordMeaningItem")
    AssessmentTrack = apps.get_model("assessments", "AssessmentTrack")
    items = WordMeaningItem.objects.using(alias)
    suffix = gia_languages.WORD_MEANING_ODD_SUFFIX["fr"]
    for first, second, difficulty, relationship, explanation, odd_words in french_bank.WORD_CONCEPTS:
        for odd in odd_words:
            items.get_or_create(
                language="fr", pair_word_1=first, pair_word_2=second, odd_word=odd, difficulty=difficulty,
                defaults={
                    "relationship_type": relationship,
                    "explanation": explanation + suffix.format(odd=odd),
                    "tags": ["original", "beta", "lang-fr", "2026-11"],
                },
            )
    for track in AssessmentTrack.objects.using(alias).filter(assessment_type="prepgia"):
        languages = list(track.available_languages or [])
        if FRENCH_LABEL not in languages:
            languages.append(FRENCH_LABEL)
            track.available_languages = languages
            track.save(update_fields=["available_languages"])


def remove_french(apps, schema_editor):
    alias = schema_editor.connection.alias
    apps.get_model("assessments", "WordMeaningItem").objects.using(alias).filter(language="fr").delete()
    for track in apps.get_model("assessments", "AssessmentTrack").objects.using(alias).filter(assessment_type="prepgia"):
        if FRENCH_LABEL in (track.available_languages or []):
            track.available_languages = [lang for lang in track.available_languages if lang != FRENCH_LABEL]
            track.save(update_fields=["available_languages"])


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0027_release_mindmetric_practice"),
    ]

    operations = [
        migrations.RunPython(seed_french, remove_french),
    ]
