(() => {
    const forms = document.querySelectorAll("[data-razorpay-checkout]");

    const showError = (message) => {
        window.alert(message || "We could not start secure checkout. Please try again.");
    };

    forms.forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!window.Razorpay) {
                showError("Secure checkout is unavailable right now. Please refresh and try again.");
                return;
            }

            const button = form.querySelector("button[type='submit']");
            const csrfToken = form.querySelector("input[name='csrfmiddlewaretoken']")?.value;
            button?.setAttribute("disabled", "disabled");

            try {
                const orderResponse = await fetch(form.action, {
                    method: "POST",
                    headers: {
                        "Accept": "application/json",
                        "X-CSRFToken": csrfToken || "",
                    },
                    credentials: "same-origin",
                });
                const order = await orderResponse.json();
                if (!orderResponse.ok) {
                    throw new Error(order.detail || "Unable to create the payment order.");
                }

                const checkout = new window.Razorpay({
                    ...order,
                    handler: async (payment) => {
                        try {
                            const verifyResponse = await fetch(form.dataset.razorpayVerifyUrl, {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                    "X-CSRFToken": csrfToken || "",
                                },
                                credentials: "same-origin",
                                body: JSON.stringify(payment),
                            });
                            const verification = await verifyResponse.json();
                            if (!verifyResponse.ok) {
                                throw new Error(verification.detail || "Payment verification failed.");
                            }
                            window.location.assign(verification.redirect_url);
                        } catch (error) {
                            showError(error.message);
                            button?.removeAttribute("disabled");
                        }
                    },
                    modal: {
                        ondismiss: () => button?.removeAttribute("disabled"),
                    },
                    theme: { color: "#3e7563" },
                });
                checkout.open();
            } catch (error) {
                showError(error.message);
                button?.removeAttribute("disabled");
            }
        });
    });
})();
