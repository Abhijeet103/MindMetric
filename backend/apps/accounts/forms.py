from django import forms

from backend.apps.tenants.services import is_institution_tenant
from backend.apps.tenants.utils import get_default_tenant


from .models import AccountType


class CustomSignupForm(forms.Form):
    account_type = forms.ChoiceField(choices=AccountType.choices, initial=AccountType.STUDENT, required=False, label="I am joining as", help_text="Recruiters start with 100 free candidate credits.")
    first_name = forms.CharField(max_length=150, label="Name", required=True)

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.account_type = self.cleaned_data.get("account_type") or AccountType.STUDENT
        request_tenant = getattr(request, "tenant", None)
        if is_institution_tenant(request_tenant):
            request_tenant = None
        user.tenant = request_tenant or user.tenant or get_default_tenant()
        user.save(update_fields=["first_name", "tenant", "account_type"])
        if user.is_recruiter:
            from backend.apps.billing.recruiter_credits import grant_welcome_credits

            grant_welcome_credits(user)
