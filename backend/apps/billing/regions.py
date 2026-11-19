from __future__ import annotations

import ipaddress
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

COUNTRY_SESSION_KEY = "billing_country_code"

# Pricing regions. Each region has a shared price row in the admin under its
# code (EU, EE, LA, IN, GB); an exact country row (CA, MX, PL, CH, ...) takes
# precedence over its region's row. Everything else pays the base USD plan.
WESTERN_EUROPE_COUNTRY_CODES = frozenset(
    {
        "AD", "AT", "AX", "BE", "CH", "DE", "DK", "ES", "FI", "FO",
        "FR", "GG", "GI", "IE", "IM", "IS", "IT", "JE", "LI", "LU",
        "MC", "MT", "NL", "NO", "PT", "SE", "SM", "VA",
    }
)
# Rest of Europe: central, eastern and south-eastern Europe, priced lower.
OTHER_EUROPE_COUNTRY_CODES = frozenset(
    {
        "AL", "BA", "BG", "BY", "CY", "CZ", "EE", "GR", "HR", "HU",
        "LT", "LV", "MD", "ME", "MK", "PL", "RO", "RS", "SI", "SK",
        "UA", "XK",
    }
)
EUROPEAN_COUNTRY_CODES = WESTERN_EUROPE_COUNTRY_CODES | OTHER_EUROPE_COUNTRY_CODES
LATIN_AMERICA_COUNTRY_CODES = frozenset(
    {
        "AR", "BO", "BR", "BZ", "CL", "CO", "CR", "CU", "DO", "EC",
        "GT", "GY", "HN", "HT", "JM", "MX", "NI", "PA", "PE", "PY",
        "SR", "SV", "TT", "UY", "VE",
    }
)

# Currency a visitor's prices are shown in when the admin has set up that
# country's or region's price row. Anything not listed is shown in USD.
COUNTRY_DISPLAY_CURRENCIES = {
    "GB": "GBP", "CH": "CHF", "CA": "CAD", "MX": "MXN", "PL": "PLN",
    "CZ": "CZK", "HU": "HUF", "SE": "SEK", "NO": "NOK", "DK": "DKK",
}
REGION_DISPLAY_CURRENCIES = {"EU": "EUR", "EE": "EUR"}


def normalize_country_code(value: str | None) -> str | None:
    country_code = (value or "").strip().upper()
    if len(country_code) == 2 and country_code.isalpha():
        return country_code
    return None


def pricing_region_for_country(country_code: str | None) -> str:
    country_code = normalize_country_code(country_code)
    if country_code == "IN":
        return "IN"
    if country_code == "GB":
        return "GB"
    if country_code in WESTERN_EUROPE_COUNTRY_CODES:
        return "EU"
    if country_code in OTHER_EUROPE_COUNTRY_CODES:
        return "EE"
    if country_code in LATIN_AMERICA_COUNTRY_CODES:
        return "LA"
    return "US"


def price_override_codes(country_code: str | None) -> tuple[str, ...]:
    """Admin price rows to try for a country, most specific first."""
    country_code = normalize_country_code(country_code)
    region = pricing_region_for_country(country_code)
    codes = []
    if country_code and country_code != "US":
        codes.append(country_code)
    if region != "US" and region not in codes:
        codes.append(region)
    return tuple(codes)


def display_currency_for_country(country_code: str | None) -> str:
    country_code = normalize_country_code(country_code)
    if country_code in COUNTRY_DISPLAY_CURRENCIES:
        return COUNTRY_DISPLAY_CURRENCIES[country_code]
    return REGION_DISPLAY_CURRENCIES.get(pricing_region_for_country(country_code), "USD")


def _country_from_proxy_header(request) -> str | None:
    if not settings.BILLING_TRUST_PROXY_COUNTRY_HEADERS:
        return None
    for header in settings.BILLING_COUNTRY_HEADERS:
        country_code = normalize_country_code(request.META.get(header))
        if country_code:
            return country_code
    return None


def _request_ip(request) -> str | None:
    raw_ip = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
    if not raw_ip:
        return None
    try:
        address = ipaddress.ip_address(raw_ip.strip())
    except ValueError:
        return None
    if not address.is_global:
        return None
    return str(address)


def _lookup_ip_country(ip_address: str) -> str | None:
    url_template = settings.BILLING_IP_COUNTRY_LOOKUP_URL
    if not url_template:
        return None
    request = Request(
        url_template.format(ip=ip_address),
        headers={"Accept": "application/json,text/plain", "User-Agent": "MindMetric/1.0"},
    )
    try:
        with urlopen(request, timeout=settings.BILLING_IP_COUNTRY_LOOKUP_TIMEOUT) as response:
            raw_value = response.read().decode("utf-8").strip()
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        logger.info("Country lookup failed for billing request: %s", exc)
        return None

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return normalize_country_code(raw_value)
    if isinstance(payload, dict):
        return normalize_country_code(
            payload.get("country_code") or payload.get("country")
        )
    return None


def _country_from_accept_language(request) -> str | None:
    for language in request.META.get("HTTP_ACCEPT_LANGUAGE", "").split(","):
        locale = language.split(";", 1)[0].strip().replace("_", "-")
        if "-" not in locale:
            continue
        country_code = normalize_country_code(locale.rsplit("-", 1)[-1])
        if country_code:
            return country_code
    return None


def detect_request_country_code(request) -> str | None:
    """Network-derived country without pricing's US fallback or language inference."""
    if "detected_country_code" in request.session:
        return normalize_country_code(request.session["detected_country_code"])
    country = _country_from_proxy_header(request)
    if not country:
        address = _request_ip(request)
        country = _lookup_ip_country(address) if address else None
    request.session["detected_country_code"] = country or ""
    return country


def get_request_country_code(request) -> str:
    saved_country = normalize_country_code(request.session.get(COUNTRY_SESSION_KEY))
    if saved_country:
        return saved_country

    country_code = _country_from_proxy_header(request)
    if not country_code:
        request_ip = _request_ip(request)
        country_code = _lookup_ip_country(request_ip) if request_ip else None
    if not country_code:
        country_code = _country_from_accept_language(request)
    country_code = country_code or "US"
    request.session[COUNTRY_SESSION_KEY] = country_code
    return country_code
