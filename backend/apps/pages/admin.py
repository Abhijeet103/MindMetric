from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.mail import EmailMessage, get_connection
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from backend.apps.tenants.admin_mixins import TenantScopedAdminMixin

from .models import AudienceContact, SaleInquiry, TestSuggestion


class MarketingEmailForm(forms.Form):
    subject = forms.CharField(max_length=180)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 14}))


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
