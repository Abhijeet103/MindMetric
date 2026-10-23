from django.db.models.signals import post_save
from django.dispatch import receiver

from backend.apps.accounts.models import User
from backend.apps.assessments.models import AssessmentTrackWaitlistEntry
from backend.apps.tenants.models import TenantStudentInvite

from .audience import upsert_audience_contact
from .models import SaleInquiry, TestSuggestion


@receiver(post_save, sender=User)
def collect_user_email(sender, instance: User, **kwargs):
    upsert_audience_contact(
        email=instance.email,
        source="user_account",
        tenant=instance.tenant,
        user=instance,
        full_name=instance.get_full_name(),
    )


@receiver(post_save, sender=SaleInquiry)
def collect_sales_inquiry_email(sender, instance: SaleInquiry, **kwargs):
    upsert_audience_contact(
        email=instance.email,
        source="sales_inquiry",
        tenant=instance.tenant,
        full_name=instance.full_name,
        marketing_opt_in=instance.marketing_opt_in,
    )


@receiver(post_save, sender=TestSuggestion)
def collect_test_suggestion_email(sender, instance: TestSuggestion, **kwargs):
    upsert_audience_contact(
        email=instance.email,
        source="test_suggestion",
        tenant=instance.tenant,
        user=instance.user,
    )


@receiver(post_save, sender=AssessmentTrackWaitlistEntry)
def collect_waitlist_email(sender, instance: AssessmentTrackWaitlistEntry, **kwargs):
    upsert_audience_contact(
        email=instance.email,
        source="assessment_waitlist",
        tenant=instance.tenant,
        user=instance.user,
    )


@receiver(post_save, sender=TenantStudentInvite)
def collect_institution_invite_email(sender, instance: TenantStudentInvite, **kwargs):
    upsert_audience_contact(
        email=instance.email,
        source="institution_invite",
        tenant=instance.tenant,
        user=instance.accepted_by,
        full_name=instance.full_name,
    )
