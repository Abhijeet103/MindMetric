"""``{% t %}``: translate interface text on localized test pages (Thomas GIA).

The English text is the key, so pages without ``ui_lang`` render unchanged.
``{% t "{n} section" plural="{n} sections" n=count %}`` picks the plural form
when ``n`` is not 1.
"""
from django import template

from backend.apps.assessments.i18n import translate

register = template.Library()


@register.simple_tag(takes_context=True)
def t(context, text, plural=None, **values):
    if plural is not None and values.get("n") != 1:
        text = plural
    return translate(text, context.get("ui_lang", "en"), **values)
