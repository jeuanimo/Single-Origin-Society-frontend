def cart_context(request):
    """Inject Shopify cart count into every template context."""
    return {"cart_count": request.session.get("shopify_cart_count", 0)}


def referral_context(request):
    return {
        "referral_placeholder": request.session.get("tracking_ref", ""),
        "utm_source_placeholder": request.session.get("tracking_utm_source", ""),
        "utm_medium_placeholder": request.session.get("tracking_utm_medium", ""),
        "utm_campaign_placeholder": request.session.get("tracking_utm_campaign", ""),
        "landing_path_placeholder": request.session.get("tracking_landing_path", request.path),
    }
