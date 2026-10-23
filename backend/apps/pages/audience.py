from __future__ import annotations

from backend.apps.accounts.models import User

from .models import AudienceContact


def upsert_audience_contact(
    *,
    email: str,
    source: str,
    tenant=None,
    user: User | None = None,
    full_name: str = "",
    marketing_opt_in: bool | None = None,
) -> AudienceContact:
    normalized_email = email.strip().lower()
    contact, created = AudienceContact.objects.get_or_create(
        email=normalized_email,
        defaults={
            "source": source,
            "tenant": tenant,
            "user": user,
            "full_name": full_name.strip(),
            "marketing_opt_in": bool(marketing_opt_in),
        },
    )
    if created:
        return contact

    updates: list[str] = []
    if tenant and contact.tenant_id is None:
        contact.tenant = tenant
        updates.append("tenant")
    if user and contact.user_id is None:
        contact.user = user
        updates.append("user")
    if full_name.strip() and not contact.full_name:
        contact.full_name = full_name.strip()
        updates.append("full_name")
    if marketing_opt_in is True and not contact.marketing_opt_in:
        contact.marketing_opt_in = True
        contact.unsubscribed_at = None
        updates.extend(("marketing_opt_in", "unsubscribed_at"))
    if updates:
        updates.append("updated_at")
        contact.save(update_fields=updates)
    return contact
