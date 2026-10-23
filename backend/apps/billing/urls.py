from django.urls import path
from .views import StartPayPalCheckoutView, PayPalReturnView, PayPalWebhookView

from .views import (
    BillingStatusView,
    CancelSubscriptionView,
    RazorpayVerifyPaymentView,
    RazorpayWebhookView,
    StartCheckoutView,
    StartRazorpayCheckoutView,
    StripeWebhookView,
)

urlpatterns = [
    path("checkout/paypal/<slug:plan_code>/", StartPayPalCheckoutView.as_view(), name="billing-paypal-checkout"),
    path("paypal/return/", PayPalReturnView.as_view(), name="billing-paypal-return"),
    path("paypal/webhook/", PayPalWebhookView.as_view(), name="billing-paypal-webhook"),
    path("status/", BillingStatusView.as_view(), name="billing-status"),
    path("checkout/<slug:plan_code>/", StartCheckoutView.as_view(), name="billing-checkout"),
    path("checkout/razorpay/<slug:plan_code>/", StartRazorpayCheckoutView.as_view(), name="billing-razorpay-checkout"),
    path("razorpay/verify/", RazorpayVerifyPaymentView.as_view(), name="billing-razorpay-verify"),
    path("razorpay/webhook/", RazorpayWebhookView.as_view(), name="billing-razorpay-webhook"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="billing-stripe-webhook"),
    path("cancel/", CancelSubscriptionView.as_view(), name="billing-cancel"),
]
