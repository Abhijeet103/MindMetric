from __future__ import annotations

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from backend.apps.accounts.models import AccountType
from backend.apps.tenants.auth import bind_session_to_tenant
from backend.apps.tenants.services import get_or_create_tenant_user, is_institution_tenant
from backend.apps.tenants.utils import get_default_tenant


class TenantAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        tenant = getattr(request, "tenant", None)
        bind_session_to_tenant(request, tenant)
        if tenant and request.user.is_authenticated:
            get_or_create_tenant_user(tenant=tenant, user=request.user)
        from backend.apps.pages.recruiter import prefers_recruiter_workspace

        if request.user.is_authenticated and prefers_recruiter_workspace(request):
            return "/recruiter/"
        return super().get_login_redirect_url(request)

    def get_signup_redirect_url(self, request):
        bind_session_to_tenant(request)
        if request.user.is_authenticated and request.user.is_recruiter:
            return "/recruiter/"
        return super().get_signup_redirect_url(request)


class TenantSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        tenant = getattr(request, "tenant", None)
        if user.tenant_id is None:
            # Institutional access is represented by TenantMembership, not by
            # changing the user's home/platform tenant.
            user.tenant = get_default_tenant() if is_institution_tenant(tenant) else tenant or get_default_tenant()
            user.save(update_fields=["tenant"])
        # A brand-new account created from the recruiter sign-in becomes a recruiter,
        # the same as choosing "Recruiter" on the email signup form.
        next_url = (getattr(sociallogin, "state", None) or {}).get("next") or ""
        if next_url.startswith("/recruiter/") and not user.is_recruiter:
            user.account_type = AccountType.RECRUITER
            user.save(update_fields=["account_type"])
            from backend.apps.billing.recruiter_credits import grant_welcome_credits

            grant_welcome_credits(user)
        return user
