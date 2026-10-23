from __future__ import annotations

import json

from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Subscription
from .regions import get_request_country_code
from .services import (
    BillingConfigurationError,
    BillingWebhookError,
    activate_subscription_from_checkout,
    activate_subscription_from_razorpay_payment,
    cancel_user_subscription,
    construct_stripe_event,
    create_checkout_session,
    create_razorpay_order,
    get_razorpay_payment,
    razorpay_webhook_is_configured,
    sync_user_subscription_access,
    verify_razorpay_payment_signature,
    verify_razorpay_webhook,
)


from .services import (create_paypal_order, capture_paypal_order, get_paypal_order,
    activate_subscription_from_paypal_order, paypal_webhook_is_configured, verify_paypal_webhook,
    PAYPAL_REVOKING_EVENTS, PayPalPaymentPendingError, paypal_capture_is_fully_reversed,
    paypal_order_id_from_event, revoke_paypal_subscription)

class StartPayPalCheckoutView(View):
    def post(self, request, plan_code: str):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")

        try:
            approval_url = create_paypal_order(
                request.user,
                plan_code,
                base_url=f"{request.scheme}://{request.get_host()}",
                country_code=get_request_country_code(request),
            )
        except (BillingConfigurationError, BillingWebhookError) as exc:
            messages.error(request, str(exc))
            return redirect(request.META.get("HTTP_REFERER") or "pages:subscription")

        return redirect(approval_url)


class PayPalReturnView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("pages:login")

        order_id = request.GET.get("token", "").strip()
        if not order_id:
            messages.error(request, "PayPal did not return an order token.")
            return redirect("pages:subscription")

        try:
            if not request.user.subscriptions.filter(provider="paypal", provider_subscription_id=order_id).exists():
                raise BillingWebhookError("This checkout does not belong to your account.")
            capture_payload = capture_paypal_order(order_id)
            activate_subscription_from_paypal_order(capture_payload)
        except PayPalPaymentPendingError as exc:
            messages.info(request, str(exc))
            return redirect(f"{request.build_absolute_uri('/subscription/')}?checkout=processing")
        except (BillingConfigurationError, BillingWebhookError) as exc:
            messages.error(request, str(exc))
            return redirect(f"{request.build_absolute_uri('/subscription/')}?checkout=cancelled")

        messages.success(request, "PayPal payment confirmed. Your access is now active.")
        return redirect("pages:subscription")


@method_decorator(csrf_exempt, name="dispatch")
class PayPalWebhookView(View):
    def post(self, request):
        if not paypal_webhook_is_configured():
            return HttpResponseBadRequest("PayPal webhook verification is not configured yet.")

        try:
            event_payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid PayPal webhook payload.")

        try:
            verified = verify_paypal_webhook(headers=request.headers, event_payload=event_payload)
        except (BillingConfigurationError, BillingWebhookError) as exc:
            return HttpResponseBadRequest(str(exc))

        if not verified:
            return HttpResponseBadRequest("Invalid PayPal webhook signature.")

        event_type = event_payload.get("event_type", "")
        try:
            if event_type == "PAYMENT.CAPTURE.COMPLETED":
                order_id = paypal_order_id_from_event(event_payload)
                if order_id:
                    activate_subscription_from_paypal_order(get_paypal_order(order_id))
            elif event_type in PAYPAL_REVOKING_EVENTS:
                order_id = paypal_order_id_from_event(event_payload)
                if order_id and paypal_capture_is_fully_reversed(event_payload):
                    revoke_paypal_subscription(order_id, reason=event_type)
        except (BillingConfigurationError, BillingWebhookError) as exc:
            return HttpResponseBadRequest(str(exc))

        return JsonResponse({"received": True, "type": event_type})
class BillingStatusView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Authentication required."}, status=401)

        sync_user_subscription_access(request.user)
        active = request.user.subscriptions.filter(status="active").first()
        expires_at = request.effective_access_expires_at
        return JsonResponse(
            {
                "role": request.effective_role,
                "role_label": request.effective_role_label,
                "subscription_expires_at": expires_at.isoformat() if expires_at else None,
                "subscription": {
                    "active": request.effective_access_active,
                    "plan_code": request.effective_plan_code or (active.plan_code if active else None),
                    "source": request.effective_access_source,
                    "source_label": request.effective_access_source_label,
                    "tenant_managed": request.effective_access_tenant_managed,
                },
            }
        )


class StartCheckoutView(View):
    def post(self, request, plan_code: str):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")

        try:
            checkout_url = create_checkout_session(
                request.user,
                plan_code,
                base_url=f"{request.scheme}://{request.get_host()}",
                country_code=get_request_country_code(request),
            )
        except BillingConfigurationError as exc:
            messages.error(request, str(exc))
            return redirect(request.META.get("HTTP_REFERER") or "pages:subscription")

        return redirect(checkout_url)


class StartRazorpayCheckoutView(View):
    def post(self, request, plan_code: str):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Authentication required."}, status=401)

        try:
            checkout = create_razorpay_order(
                request.user,
                plan_code,
                base_url=f"{request.scheme}://{request.get_host()}",
                country_code=get_request_country_code(request),
            )
        except (BillingConfigurationError, BillingWebhookError) as exc:
            return JsonResponse({"detail": str(exc)}, status=400)

        return JsonResponse(checkout)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    def post(self, request):
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = construct_stripe_event(request.body, signature)
        except (BillingConfigurationError, BillingWebhookError) as exc:
            return HttpResponseBadRequest(str(exc))

        event_type = event["type"]
        if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            session_payload = event["data"]["object"]
            if session_payload.get("payment_status") == "paid":
                try:
                    activate_subscription_from_checkout(session_payload)
                except (BillingConfigurationError, BillingWebhookError) as exc:
                    return HttpResponseBadRequest(str(exc))

        return JsonResponse({"received": True, "type": event_type})


class RazorpayVerifyPaymentView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Authentication required."}, status=401)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid Razorpay payment payload.")

        order_id = str(payload.get("razorpay_order_id", "")).strip()
        payment_id = str(payload.get("razorpay_payment_id", "")).strip()
        signature = str(payload.get("razorpay_signature", "")).strip()
        try:
            verify_razorpay_payment_signature(
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
            )
            request.user.subscriptions.get(
                provider="razorpay",
                provider_subscription_id=order_id,
            )
            payment = get_razorpay_payment(payment_id)
            if payment.get("order_id") != order_id:
                raise BillingWebhookError("Razorpay payment does not match its checkout order.")
            subscription = activate_subscription_from_razorpay_payment(payment)
        except (BillingConfigurationError, BillingWebhookError) as exc:
            return JsonResponse({"detail": str(exc)}, status=400)
        except Subscription.DoesNotExist:
            return JsonResponse({"detail": "This checkout does not belong to your account."}, status=403)

        return JsonResponse(
            {
                "received": True,
                "subscription_id": subscription.id,
                "redirect_url": f"{request.build_absolute_uri('/subscription/')}?checkout=success",
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(View):
    def post(self, request):
        if not razorpay_webhook_is_configured():
            return HttpResponseBadRequest("Razorpay webhook verification is not configured yet.")

        try:
            event_payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid Razorpay webhook payload.")

        try:
            verify_razorpay_webhook(
                payload=request.body,
                signature=request.META.get("HTTP_X_RAZORPAY_SIGNATURE", ""),
            )
        except (BillingConfigurationError, BillingWebhookError) as exc:
            return HttpResponseBadRequest(str(exc))

        event_type = event_payload.get("event", "")
        if event_type == "payment.captured":
            payment = ((event_payload.get("payload") or {}).get("payment") or {}).get("entity") or {}
            try:
                activate_subscription_from_razorpay_payment(payment)
            except (BillingConfigurationError, BillingWebhookError) as exc:
                return HttpResponseBadRequest(str(exc))

        return JsonResponse({"received": True, "type": event_type})


class CancelSubscriptionView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("pages:login")

        cancel_user_subscription(request.user)
        messages.success(request, "Your subscription has been canceled.")
        return redirect(request.META.get("HTTP_REFERER") or "pages:subscription")
