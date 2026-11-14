from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import urlparse

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from backend.apps.assessments.config import ASSESSMENT_CONFIG, PRACTICE_TRACK_LIBRARY
from backend.apps.pages.models import LegalPage
from backend.apps.pages.guides import iter_assessment_guides, iter_module_guides
from backend.apps.pages.seo import canonical_site_url


def _published_legal_slugs() -> list[str]:
    try:
        return list(LegalPage.objects.filter(is_published=True).values_list("slug", flat=True))
    except Exception:  # No database available (e.g. database-free tests).
        return []


class PublicPageSitemap(Sitemap):
    def get_urls(self, page=1, site=None, protocol=None):
        parsed_site_url = urlparse(canonical_site_url())
        canonical_site = SimpleNamespace(domain=parsed_site_url.netloc)
        return super().get_urls(
            page=page,
            site=canonical_site,
            protocol=parsed_site_url.scheme,
        )

    def items(self):
        pages = [
            ("pages:home", ()),
            ("pages:pricing", ()),
            ("pages:practice", ()),
            ("pages:company-lookup", ()),
        ]
        for assessment_slug, assessment in ASSESSMENT_CONFIG.items():
            track = PRACTICE_TRACK_LIBRARY.get(assessment_slug, {})
            if not track.get("route_enabled"):
                continue
            pages.append(("pages:assessment-practice", (assessment_slug,)))
            pages.extend(
                (
                    "pages:assessment-section-detail",
                    (assessment_slug, str(module["key"])),
                )
                for module in assessment["modules"]
            )
        pages.extend(
            ("pages:assessment-guide", (guide["slug"],))
            for guide in iter_assessment_guides()
        )
        pages.extend(
            ("pages:module-guide", (assessment_slug, module_slug))
            for assessment_slug, module_slug in iter_module_guides()
        )
        pages.extend(("pages:legal-page", (slug,)) for slug in _published_legal_slugs())
        return pages

    def location(self, item):
        route_name, args = item
        return reverse(route_name, args=args)

    def changefreq(self, item):
        route_name, _ = item
        if route_name == "pages:home":
            return "daily"
        if route_name == "pages:legal-page":
            return "yearly"
        return "weekly"

    def priority(self, item):
        route_name, _ = item
        priorities = {
            "pages:home": 1.0,
            "pages:practice": 0.9,
            "pages:assessment-practice": 0.8,
            "pages:assessment-section-detail": 0.7,
            "pages:assessment-guide": 0.85,
            "pages:module-guide": 0.75,
            "pages:pricing": 0.5,
            "pages:company-lookup": 0.6,
            "pages:legal-page": 0.2,
        }
        return priorities.get(route_name, 0.5)
