from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.mail import EmailMessage, get_connection
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone

from backend.apps.tenants.admin_mixins import TenantScopedAdminMixin

from .models import AdminEmail, AudienceContact, SaleInquiry, TestSuggestion


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
            count = EmailMessage(
                subject=data["subject"], body=data["body"],
                from_email=settings.DEFAULT_FROM_EMAIL, to=[data["recipient"]],
            ).send(fail_silently=False)
            if count != 1:
                raise RuntimeError("Email backend did not accept the message")
        except Exception:
            form.add_error(None, "The email service did not confirm sending. Check your email configuration before retrying; your message has been preserved.")
        else:
            AdminEmail.objects.create(**data, inquiry=inquiry, sent_by=request.user)
            if inquiry:
                inquiry.contacted_at = timezone.now()
                if inquiry.status == SaleInquiry.Status.NEW:
                    inquiry.status = SaleInquiry.Status.CONTACTED
                inquiry.save(update_fields=("contacted_at", "status", "updated_at"))
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
    actions = ("send_marketing_email", "unsubscribe_selected_contacts")

    def has_module_permission(self, request):
        return bool(request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    @admin.action(description="Send marketing email to selected subscribed contacts")
    def send_marketing_email(self, request, queryset):
        recipients = queryset.filter(marketing_opt_in=True, unsubscribed_at__isnull=True)
        if "send_campaign" in request.POST:
            form = MarketingEmailForm(request.POST)
            if form.is_valid():
                recipient_list = list(recipients)
                if not recipient_list:
                    self.message_user(
                        request,
                        "No subscribed contacts were selected; no email was sent.",
                        level=messages.WARNING,
                    )
                    return None
                connection = get_connection(fail_silently=False)
                email_messages = [
                    EmailMessage(
                        subject=form.cleaned_data["subject"],
                        body=form.cleaned_data["body"],
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[contact.email],
                        connection=connection,
                    )
                    for contact in recipient_list
                ]
                connection.send_messages(email_messages)
                recipients.update(last_campaign_sent_at=timezone.now())
                self.message_user(
                    request,
                    f"Sent the marketing email to {len(recipient_list)} subscribed contact(s).",
                    level=messages.SUCCESS,
                )
                return None
        else:
            form = MarketingEmailForm()

        return render(
            request,
            "admin/pages/audiencecontact/send_marketing_email.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": "Send marketing email",
                "contacts": recipients,
                "form": form,
                "action_name": "send_marketing_email",
                "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
                "cancel_url": reverse("admin:pages_audiencecontact_changelist"),
            },
        )

    @admin.action(description="Unsubscribe selected contacts from marketing")
    def unsubscribe_selected_contacts(self, request, queryset):
        updated = queryset.filter(marketing_opt_in=True).update(
            marketing_opt_in=False,
            unsubscribed_at=timezone.now(),
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

    list_display = ("tenant", "full_name", "email", "phone", "marketing_opt_in", "source_page", "status", "created_at")
    list_filter = ("status", "marketing_opt_in", "source_page", "created_at")
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
