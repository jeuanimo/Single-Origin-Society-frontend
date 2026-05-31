"""
Shopify webhook endpoint.
Verifies HMAC-SHA256 signature, parses order payload,
sends notification email to the contact inbox.
"""

import hashlib
import hmac
import json
import base64
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _verify_shopify_signature(request):
    secret = settings.SHOPIFY_WEBHOOK_SECRET.strip()
    if not secret:
        logger.warning("SHOPIFY_WEBHOOK_SECRET is not set — skipping signature check.")
        return True

    header_hmac = request.headers.get("X-Shopify-Hmac-Sha256", "")
    digest = hmac.new(
        secret.encode("utf-8"),
        request.body,
        digestmod=hashlib.sha256,
    ).digest()
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, header_hmac)


def _build_order_email_body(order):
    name = order.get("name", "—")
    email = order.get("email", "—")
    total = order.get("total_price", "—")
    currency = order.get("currency", "")
    financial = order.get("financial_status", "—")
    fulfillment = order.get("fulfillment_status") or "unfulfilled"

    customer = order.get("customer", {})
    first = customer.get("first_name", "")
    last = customer.get("last_name", "")
    customer_name = f"{first} {last}".strip() or email

    shipping = order.get("shipping_address", {})
    ship_line = ", ".join(filter(None, [
        shipping.get("address1"),
        shipping.get("city"),
        shipping.get("province"),
        shipping.get("country"),
    ])) if shipping else "—"

    lines = order.get("line_items", [])
    items_text = "\n".join(
        f"  • {item.get('title', '?')} x{item.get('quantity', 1)}  ${item.get('price', '0.00')}"
        for item in lines
    ) or "  (no items)"

    return f"""New order received on Single Origin Society.

ORDER: {name}
CUSTOMER: {customer_name}
EMAIL: {email}
TOTAL: {total} {currency}
PAYMENT: {financial}
FULFILLMENT: {fulfillment}
SHIP TO: {ship_line}

ITEMS:
{items_text}

---
View order in Shopify Admin:
https://admin.shopify.com/store/{settings.SHOPIFY_STORE_DOMAIN.replace('.myshopify.com', '')}/orders
"""


@csrf_exempt
@require_POST
def order_paid(request):
    if not _verify_shopify_signature(request):
        logger.warning("Shopify webhook signature verification failed.")
        return HttpResponseForbidden("Invalid signature.")

    try:
        order = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON.")

    order_name = order.get("name", "New Order")
    recipient = settings.ORDER_NOTIFICATION_EMAIL.strip()

    try:
        msg = EmailMessage(
            subject=f"🛍 Order {order_name} — Single Origin Society",
            body=_build_order_email_body(order),
            from_email=None,
            to=[recipient],
        )
        msg.send()
        logger.info("Order notification sent for %s", order_name)
    except Exception as e:
        logger.error("Failed to send order notification: %s", e)

    return HttpResponse(status=200)
