import logging

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.mail import get_connection
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone

from backend.apps.accounts.gifts import grant_one_month_gift, send_one_month_gift_email
from backend.apps.accounts.models import User
from backend.apps.tenants.admin_mixins import TenantScopedAdminMixin

from .models import AdminEmail, AudienceContact, PortalFeedback, SaleInquiry, TestSuggestion
from .emails import build_branded_email, campaign_email_initial

logger = logging.getLogger(__name__)


class MarketingEmailForm(forms.Form):
    subject = forms.CharField(max_length=180)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 14}))


class DirectEmailForm(MarketingEmailForm):
    recipient = forms.EmailField()


def compose_email(model_admin, request, inquiry=None):
    initial = {"recipient": inquiry.email, "subject": "Re: Your MindMetric sales enquiry"} if inquiry else {}
    form = DirectEmailForm(request.POST if request.method == "POST" else None, initial=initial)
    if inquiry:
        form.fields["recipient"].disabled = True
    cancel_url = reverse("admin:pages_saleinquiry_change", args=[inquiry.pk]) if inquiry else reverse("admin:pages_adminemail_changelist")
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            count = build_branded_email(
                subject=data["subject"], body=data["body"],
                recipient=data["recipient"],
            ).send(fail_silently=False)
            if count != 1:
                raise RuntimeError("Email backend did not accept the message")
        except Exception:
            form.add_error(None, "The email service did not confirm sending. Check your email configuration before retrying; your message has been preserved.")
        else:
            AdminEmail.objects.create(**data, inquiry=inquiry, sent_by=request.user)
            if inquiry:
                inquiry.contacted_back = True
                inquiry.contacted_at = timezone.now()
                if inquiry.status == SaleInquiry.Status.NEW:
                    inquiry.status = SaleInquiry.Status.CONTACTED
                inquiry.save(update_fields=("contacted_back", "contacted_at", "status", "updated_at"))
            model_admin.message_user(request, "Email accepted by the configured email service and saved in sent history.", messages.SUCCESS)
            return redirect(cancel_url)
    return render(request, "admin/pages/compose_email.html", {
        **model_admin.admin_site.each_context(request),
        "opts": model_admin.model._meta, "form": form, "inquiry": inquiry,
        "title": "Reply to sales enquiry" if inquiry else "Send email",
        "cancel_url": cancel_url, "sender": settings.DEFAULT_FROM_EMAIL,
    })


@admin.register(AdminEmail)
class AdminEmailAdmin(admin.ModelAdmin):
    list_display = ("recipient", "subject", "inquiry", "sent_by", "sent_at")
    search_fields = ("recipient", "subject", "body")
    readonly_fields = ("recipient", "subject", "body", "inquiry", "sent_by", "sent_at")
    change_list_template = "admin/pages/adminemail/change_list.html"

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def add_view(self, request, form_url="", extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied
        return compose_email(self, request)


class InquiryReplyInline(admin.StackedInline):
    model = AdminEmail
    fields = ("recipient", "subject", "body", "sent_by", "sent_at")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        allowed = request.user.has_perm("pages.view_saleinquiry") or request.user.has_perm("pages.change_saleinquiry")
        return bool(allowed and request.user.tenant_id and (obj is None or request.user.tenant_id == obj.tenant_id))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        if not request.user.tenant_id:
            return queryset.none()
        return queryset.filter(inquiry__tenant_id=request.user.tenant_id)


@admin.register(AudienceContact)
class AudienceContactAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "full_name",
        "source",
        "tenant",
        "marketing_opt_in",
        "unsubscribed_at",
        "last_campaign_sent_at",
        "updated_at",
    )
    list_filter = ("marketing_opt_in", "source", "tenant", "updated_at")
    search_fields = ("email", "full_name")
    readonly_fields = ("created_at", "updated_at", "last_campaign_sent_at")
    change_list_template = "admin/pages/audiencecontact/change_list.html"
    actions = (
        "send_product_update",
        "send_feedback_request",
        "send_marketing_email",
        "gift_one_month_access",
        "subscribe_selected_contacts",
        "unsubscribe_selected_contacts",
    )

    def has_module_permission(self, request):
        return bool(request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def get_urls(self):
        return [
            path("email/<str:kind>/", self.admin_site.admin_view(self.email_everyone_view),
                 name="pages_audiencecontact_email_everyone"),
        ] + super().get_urls()

    def email_everyone_view(self, request, kind):
        if not request.user.is_superuser:
            raise PermissionDenied
        if kind not in {"product_update", "feedback_request"}:
            raise Http404
        return self.campaign_view(request, self.get_queryset(request), kind, everyone=True)

    @admin.action(description="Send MindMetric updates / new tests to selected subscribed contacts")
    def send_product_update(self, request, queryset):
        return self.campaign_view(request, queryset, "product_update")

    @admin.action(description="Request feedback from selected subscribed contacts")
    def send_feedback_request(self, request, queryset):
        return self.campaign_view(request, queryset, "feedback_request")

    @admin.action(description="Send marketing email to selected subscribed contacts")
    def send_marketing_email(self, request, queryset):
        return self.campaign_view(request, queryset, "marketing_email")

    def campaign_view(self, request, queryset, kind, *, everyone=False):
        if not request.user.is_superuser:
            raise PermissionDenied
        recipients = queryset.filter(marketing_opt_in=True, unsubscribed_at__isnull=True)
        titles = {
            "product_update": "Send MindMetric updates and new tests",
            "feedback_request": "Request MindMetric feedback",
            "marketing_email": "Send marketing email",
        }
        form = MarketingEmailForm(
            request.POST if "send_campaign" in request.POST else None,
            initial=campaign_email_initial(kind),
        )
        cancel_url = reverse("admin:pages_audiencecontact_changelist")
        valid = "send_campaign" in request.POST and form.is_valid()
        if (
            valid and kind == "product_update"
            and "[Add the new tests, features, or improvements here before sending.]" in form.cleaned_data["body"]
        ):
            form.add_error("body", "Replace the placeholder with your new tests or features before sending.")
            valid = False
        if valid:
            if not recipients.exists():
                self.message_user(request, "No subscribed contacts were selected; no email was sent.", messages.WARNING)
                return redirect(cancel_url)
            sent = failed = 0
            # Individual sends let us record only confirmed messages and continue
            # after one recipient fails, without exposing anyone else's address.
            connection = get_connection(fail_silently=False)
            try:
                connection.open()
                for contact in recipients.iterator():
                    try:
                        count = build_branded_email(
                            subject=form.cleaned_data["subject"],
                            body=form.cleaned_data["body"],
                            recipient=contact.email,
                            connection=connection,
                        ).send(fail_silently=False)
                        if count != 1:
                            raise RuntimeError("Email backend did not accept the message")
                    except Exception:
                        failed += 1
                        logger.exception("Campaign email failed for contact=%s", contact.pk)
                        continue
                    sent += 1
                    AudienceContact.objects.filter(pk=contact.pk).update(last_campaign_sent_at=timezone.now())
                    AdminEmail.objects.create(
                        recipient=contact.email, sent_by=request.user, **form.cleaned_data,
                    )
            except Exception:
                logger.exception("Campaign email service failed")
                form.add_error(None, "The email service failed. Check sent history before retrying; your message has been preserved.")
            else:
                self.message_user(
                    request,
                    f"Email service accepted {sent} email(s); failed for {failed} subscribed contact(s).",
                    level=messages.SUCCESS if sent and not failed else messages.WARNING,
                )
                return redirect(cancel_url)
            finally:
                connection.close()

        return render(request, "admin/pages/audiencecontact/send_marketing_email.html", {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": titles[kind],
            "recipient_count": recipients.count(),
            "selected_ids": request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
            "form": form,
            "everyone": everyone,
            "select_across": request.POST.get("select_across", "0"),
            "action_name": "send_" + kind,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "cancel_url": cancel_url,
        })

    @admin.action(description="Gift one month of paid trial access to selected subscribed contacts")
    def gift_one_month_access(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only a superuser can gift paid access.", level=messages.ERROR)
            return None

        contacts = list(queryset.filter(marketing_opt_in=True, unsubscribed_at__isnull=True).select_related("user"))
        account_by_email = {
            user.email.lower(): user
            for user in User.objects.filter(
                email__in=[contact.email for contact in contacts],
                is_active=True,
            )
        }
        recipients = []
        for contact in contacts:
            user = contact.user if contact.user and contact.user.is_active else account_by_email.get(contact.email.lower())
            if user:
                recipients.append((contact, user))

        if "grant_gifts" in request.POST:
            granted = email_sent = email_failed = 0
            for _contact, user in recipients:
                expiry = grant_one_month_gift(user)
                granted += 1
                try:
                    if send_one_month_gift_email(email=user.email, first_name=user.first_name, expires_at=expiry):
                        email_sent += 1
                    else:
                        email_failed += 1
                except Exception:
                    email_failed += 1
                    logger.exception("Failed to send paid-access gift email to user=%s", user.pk)

            skipped = len(contacts) - len(recipients)
            level = messages.SUCCESS if not email_failed and not skipped else messages.WARNING
            self.message_user(
                request,
                f"Gifted one month of paid trial access to {granted} account(s). "
                f"Email sent to {email_sent}; failed for {email_failed}; skipped {skipped} contact(s) "
                "without an active account or marketing consent.",
                level=level,
            )
            return None

        return render(
            request,
            "admin/pages/audiencecontact/gift_access.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": "Gift one month of paid trial access",
                "contacts": [contact for contact, _user in recipients],
                "recipient_count": len(recipients),
                "skipped_count": len(queryset) - len(recipients),
                "action_name": "gift_one_month_access",
                "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
                "cancel_url": reverse("admin:pages_audiencecontact_changelist"),
            },
        )

    @admin.action(description="Opt in selected contacts to marketing", permissions=["change"])
    def subscribe_selected_contacts(self, request, queryset):
        updated = queryset.update(
            marketing_opt_in=True, unsubscribed_at=None, updated_at=timezone.now(),
        )
        self.message_user(request, f"Opted {updated} contact(s) in to marketing.", messages.SUCCESS)

    @admin.action(description="Opt out selected contacts from marketing", permissions=["change"])
    def unsubscribe_selected_contacts(self, request, queryset):
        updated = queryset.filter(marketing_opt_in=True).update(
            marketing_opt_in=False,
            unsubscribed_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Unsubscribed {updated} contact(s) from marketing.",
            level=messages.SUCCESS,
        )


@admin.register(SaleInquiry)
class SaleInquiryAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    change_form_template = "admin/pages/saleinquiry/change_form.html"
    inlines = (InquiryReplyInline,)

    def get_urls(self):
        return [path("<int:object_id>/reply/", self.admin_site.admin_view(self.reply_view), name="pages_saleinquiry_reply")] + super().get_urls()

    def reply_view(self, request, object_id):
        inquiry = get_object_or_404(self.get_queryset(request), pk=object_id)
        if not self.has_change_permission(request, inquiry):
            raise PermissionDenied
        return compose_email(self, request, inquiry)

    list_display = ("tenant", "full_name", "email", "phone", "marketing_opt_in", "source_page", "status", "contacted_back", "created_at")
    list_filter = ("contacted_back", "status", "marketing_opt_in", "source_page", "created_at")
    search_fields = ("full_name", "email", "phone", "message")
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "tenant",
        "full_name",
        "email",
        "phone",
        "source_page",
        "status",
        "message",
        "marketing_opt_in",
        "notes",
        "contacted_back",
        "contacted_at",
        "created_at",
        "updated_at",
    )


@admin.register(TestSuggestion)
class TestSuggestionAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    list_display = ("tenant", "requested_test", "email", "source_page", "status", "created_at")
    list_filter = ("status", "source_page", "created_at")
    search_fields = ("requested_test", "email", "message", "notes")
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "tenant",
        "user",
        "email",
        "requested_test",
        "source_page",
        "status",
        "message",
        "notes",
        "created_at",
        "updated_at",
    )


@admin.register(PortalFeedback)
class PortalFeedbackAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    list_display = ("created_at", "category", "email", "source_page", "tenant", "status")
    list_filter = ("status", "category", "tenant", "created_at")
    search_fields = ("email", "message", "source_page", "user__first_name", "user__last_name")
    readonly_fields = ("user", "email", "message", "source_page", "context", "created_at")
    fields = ("tenant", "user", "email", "category", "message", "source_page", "context", "status", "created_at")


from .models import ApplicationDeadline, EmployerAssessment, LegalPage  # noqa: E402


@admin.register(EmployerAssessment)
class EmployerAssessmentAdmin(admin.ModelAdmin):
    list_display = ("company", "industry", "assessment_types", "verified_on", "is_published")
    list_filter = ("is_published", "industry")
    search_fields = ("company", "industry")


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "effective_date", "is_published", "updated_at")


@admin.register(ApplicationDeadline)
class ApplicationDeadlineAdmin(admin.ModelAdmin):
    list_display = ("company", "user", "assessment_type", "due_date", "reminder_sent_at")
    search_fields = ("company", "user__email")
    raw_id_fields = ("user",)
