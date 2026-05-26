class ReferralTrackingMiddleware:
    """Stores referral and campaign query parameters as lightweight attribution placeholders."""

    TRACK_KEYS = ("ref", "utm_source", "utm_medium", "utm_campaign")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        for key in self.TRACK_KEYS:
            value = (request.GET.get(key) or "").strip()
            if value:
                request.session[f"tracking_{key}"] = value[:120]

        if request.GET:
            request.session["tracking_landing_path"] = request.path

        return self.get_response(request)
